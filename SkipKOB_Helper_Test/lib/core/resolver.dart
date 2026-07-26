import 'calendar.dart';
import 'models.dart';
import 'store.dart';

/// Какие пары в конкретный день: ручная правка дня, иначе база по чётности.
List<Pair> pairsForDate(AppData data, DateTime day, int weekN) {
  final iso = isoDate(day);
  final override = data.overrides[iso];
  if (override != null) return List<Pair>.from(override);

  // До 1 сентября учебного года пар нет (дни первой недели из августа).
  if (day.isBefore(DateTime(data.academicYearStart, 9, 1))) return const [];

  final weekday = day.weekday; // 1 = понедельник
  if (weekday > dayKeys.length) return const [];
  final dayKey = dayKeys[weekday - 1];
  return List<Pair>.from(data.baseSchedule[parityKey(weekN)]?[dayKey] ?? const <Pair>[]);
}

/// Отметки дня, выровненные по списку пар. Недостающие — дефолтные.
List<Mark> dayMarks(AppData data, DateTime day, List<Pair> pairs) {
  final stored = data.marks[isoDate(day)] ?? const <Mark>[];
  return [
    for (var i = 0; i < pairs.length; i++)
      Mark(
        subject: pairs[i].name,
        status: (i < stored.length && stored[i].subject == pairs[i].name)
            ? stored[i].status
            : pairs[i].defaultStatusKey,
        consultation: pairs[i].consultation,
        kind: pairs[i].kind,
      ),
  ];
}

/// Проставить статус паре, сохранив снимок всего дня.
void setMark(AppData data, DateTime day, List<Pair> pairs, int index, String status) {
  final marks = dayMarks(data, day, pairs);
  if (index < 0 || index >= marks.length) return;
  marks[index] = marks[index].copyWith(status: status);
  data.marks[isoDate(day)] = marks;
}
