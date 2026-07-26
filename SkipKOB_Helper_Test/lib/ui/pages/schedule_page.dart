import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app_state.dart';
import '../../core/calendar.dart';
import '../../core/models.dart';
import '../../core/resolver.dart';
import '../../core/store.dart';
import '../theme.dart';

/// Сколько нужно оттянуть список за край, чтобы сменить неделю.
const overTrigger = 75.0;
const edgeZone = 90.0;
const pullBarWidth = 150.0;

/// Упругая физика для списка дней.
///
/// Нужна именно она, а не стандартная для Android: при clamping-физике список
/// не сдвигается за край вообще, поэтому протягивание нельзя ни увидеть, ни
/// отмотать назад. С упругой список едет за пальцем в обе стороны, а индикатор
/// просто повторяет его смещение.
const pullPhysics = BouncingScrollPhysics(
  parent: AlwaysScrollableScrollPhysics(),
);

class SchedulePage extends StatefulWidget {
  final AppState state;

  const SchedulePage({super.key, required this.state});

  @override
  State<SchedulePage> createState() => _SchedulePageState();
}

class _SchedulePageState extends State<SchedulePage> {
  late int _week;

  /// Текущее смещение списка за край, px. Следует за пальцем в обе стороны.
  double _over = 0;
  bool _pullDown = true;
  DateTime _lastSwitch = DateTime.fromMillisecondsSinceEpoch(0);

  AppState get _s => widget.state;
  AppData get _data => widget.state.data;

  @override
  void initState() {
    super.initState();
    final last = _data.lastWeek;
    _week = (last != null && last >= 1 && last <= totalWeeks)
        ? last
        : currentWeekNumber(_data.academicYearStart, _data.breaks);
  }

  void _changeWeek(int delta) {
    final target = math.max(1, math.min(totalWeeks, _week + delta));
    if (target == _week) return;
    _goToWeek(target);
  }

  void _goToWeek(int n) {
    setState(() {
      _week = n;
      _over = 0;
      _lastSwitch = DateTime.now();
    });
    _data.lastWeek = n;
    _s.persist(notify: false);
  }

  /// Протягивание за край — источник правды не накопленные события, а само
  /// смещение списка за границу.
  ///
  /// Поэтому индикатор ведёт себя «на шарнирах»: тянешь дальше — растёт, ведёшь
  /// палец назад — уменьшается, отпустил — уезжает вместе с отпружиниванием
  /// списка. Смена недели срабатывает только пока палец на экране: у инерции
  /// dragDetails пуст, иначе неделя менялась бы сама после броска.
  bool _onNotification(ScrollNotification n) {
    final m = n.metrics;
    var over = 0.0;
    var down = _pullDown;
    if (m.pixels > m.maxScrollExtent) {
      over = m.pixels - m.maxScrollExtent; // тянем за низ
      down = true;
    } else if (m.pixels < m.minScrollExtent) {
      over = m.minScrollExtent - m.pixels; // тянем за верх
      down = false;
    }
    if (n is ScrollEndNotification) over = 0;

    if (over != _over || down != _pullDown) {
      setState(() {
        _over = over;
        _pullDown = down;
      });
    }

    final dragging = (n is ScrollUpdateNotification && n.dragDetails != null) ||
        (n is OverscrollNotification && n.dragDetails != null);
    if (!dragging) return false;
    if (DateTime.now().difference(_lastSwitch).inMilliseconds < 700) return false;
    if (over >= overTrigger) _changeWeek(down ? 1 : -1);
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final dates = datesForWeek(_data.academicYearStart, _data.breaks, _week);
    return Column(
      children: [
        _header(),
        Expanded(
          child: NotificationListener<ScrollNotification>(
            onNotification: _onNotification,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 180),
              switchInCurve: Curves.easeOut,
              child: ListView(
                key: ValueKey(_week),
                physics: pullPhysics,
                padding: const EdgeInsets.all(14),
                children: [
                  _edgeHint(up: true),
                  for (final d in dates) ...[
                    _DayCard(
                      state: _s,
                      day: d,
                      week: _week,
                      onChanged: () => setState(() {}),
                    ),
                    const SizedBox(height: 12),
                  ],
                  _edgeHint(up: false),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _header() {
    final odd = isOdd(_week);
    return Container(
      color: T.surface,
      padding: const EdgeInsets.only(left: 14, right: 4, top: 10, bottom: 10),
      child: Row(
        children: [
          Text('Неделя $_week',
              style: const TextStyle(
                  fontSize: T.fsSection,
                  fontWeight: FontWeight.bold,
                  color: T.text)),
          const SizedBox(width: 8),
          Chip2(parityLabel(_week), odd ? T.oddColor : T.evenColor),
          const Spacer(),
          InkWell(
            onTap: _openWeekPicker,
            borderRadius: BorderRadius.circular(10),
            child: Container(
              padding: const EdgeInsets.only(left: 12, right: 4, top: 8, bottom: 8),
              decoration: BoxDecoration(
                border: Border.all(color: T.border),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Text('$_week',
                    style: const TextStyle(
                        fontSize: T.fsLabel,
                        fontWeight: FontWeight.bold,
                        color: T.text)),
                const Icon(Icons.arrow_drop_down, size: 20, color: T.textDim),
              ]),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.keyboard_arrow_up, size: 22, color: T.textDim),
            tooltip: 'Прошлая неделя',
            onPressed: () => _changeWeek(-1),
          ),
          IconButton(
            icon: const Icon(Icons.keyboard_arrow_down, size: 22, color: T.textDim),
            tooltip: 'Следующая неделя',
            onPressed: () => _changeWeek(1),
          ),
        ],
      ),
    );
  }

  /// Зона-подсказка у края с индикатором протягивания.
  Widget _edgeHint({required bool up}) {
    final active = up ? !_pullDown : _pullDown;
    final frac = active ? math.min(1.0, _over / overTrigger) : 0.0;
    final ready = frac >= 1.0;
    final color = ready ? T.accent : (frac > 0 ? const Color(0xFF90A4AE) : T.textDim);
    return SizedBox(
      height: edgeZone,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(up ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
              size: 22, color: color),
          Text(up ? 'Прошлая неделя' : 'Следующая неделя',
              style: TextStyle(fontSize: T.fsHint, color: color)),
          const SizedBox(height: 6),
          Container(
            width: pullBarWidth,
            height: 4,
            decoration: BoxDecoration(
              color: T.surface2,
              borderRadius: BorderRadius.circular(3),
            ),
            alignment: Alignment.centerLeft,
            // без анимации: полоска повторяет смещение списка, а плавность
            // на отпускании даёт само отпружинивание
            child: Container(
              width: pullBarWidth * frac,
              height: 4,
              decoration: BoxDecoration(
                color: ready ? T.accent : const Color(0xFF90A4AE),
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _openWeekPicker() async {
    final picked = await showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: T.surface,
        title: const Text('Выбор недели',
            style: TextStyle(color: T.text, fontSize: T.fsSection)),
        content: SizedBox(
          width: 300,
          height: 400,
          child: Scrollbar(
            thumbVisibility: true, // полоса прокрутки видна всегда
            child: SingleChildScrollView(
              padding: const EdgeInsets.only(right: 10),
              child: Column(
                children: [
                  // по два в ряду: слева нечётная, справа чётная
                  for (var n = 1; n <= totalWeeks; n += 2)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _weekCell(ctx, n),
                          const SizedBox(width: 10),
                          _weekCell(ctx, n + 1),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Отмена'),
          ),
        ],
      ),
    );
    if (picked != null) _goToWeek(picked);
  }

  Widget _weekCell(BuildContext ctx, int n) {
    final selected = n == _week;
    final odd = isOdd(n);
    return InkWell(
      onTap: () => Navigator.pop(ctx, n),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        width: 118,
        height: 58,
        decoration: BoxDecoration(
          color: selected ? T.accent : T.surface2,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 4,
              height: 24,
              decoration: BoxDecoration(
                color: selected
                    ? const Color(0xFF10101A)
                    : (odd ? T.oddColor : T.evenColor),
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            const SizedBox(width: 10),
            Text('$n',
                style: TextStyle(
                  fontSize: T.fsSection,
                  fontWeight: selected ? FontWeight.bold : FontWeight.normal,
                  color: selected ? const Color(0xFF10101A) : T.text,
                )),
          ],
        ),
      ),
    );
  }
}

/// Карточка одного дня со списком пар.
class _DayCard extends StatelessWidget {
  final AppState state;
  final DateTime day;
  final int week;
  final VoidCallback onChanged;

  const _DayCard({
    required this.state,
    required this.day,
    required this.week,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final data = state.data;
    final pairs = pairsForDate(data, day, week);
    final marks = dayMarks(data, day, pairs);
    final isToday = dateOnly(day) == dateOnly(DateTime.now());
    final isOverride = data.overrides.containsKey(isoDate(day));
    final dayKey = dayKeys[day.weekday - 1];

    return Panel(
      borderColor: isToday ? T.accent : T.border,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(dayNamesRu[dayKey]!,
                      style: TextStyle(
                        fontSize: T.fsSection,
                        fontWeight: FontWeight.bold,
                        color: isToday ? T.accent : T.text,
                      )),
                  Text(formatDate(day),
                      style: const TextStyle(
                          fontSize: T.fsHint, color: T.textDim)),
                ],
              ),
              const Spacer(),
              if (isOverride)
                const Chip2('изменён', Color(0xFFFFB74D)),
              IconButton(
                icon: const Icon(Icons.edit_calendar_outlined,
                    size: 22, color: T.textDim),
                tooltip: 'Изменить пары этого дня',
                onPressed: () => _editDay(context, pairs),
              ),
            ],
          ),
          const Divider(height: 14, color: T.border),
          if (pairs.isEmpty)
            const Text('Нет пар',
                style: TextStyle(
                    fontSize: T.fsHint,
                    color: T.textDim,
                    fontStyle: FontStyle.italic))
          else
            for (var i = 0; i < pairs.length; i++)
              _pairRow(pairs, i, marks[i]),
        ],
      ),
    );
  }

  Widget _pairRow(List<Pair> pairs, int index, Mark mark) {
    final pair = pairs[index];
    final status = statusByKey(mark.status, consultation: pair.consultation);
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            pair.consultation
                ? const Chip2(consultationLabel, consultationColor)
                : Chip2(kindLabels[pair.kind]!, kindColors[pair.kind]!),
            const SizedBox(width: 8),
            Expanded(
              child: Text(pair.name,
                  style: TextStyle(
                    fontSize: T.fsBody,
                    color: pair.consultation ? T.textCons : T.text,
                  )),
            ),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: status?.color ?? T.textDim,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 10),
            SizedBox(
              width: 168,
              child: DropdownButtonFormField<String>(
                value: mark.status,
                isDense: true,
                dropdownColor: T.surface2,
                style: const TextStyle(fontSize: T.fsLabel, color: T.text),
                decoration: InputDecoration(
                  isDense: true,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  enabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: T.border),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: T.accent),
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                items: [
                  for (final s in pair.availableStatuses)
                    DropdownMenuItem(value: s.key, child: Text(s.label)),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setMark(state.data, day, pairs, index, value);
                  state.persist(notify: false);
                  onChanged();
                },
              ),
            ),
          ]),
        ],
      ),
    );
  }

  Future<void> _editDay(BuildContext context, List<Pair> pairs) async {
    final controller =
        TextEditingController(text: pairs.map((p) => p.format()).join('\n'));
    final action = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: T.surface,
        title: Text('${dayNamesRu[dayKeys[day.weekday - 1]]}, ${formatDate(day)}',
            style: const TextStyle(color: T.text, fontSize: T.fsSection)),
        content: SizedBox(
          width: 360,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Префиксы: # — консультация, * — практика, ~ — лаб (без знака — лекция)',
                style: TextStyle(fontSize: T.fsHint, color: T.textDim),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: controller,
                maxLines: 10,
                minLines: 5,
                style: const TextStyle(fontSize: T.fsBody, color: T.text),
                decoration: InputDecoration(
                  labelText: 'Пары (по одной в строке)',
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, 'reset'),
            style: TextButton.styleFrom(foregroundColor: const Color(0xFFE57373)),
            child: const Text('Сбросить к базе'),
          ),
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Отмена')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, 'save'),
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );

    if (action == 'save') {
      final lines = controller.text
          .split('\n')
          .where((l) => l.trim().isNotEmpty)
          .map(parsePair)
          .toList();
      state.data.overrides[isoDate(day)] = lines;
      state.data.marks.remove(isoDate(day));
      await state.persist(notify: false);
      onChanged();
    } else if (action == 'reset') {
      state.data.overrides.remove(isoDate(day));
      state.data.marks.remove(isoDate(day));
      await state.persist(notify: false);
      onChanged();
    }
  }
}
