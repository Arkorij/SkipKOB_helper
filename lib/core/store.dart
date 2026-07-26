import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'calendar.dart';
import 'models.dart';

/// Все данные приложения: расписание, отметки, настройки.
///
/// Хранится локально одним JSON-файлом, как и в Python-версии, чтобы файлы
/// расписания были совместимы между ними.
class AppData {
  int academicYearStart;
  List<Break> breaks;

  /// 'odd'/'even' -> день недели -> список пар
  Map<String, Map<String, List<Pair>>> baseSchedule;

  /// ISO-дата -> пары этого дня (замена базовому расписанию)
  Map<String, List<Pair>> overrides;

  /// ISO-дата -> отметки
  Map<String, List<Mark>> marks;

  int? lastWeek;
  bool swipePages;

  AppData({
    required this.academicYearStart,
    required this.breaks,
    required this.baseSchedule,
    required this.overrides,
    required this.marks,
    this.lastWeek,
    this.swipePages = true,
  });

  factory AppData.empty() => AppData(
        academicYearStart: academicYearForDate(DateTime.now()),
        breaks: [],
        baseSchedule: {
          'odd': {for (final d in dayKeys) d: <Pair>[]},
          'even': {for (final d in dayKeys) d: <Pair>[]},
        },
        overrides: {},
        marks: {},
      );

  Map<String, dynamic> toJson() => {
        'academic_year_start': academicYearStart,
        'breaks': breaks.map((b) => b.toJson()).toList(),
        'base_schedule': {
          for (final parity in ['odd', 'even'])
            parity: {
              for (final d in dayKeys)
                d: (baseSchedule[parity]?[d] ?? const <Pair>[])
                    .map((p) => p.toJson())
                    .toList(),
            },
        },
        'overrides': {
          for (final e in overrides.entries) e.key: e.value.map((p) => p.toJson()).toList(),
        },
        'marks': {
          for (final e in marks.entries) e.key: e.value.map((m) => m.toJson()).toList(),
        },
        'last_week': lastWeek,
        'swipe_pages': swipePages,
      };

  factory AppData.fromJson(Map<String, dynamic> raw) {
    final data = AppData.empty();
    if (raw['academic_year_start'] is int) {
      data.academicYearStart = raw['academic_year_start'] as int;
    }
    if (raw['breaks'] is List) {
      data.breaks = (raw['breaks'] as List)
          .map(Break.fromJson)
          .whereType<Break>()
          .toList();
    }
    final sched = raw['base_schedule'];
    if (sched is Map) {
      for (final parity in ['odd', 'even']) {
        final par = sched[parity];
        if (par is Map) {
          for (final d in dayKeys) {
            final list = par[d];
            if (list is List) {
              data.baseSchedule[parity]![d] = list.map(Pair.fromJson).toList();
            }
          }
        }
      }
    }
    final ov = raw['overrides'];
    if (ov is Map) {
      ov.forEach((key, value) {
        if (value is List) {
          data.overrides[key as String] = value.map(Pair.fromJson).toList();
        }
      });
    }
    final mk = raw['marks'];
    if (mk is Map) {
      mk.forEach((key, value) {
        if (value is List) {
          data.marks[key as String] =
              value.whereType<Map>().map(Mark.fromJson).toList();
        }
      });
    }
    if (raw['last_week'] is int) data.lastWeek = raw['last_week'] as int;
    if (raw['swipe_pages'] is bool) data.swipePages = raw['swipe_pages'] as bool;
    return data;
  }

  /// Только «основа» — то, что уходит в файл расписания.
  Map<String, dynamic> baseToJson() => {
        '_format': 'SkipKOB_Helper schedule',
        'academic_year_start': academicYearStart,
        'breaks': breaks.map((b) => b.toJson()).toList(),
        'base_schedule': toJson()['base_schedule'],
      };

  /// Перезаписать основу импортом, сохранив отметки.
  void applyBase(Map<String, dynamic> incoming) {
    final parsed = AppData.fromJson({
      ...toJson(),
      if (incoming.containsKey('academic_year_start'))
        'academic_year_start': incoming['academic_year_start'],
      if (incoming.containsKey('breaks')) 'breaks': incoming['breaks'],
      if (incoming.containsKey('base_schedule'))
        'base_schedule': incoming['base_schedule'],
    });
    academicYearStart = parsed.academicYearStart;
    breaks = parsed.breaks;
    baseSchedule = parsed.baseSchedule;
  }
}

class Store {
  static const fileName = 'data.json';

  static Future<File> _file() async {
    final dir = await getApplicationSupportDirectory();
    if (!await dir.exists()) await dir.create(recursive: true);
    return File('${dir.path}${Platform.pathSeparator}$fileName');
  }

  static Future<AppData> load() async {
    try {
      final f = await _file();
      if (!await f.exists()) {
        final data = AppData.empty();
        await save(data);
        return data;
      }
      final raw = jsonDecode(await f.readAsString());
      if (raw is Map<String, dynamic>) return AppData.fromJson(raw);
    } catch (_) {
      // повреждённый файл — начинаем с пустых данных, чтобы приложение открылось
    }
    return AppData.empty();
  }

  static Future<void> save(AppData data) async {
    final f = await _file();
    final tmp = File('${f.path}.tmp');
    await tmp.writeAsString(const JsonEncoder.withIndent('  ').convert(data.toJson()));
    await tmp.rename(f.path);
  }

  static Future<AppData> reset() async {
    final data = AppData.empty();
    await save(data);
    return data;
  }
}
