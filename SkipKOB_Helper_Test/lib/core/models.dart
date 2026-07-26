import 'package:flutter/material.dart';

/// Тип занятия — определяет цвет плашки у пары.
enum PairKind { lecture, practice, lab }

const kindLabels = {
  PairKind.lecture: 'Лекция',
  PairKind.practice: 'Практика',
  PairKind.lab: 'Лабораторная',
};

const kindShort = {
  PairKind.lecture: 'Лек',
  PairKind.practice: 'Прк',
  PairKind.lab: 'Лаб',
};

const kindColors = {
  PairKind.lecture: Color(0xFF66BB6A), // зелёный
  PairKind.practice: Color(0xFFFDD835), // жёлтый
  PairKind.lab: Color(0xFF42A5F5), // синий
};

const consultationLabel = 'Консультация';
const consultationColor = Color(0xFFF06292); // розовый

/// Категория статуса — по ней считается статистика.
enum StatusCategory { came, excused, unexcused, neutral, consAbsent, consPresent }

class Status {
  final String key;
  final String label;
  final StatusCategory category;

  /// Цвет кружка в расписании.
  final Color color;

  /// Оттенок для диаграммы: похожие причины должны различаться.
  final Color chartColor;

  const Status(this.key, this.label, this.category, this.color, this.chartColor);
}

/// Статусы обычной пары. Пришёл — зелёный; уважительные — оранжевый;
/// неуважительные — красный; «всё сдал» — фиолетовый; отменена — серый.
const statuses = <Status>[
  Status('came', 'Пришёл', StatusCategory.came, Color(0xFF66BB6A), Color(0xFF66BB6A)),
  Status('medical', 'Справка', StatusCategory.excused, Color(0xFFFFA726), Color(0xFFFFD54F)),
  Status('excused', 'Уваж. причина', StatusCategory.excused, Color(0xFFFFA726), Color(0xFFFB8C00)),
  Status('overslept', 'Проспал', StatusCategory.unexcused, Color(0xFFEF5350), Color(0xFFE57373)),
  Status('skipped', 'Не захотел', StatusCategory.unexcused, Color(0xFFEF5350), Color(0xFFEF5350)),
  Status('no_energy', 'Нет сил', StatusCategory.unexcused, Color(0xFFEF5350), Color(0xFFE53935)),
  Status('passed', 'Всё сдал', StatusCategory.neutral, Color(0xFFBA68C8), Color(0xFFBA68C8)),
  Status('cancelled', 'Пара отменена', StatusCategory.neutral, Color(0xFF78909C), Color(0xFF78909C)),
];

const consStatuses = <Status>[
  Status('not_came', 'Не пришёл', StatusCategory.consAbsent, Color(0xFF78909C), Color(0xFF78909C)),
  Status('present', 'Пришёл', StatusCategory.consPresent, Color(0xFF66BB6A), Color(0xFF66BB6A)),
];

const defaultStatus = 'came';
const consDefaultStatus = 'not_came';

const absenceKeys = {'medical', 'excused', 'overslept', 'skipped', 'no_energy'};
const excusedKeys = {'medical', 'excused'};
const unexcusedKeys = {'overslept', 'skipped', 'no_energy'};
const neutralKeys = {'passed', 'cancelled'};

Status? statusByKey(String key, {bool consultation = false}) {
  final table = consultation ? consStatuses : statuses;
  for (final s in table) {
    if (s.key == key) return s;
  }
  return null;
}

String statusLabel(String key, {bool consultation = false}) =>
    statusByKey(key, consultation: consultation)?.label ?? key;

/// Пара в расписании.
class Pair {
  final String name;
  final PairKind kind;
  final bool consultation;

  const Pair(this.name, {this.kind = PairKind.lecture, this.consultation = false});

  String get defaultStatusKey => consultation ? consDefaultStatus : defaultStatus;

  List<Status> get availableStatuses => consultation ? consStatuses : statuses;

  Map<String, dynamic> toJson() => {
        'name': name,
        'kind': kind.name,
        'consultation': consultation,
      };

  static Pair fromJson(dynamic raw) {
    if (raw is String) return parsePair(raw);
    if (raw is Map) {
      final kindName = raw['kind'] as String? ?? 'lecture';
      return Pair(
        (raw['name'] as String? ?? '').trim(),
        kind: PairKind.values.firstWhere(
          (k) => k.name == kindName,
          orElse: () => PairKind.lecture,
        ),
        consultation: raw['consultation'] == true,
      );
    }
    return const Pair('');
  }

  /// Строка редактора: '#' — консультация, '*' — практика, '~' — лаб.
  static Pair parse(String line) => parsePair(line);

  String format() {
    var prefix = '';
    if (consultation) prefix += '#';
    if (kind == PairKind.practice) {
      prefix += '*';
    } else if (kind == PairKind.lab) {
      prefix += '~';
    }
    return prefix.isEmpty ? name : '$prefix $name';
  }
}

Pair parsePair(String line) {
  var s = line.trim();
  var consultation = false;
  var kind = PairKind.lecture;
  while (s.isNotEmpty && '#*~^'.contains(s[0])) {
    switch (s[0]) {
      case '#':
        consultation = true;
        break;
      case '*':
        kind = PairKind.practice;
        break;
      case '~':
        kind = PairKind.lab;
        break;
      case '^':
        kind = PairKind.lecture;
        break;
    }
    s = s.substring(1).trimLeft();
  }
  return Pair(s, kind: kind, consultation: consultation);
}

/// Отметка посещаемости — снимок пары вместе с проставленным статусом.
class Mark {
  final String subject;
  final String status;
  final bool consultation;
  final PairKind kind;

  const Mark({
    required this.subject,
    required this.status,
    this.consultation = false,
    this.kind = PairKind.lecture,
  });

  Mark copyWith({String? status}) => Mark(
        subject: subject,
        status: status ?? this.status,
        consultation: consultation,
        kind: kind,
      );

  Map<String, dynamic> toJson() => {
        'subject': subject,
        'status': status,
        'consultation': consultation,
        'kind': kind.name,
      };

  static Mark fromJson(Map raw) {
    final kindName = raw['kind'] as String? ?? 'lecture';
    return Mark(
      subject: raw['subject'] as String? ?? '',
      status: raw['status'] as String? ?? defaultStatus,
      consultation: raw['consultation'] == true,
      kind: PairKind.values.firstWhere(
        (k) => k.name == kindName,
        orElse: () => PairKind.lecture,
      ),
    );
  }
}
