import 'calendar.dart';
import 'models.dart';
import 'store.dart';

class Stats {
  int totalAbsences = 0;
  int excused = 0;
  int unexcused = 0;
  int fullDays = 0;
  int passed = 0;
  int cancelled = 0;
  int consPresent = 0;

  /// ключ статуса -> количество
  final Map<String, int> byReason = {};

  /// предмет -> количество прогулов
  final Map<String, int> bySubject = {};

  /// предмет -> тип занятия -> количество
  final Map<String, Map<PairKind, int>> bySubjectKind = {};
}

/// День пропущен полностью?
///
/// Считаются только «зачётные» пары: без консультаций, без отменённых и без
/// «всё сдал». Если таких нет — день не пропущен. Если хоть на одной «пришёл» —
/// тоже нет. Если все пропущены (по любой причине) — день полный.
bool isFullDay(List<Mark> marks) {
  final countable = marks
      .where((m) => !m.consultation && !neutralKeys.contains(m.status))
      .toList();
  if (countable.isEmpty) return false;
  if (countable.any((m) => m.status == 'came')) return false;
  return countable.every((m) => absenceKeys.contains(m.status));
}

Stats computeStats(AppData data) {
  final s = Stats();
  data.marks.forEach((iso, marks) {
    for (final m in marks) {
      if (m.consultation) {
        if (m.status == 'present') s.consPresent++;
        continue;
      }
      if (absenceKeys.contains(m.status)) {
        s.totalAbsences++;
        s.byReason[m.status] = (s.byReason[m.status] ?? 0) + 1;
        s.bySubject[m.subject] = (s.bySubject[m.subject] ?? 0) + 1;
        final kinds = s.bySubjectKind.putIfAbsent(m.subject, () => {});
        kinds[m.kind] = (kinds[m.kind] ?? 0) + 1;
        if (excusedKeys.contains(m.status)) {
          s.excused++;
        } else if (unexcusedKeys.contains(m.status)) {
          s.unexcused++;
        }
      } else if (m.status == 'passed') {
        s.passed++;
      } else if (m.status == 'cancelled') {
        s.cancelled++;
      }
    }
    if (isFullDay(marks)) s.fullDays++;
  });
  return s;
}

class AbsenceRecord {
  final DateTime date;
  final String subject;
  final String status;

  const AbsenceRecord(this.date, this.subject, this.status);
}

List<AbsenceRecord> absenceRecords(AppData data) {
  final out = <AbsenceRecord>[];
  data.marks.forEach((iso, marks) {
    final day = DateTime.tryParse(iso);
    if (day == null) return;
    for (final m in marks) {
      if (m.consultation) continue;
      if (absenceKeys.contains(m.status)) {
        out.add(AbsenceRecord(day, m.subject, m.status));
      }
    }
  });
  out.sort((a, b) {
    final byDate = a.date.compareTo(b.date);
    return byDate != 0 ? byDate : a.subject.compareTo(b.subject);
  });
  return out;
}

/// Markdown-отчёт: сверху сводка, ниже подробности по каждому прогулу.
String buildReport(AppData data) {
  final s = computeStats(data);
  final records = absenceRecords(data);
  final b = StringBuffer()
    ..writeln('# Отчёт о прогулах — SkipKOB_Helper')
    ..writeln()
    ..writeln('_Сформировано: ${formatDateShort(DateTime.now())}_')
    ..writeln()
    ..writeln('## Краткая статистика')
    ..writeln()
    ..writeln('- Всего прогулов (пар): **${s.totalAbsences}**')
    ..writeln('  - по уважительной причине: **${s.excused}**')
    ..writeln('  - по неуважительной причине: **${s.unexcused}**')
    ..writeln('- Полностью пропущенных дней: **${s.fullDays}**')
    ..writeln('- Пар «всё сдал»: ${s.passed}')
    ..writeln('- Отменённых пар: ${s.cancelled}')
    ..writeln('- Посещено консультаций: ${s.consPresent}')
    ..writeln();

  if (s.byReason.isNotEmpty) {
    b
      ..writeln('### По причинам')
      ..writeln();
    final reasons = s.byReason.entries.toList()
      ..sort((x, y) => y.value.compareTo(x.value));
    for (final e in reasons) {
      b.writeln('- ${statusLabel(e.key)}: ${e.value}');
    }
    b.writeln();
  }

  if (s.bySubject.isNotEmpty) {
    b
      ..writeln('### По предметам')
      ..writeln();
    final subjects = s.bySubject.entries.toList()
      ..sort((x, y) => y.value.compareTo(x.value));
    for (final e in subjects) {
      b.writeln('- ${e.key}: ${e.value}');
    }
    b.writeln();
  }

  b
    ..writeln('## Подробности по каждому прогулу')
    ..writeln();
  if (records.isEmpty) {
    b.writeln('_Прогулов нет._');
  } else {
    b
      ..writeln('| Дата | Предмет | Причина |')
      ..writeln('| --- | --- | --- |');
    for (final r in records) {
      final wd = r.date.weekday <= 6 ? dayShortRu[dayKeys[r.date.weekday - 1]] : null;
      final dateStr =
          wd != null ? '${formatDateShort(r.date)} ($wd)' : formatDateShort(r.date);
      b.writeln('| $dateStr | ${r.subject} | ${statusLabel(r.status)} |');
    }
  }
  b.writeln();
  return b.toString();
}
