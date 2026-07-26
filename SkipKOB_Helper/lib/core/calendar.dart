/// Учебный календарь: номера недель, чётность, пропуск каникул.
library;

const totalWeeks = 40;

const dayKeys = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'];

const dayNamesRu = {
  'mon': 'Понедельник',
  'tue': 'Вторник',
  'wed': 'Среда',
  'thu': 'Четверг',
  'fri': 'Пятница',
  'sat': 'Суббота',
};

const dayShortRu = {
  'mon': 'Пн',
  'tue': 'Вт',
  'wed': 'Ср',
  'thu': 'Чт',
  'fri': 'Пт',
  'sat': 'Сб',
};

const monthsRu = [
  '',
  'января',
  'февраля',
  'марта',
  'апреля',
  'мая',
  'июня',
  'июля',
  'августа',
  'сентября',
  'октября',
  'ноября',
  'декабря',
];

class Break {
  final DateTime start;
  final DateTime end;

  const Break(this.start, this.end);

  Map<String, String> toJson() => {
        'start': _iso(start),
        'end': _iso(end),
      };

  static Break? fromJson(dynamic raw) {
    if (raw is! Map) return null;
    final s = DateTime.tryParse(raw['start'] as String? ?? '');
    final e = DateTime.tryParse(raw['end'] as String? ?? '');
    if (s == null || e == null) return null;
    return e.isBefore(s) ? Break(e, s) : Break(s, e);
  }
}

String _iso(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

String isoDate(DateTime d) => _iso(d);

DateTime dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);

/// К какому учебному году (по 1 сентября) относится дата.
int academicYearForDate(DateTime d) => d.month >= 9 ? d.year : d.year - 1;

/// Понедельник недели, в которую попадает 1 сентября.
DateTime firstMonday(int yearStart) {
  final sept1 = DateTime(yearStart, 9, 1);
  return sept1.subtract(Duration(days: sept1.weekday - 1));
}

bool _mondayInBreak(DateTime monday, List<Break> breaks) {
  for (final b in breaks) {
    if (!monday.isBefore(b.start) && !monday.isAfter(b.end)) return true;
  }
  return false;
}

/// Номер учебной недели -> понедельник. Каникулярные недели пропускаются.
Map<int, DateTime> weekMondays(int yearStart, List<Break> breaks, {int total = totalWeeks}) {
  final result = <int, DateTime>{};
  var monday = firstMonday(yearStart);
  var n = 0;
  var guard = 0;
  while (n < total && guard < total + 120) {
    guard++;
    if (!_mondayInBreak(monday, breaks)) {
      n++;
      result[n] = monday;
    }
    monday = monday.add(const Duration(days: 7));
  }
  return result;
}

/// Даты Пн..Сб для учебной недели n.
List<DateTime> datesForWeek(int yearStart, List<Break> breaks, int n) {
  final monday = weekMondays(yearStart, breaks)[n];
  if (monday == null) return const [];
  return List.generate(6, (i) => monday.add(Duration(days: i)));
}

bool isOdd(int n) => n % 2 == 1;

String parityKey(int n) => isOdd(n) ? 'odd' : 'even';

String parityLabel(int n) => isOdd(n) ? 'нечётная' : 'чётная';

/// Номер недели, в которую попадает дата (с защёлкиванием в диапазон).
int currentWeekNumber(int yearStart, List<Break> breaks, [DateTime? today]) {
  final day = dateOnly(today ?? DateTime.now());
  final mondays = weekMondays(yearStart, breaks);
  if (mondays.isEmpty) return 1;
  for (final entry in mondays.entries) {
    final end = entry.value.add(const Duration(days: 6));
    if (!day.isBefore(entry.value) && !day.isAfter(end)) return entry.key;
  }
  if (day.isBefore(mondays[1]!)) return 1;
  return mondays.keys.reduce((a, b) => a > b ? a : b);
}

String formatDate(DateTime d) => '${d.day} ${monthsRu[d.month]}';

String formatDateShort(DateTime d) =>
    '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
