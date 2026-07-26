import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app_state.dart';
import '../../core/models.dart';
import '../../core/stats.dart';
import '../theme.dart';

class StatsPage extends StatefulWidget {
  final AppState state;

  const StatsPage({super.key, required this.state});

  @override
  State<StatsPage> createState() => _StatsPageState();
}

class _StatsPageState extends State<StatsPage> {
  bool _detailed = true;

  @override
  Widget build(BuildContext context) {
    final s = computeStats(widget.state.data);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Статистика прогулов',
          style: TextStyle(
            fontSize: T.fsTitle,
            fontWeight: FontWeight.bold,
            color: T.text,
          ),
        ),
        const SizedBox(height: 16),
        Row(children: [
          Expanded(
            child: _StatCard('Всего прогулов', s.totalAbsences,
                const Color(0xFFE57373), Icons.event_busy),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _StatCard('Полных дней', s.fullDays,
                const Color(0xFFFF8A65), Icons.today),
          ),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: _StatCard('Уважительные', s.excused,
                const Color(0xFF64B5F6), Icons.verified_outlined),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _StatCard('Неуважительные', s.unexcused,
                const Color(0xFFFFB74D), Icons.report_gmailerrorred),
          ),
        ]),
        const SizedBox(height: 16),
        _reasonsCard(s),
        const SizedBox(height: 16),
        if (s.bySubject.isNotEmpty) ...[
          _subjectsCard(s),
          const SizedBox(height: 16),
        ],
        _extraCard(s),
      ],
    );
  }

  Widget _reasonsCard(Stats s) {
    if (s.byReason.isEmpty) {
      return const Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionTitle('Причины прогулов'),
            SizedBox(height: 8),
            Text('Пока нет прогулов',
                style: TextStyle(
                    fontSize: T.fsHint,
                    color: T.textDim,
                    fontStyle: FontStyle.italic)),
          ],
        ),
      );
    }
    final entries = s.byReason.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final total = s.byReason.values.fold<int>(0, (a, b) => a + b);
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionTitle('Причины прогулов'),
          const SizedBox(height: 10),
          Row(
            children: [
              SizedBox(
                width: 150,
                height: 150,
                child: CustomPaint(
                  painter: _DonutPainter([
                    for (final e in entries)
                      _Slice(e.value / total,
                          statusByKey(e.key)?.chartColor ?? T.textDim),
                  ]),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    for (final e in entries)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(children: [
                          Container(
                            width: 12,
                            height: 12,
                            decoration: BoxDecoration(
                              color: statusByKey(e.key)?.chartColor ?? T.textDim,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              '${statusLabel(e.key)} — ${e.value}',
                              style: const TextStyle(
                                  fontSize: T.fsLabel, color: T.text),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ]),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _subjectsCard(Stats s) {
    final rows = <Widget>[];
    if (_detailed) {
      final entries = <({String subject, PairKind kind, int count})>[];
      s.bySubjectKind.forEach((subject, kinds) {
        for (final k in PairKind.values) {
          final c = kinds[k] ?? 0;
          if (c > 0) entries.add((subject: subject, kind: k, count: c));
        }
      });
      entries.sort((a, b) => b.count.compareTo(a.count));
      final top = entries.take(14).toList();
      final maxv = top.isEmpty ? 1 : top.first.count;
      for (final e in top) {
        rows.add(_BarRow(
          label: e.subject,
          labelWidth: 112,
          chip: Chip2(kindShort[e.kind]!, kindColors[e.kind]!),
          count: e.count,
          maxCount: maxv,
        ));
      }
    } else {
      final entries = s.bySubject.entries.toList()
        ..sort((a, b) => b.value.compareTo(a.value));
      final top = entries.take(10).toList();
      final maxv = top.isEmpty ? 1 : top.first.value;
      for (final e in top) {
        rows.add(_BarRow(
          label: e.key,
          labelWidth: 128,
          count: e.value,
          maxCount: maxv,
        ));
      }
    }

    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const SectionTitle('Прогулы по предметам'),
              TextButton.icon(
                onPressed: () => setState(() => _detailed = !_detailed),
                icon: const Icon(Icons.tune, size: 18),
                label: Text(_detailed ? 'Суммарно' : 'Детально'),
                style: TextButton.styleFrom(
                  foregroundColor: T.accent,
                  backgroundColor: T.surface2,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...rows,
        ],
      ),
    );
  }

  Widget _extraCard(Stats s) => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Дополнительно (не считается прогулом)'),
            const SizedBox(height: 12),
            _line('Освобождён от пары', s.passed, const Color(0xFFBA68C8),
                Icons.check_circle_outline),
            const SizedBox(height: 12),
            _line('Отменено пар', s.cancelled, const Color(0xFF90A4AE),
                Icons.cancel_outlined),
            const SizedBox(height: 12),
            _line('Посещено консультаций', s.consPresent,
                const Color(0xFF81C784), Icons.school_outlined),
          ],
        ),
      );

  Widget _line(String label, int value, Color color, IconData icon) => Row(
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(label,
                style: const TextStyle(fontSize: T.fsBody, color: T.textDim)),
          ),
          Text('$value',
              style: const TextStyle(
                  fontSize: T.fsBody,
                  fontWeight: FontWeight.bold,
                  color: T.text)),
        ],
      );
}

class _StatCard extends StatelessWidget {
  final String title;
  final int value;
  final Color accent;
  final IconData icon;

  const _StatCard(this.title, this.value, this.accent, this.icon);

  @override
  Widget build(BuildContext context) => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(icon, size: 20, color: accent),
              const SizedBox(width: 6),
              Expanded(
                child: Text(title,
                    style:
                        const TextStyle(fontSize: T.fsLabel, color: T.textDim),
                    overflow: TextOverflow.ellipsis),
              ),
            ]),
            const SizedBox(height: 4),
            Text('$value',
                style: const TextStyle(
                    fontSize: T.fsValue,
                    fontWeight: FontWeight.bold,
                    color: T.text)),
          ],
        ),
      );
}

/// Строка «предмет — [плашка] — полоса — число».
class _BarRow extends StatelessWidget {
  final String label;
  final double labelWidth;
  final Widget? chip;
  final int count;
  final int maxCount;

  const _BarRow({
    required this.label,
    required this.labelWidth,
    required this.count,
    required this.maxCount,
    this.chip,
  });

  @override
  Widget build(BuildContext context) {
    // запас справа, чтобы самая длинная полоса не упиралась в число
    final headroom = math.max(1, (maxCount * 0.18).round());
    final total = maxCount + headroom;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: SizedBox(
        height: 30,
        child: Row(
          children: [
            SizedBox(
              width: labelWidth,
              child: Text(label,
                  style: const TextStyle(fontSize: T.fsLabel, color: T.text),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis),
            ),
            if (chip != null) ...[const SizedBox(width: 8), chip!],
            const SizedBox(width: 8),
            Expanded(
              child: Row(children: [
                Expanded(
                  flex: math.max(1, count),
                  child: Container(
                    height: 16,
                    decoration: BoxDecoration(
                      color: T.accent,
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
                Expanded(flex: math.max(1, total - count), child: const SizedBox()),
              ]),
            ),
            SizedBox(
              width: 30,
              child: Text('$count',
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                      fontSize: T.fsBody,
                      fontWeight: FontWeight.bold,
                      color: T.text)),
            ),
          ],
        ),
      ),
    );
  }
}

class _Slice {
  final double fraction;
  final Color color;

  const _Slice(this.fraction, this.color);
}

/// Кольцевая диаграмма причин с подписями долей.
class _DonutPainter extends CustomPainter {
  final List<_Slice> slices;

  _DonutPainter(this.slices);

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2;
    final ring = radius * 0.45;
    var start = -math.pi / 2;

    for (final s in slices) {
      final sweep = s.fraction * 2 * math.pi;
      final paint = Paint()
        ..color = s.color
        ..style = PaintingStyle.stroke
        ..strokeWidth = ring;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius - ring / 2),
        start,
        sweep - 0.02,
        false,
        paint,
      );

      if (s.fraction >= 0.06) {
        final mid = start + sweep / 2;
        final pos = Offset(
          center.dx + (radius - ring / 2) * math.cos(mid),
          center.dy + (radius - ring / 2) * math.sin(mid),
        );
        final tp = TextPainter(
          text: TextSpan(
            text: '${(s.fraction * 100).round()}%',
            style: const TextStyle(
              fontSize: T.fsChip,
              fontWeight: FontWeight.bold,
              color: Color(0xFF10101A),
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas, pos - Offset(tp.width / 2, tp.height / 2));
      }
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter old) => true;
}
