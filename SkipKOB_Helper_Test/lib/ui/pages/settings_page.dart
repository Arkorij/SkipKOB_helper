import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../app_state.dart';
import '../../core/calendar.dart';
import '../../core/models.dart';
import '../../core/stats.dart';
import '../../core/store.dart';
import '../theme.dart';

class SettingsPage extends StatefulWidget {
  final AppState state;

  const SettingsPage({super.key, required this.state});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late TextEditingController _yearCtl;
  final Map<String, TextEditingController> _schedCtl = {};
  String _parity = 'odd';

  AppState get _s => widget.state;
  AppData get _data => widget.state.data;

  @override
  void initState() {
    super.initState();
    _yearCtl = TextEditingController(text: '${_data.academicYearStart}');
    _rebuildScheduleControllers();
  }

  void _rebuildScheduleControllers() {
    for (final parity in ['odd', 'even']) {
      for (final d in dayKeys) {
        final pairs = _data.baseSchedule[parity]?[d] ?? const <Pair>[];
        _schedCtl['$parity/$d'] =
            TextEditingController(text: pairs.map((p) => p.format()).join('\n'));
      }
    }
  }

  @override
  void dispose() {
    _yearCtl.dispose();
    for (final c in _schedCtl.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _yearCard(),
        const SizedBox(height: 18),
        _breaksCard(),
        const SizedBox(height: 18),
        _scheduleCard(),
        const SizedBox(height: 18),
        _interfaceCard(),
        const SizedBox(height: 18),
        _filesCard(),
        const SizedBox(height: 18),
        _dangerCard(),
      ],
    );
  }

  Widget _yearCard() => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Учебный год'),
            const SizedBox(height: 8),
            const Text(
              'Год, в котором 1 сентября. По нему строится весь календарь (недели 1–40).',
              style: TextStyle(fontSize: T.fsHint, color: T.textDim),
            ),
            const SizedBox(height: 10),
            Row(children: [
              SizedBox(
                width: 130,
                child: TextField(
                  controller: _yearCtl,
                  keyboardType: TextInputType.number,
                  style: const TextStyle(fontSize: T.fsBody, color: T.text),
                  decoration: const InputDecoration(border: OutlineInputBorder()),
                ),
              ),
              const SizedBox(width: 10),
              OutlinedButton(
                onPressed: () {
                  final y = int.tryParse(_yearCtl.text.trim());
                  if (y == null) {
                    _toast('Год должен быть числом');
                    return;
                  }
                  _data.academicYearStart = y;
                  _s.persist();
                  _toast('Учебный год: 1 сентября $y');
                },
                child: const Text('Применить'),
              ),
            ]),
          ],
        ),
      );

  Widget _breaksCard() => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Каникулы'),
            const SizedBox(height: 8),
            const Text(
              'На каникулах нумерация недель не идёт. Формат дат: ГГГГ-ММ-ДД.',
              style: TextStyle(fontSize: T.fsHint, color: T.textDim),
            ),
            const SizedBox(height: 10),
            if (_data.breaks.isEmpty)
              const Text('Каникулы не заданы',
                  style: TextStyle(
                      fontSize: T.fsHint,
                      color: T.textDim,
                      fontStyle: FontStyle.italic))
            else
              for (var i = 0; i < _data.breaks.length; i++)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(children: [
                    Expanded(child: Text(isoDate(_data.breaks[i].start),
                        style: const TextStyle(color: T.text))),
                    const Text('—', style: TextStyle(color: T.textDim)),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.only(left: 8),
                        child: Text(isoDate(_data.breaks[i].end),
                            style: const TextStyle(color: T.text)),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline,
                          color: Color(0xFFE57373)),
                      onPressed: () {
                        setState(() => _data.breaks.removeAt(i));
                        _s.persist();
                      },
                    ),
                  ]),
                ),
            const SizedBox(height: 4),
            OutlinedButton.icon(
              onPressed: _addBreak,
              icon: const Icon(Icons.add),
              label: const Text('Добавить период'),
            ),
          ],
        ),
      );

  Future<void> _addBreak() async {
    final now = DateTime.now();
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime(now.year - 2),
      lastDate: DateTime(now.year + 2),
      helpText: 'Период каникул',
    );
    if (range == null) return;
    setState(() => _data.breaks.add(Break(range.start, range.end)));
    await _s.persist();
  }

  Widget _scheduleCard() => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Базовое расписание'),
            const SizedBox(height: 8),
            const Text(
              'Пары по одной в строке. Префиксы: # — консультация, * — практика, ~ — лаб (без знака — лекция).',
              style: TextStyle(fontSize: T.fsHint, color: T.textDim),
            ),
            const SizedBox(height: 10),
            Row(children: [
              _parityButton('odd', 'Нечётная'),
              const SizedBox(width: 8),
              _parityButton('even', 'Чётная'),
            ]),
            const SizedBox(height: 10),
            for (final d in dayKeys)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: TextField(
                  controller: _schedCtl['$_parity/$d'],
                  maxLines: 8,
                  minLines: 1,
                  style: const TextStyle(fontSize: T.fsBody, color: T.text),
                  decoration: InputDecoration(
                    labelText: dayNamesRu[d],
                    border: const OutlineInputBorder(),
                  ),
                ),
              ),
            FilledButton.icon(
              onPressed: _saveSchedule,
              icon: const Icon(Icons.save_outlined),
              label: const Text('Сохранить расписание'),
            ),
          ],
        ),
      );

  Widget _parityButton(String value, String label) {
    final active = _parity == value;
    return TextButton(
      onPressed: () => setState(() => _parity = value),
      style: TextButton.styleFrom(
        backgroundColor: active ? T.accent : T.surface2,
        foregroundColor: active ? const Color(0xFF10101A) : T.textDim,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
      child: Text(label),
    );
  }

  void _saveSchedule() {
    for (final parity in ['odd', 'even']) {
      for (final d in dayKeys) {
        final text = _schedCtl['$parity/$d']?.text ?? '';
        _data.baseSchedule[parity]![d] = text
            .split('\n')
            .where((l) => l.trim().isNotEmpty)
            .map(parsePair)
            .toList();
      }
    }
    _s.persist();
    _toast('Базовое расписание сохранено');
  }

  Widget _interfaceCard() => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Интерфейс'),
            const SizedBox(height: 10),
            Row(children: [
              Switch(
                value: _data.swipePages,
                activeColor: T.accent,
                onChanged: (v) {
                  setState(() => _data.swipePages = v);
                  _s.persist();
                  _toast(v ? 'Свайп страниц включён' : 'Свайп страниц выключен');
                },
              ),
              const SizedBox(width: 6),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Свайп между страницами',
                        style: TextStyle(fontSize: T.fsBody, color: T.text)),
                    Text('Листать страницы влево-вправо: контент едет за пальцем.',
                        style: TextStyle(fontSize: T.fsHint, color: T.textDim)),
                  ],
                ),
              ),
            ]),
          ],
        ),
      );

  Widget _filesCard() => Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Файлы'),
            const SizedBox(height: 10),
            Wrap(spacing: 10, runSpacing: 10, children: [
              OutlinedButton.icon(
                onPressed: _exportSchedule,
                icon: const Icon(Icons.upload_file),
                label: const Text('Экспорт расписания'),
              ),
              OutlinedButton.icon(
                onPressed: _importSchedule,
                icon: const Icon(Icons.download),
                label: const Text('Импорт расписания'),
              ),
            ]),
            const Divider(height: 20, color: T.border),
            FilledButton.icon(
              onPressed: _exportReport,
              icon: const Icon(Icons.description_outlined),
              label: const Text('Экспорт отчёта (Markdown)'),
            ),
          ],
        ),
      );

  Future<void> _exportSchedule() async {
    try {
      final bytes = utf8.encode(
          const JsonEncoder.withIndent('  ').convert(_data.baseToJson()));
      final path = await FilePicker.saveFile(
        dialogTitle: 'Сохранить расписание',
        fileName: 'skipkob_schedule.conf',
        bytes: bytes,
      );
      if (path != null) {
        // на desktop файл не пишется автоматически — дописываем сами
        final f = File(path);
        if (!await f.exists() || await f.length() == 0) {
          await f.writeAsBytes(bytes);
        }
        _toast('Расписание экспортировано');
      }
    } catch (e) {
      _toast('Ошибка экспорта: $e');
    }
  }

  Future<void> _importSchedule() async {
    try {
      final res = await FilePicker.pickFiles(
        dialogTitle: 'Выбрать файл расписания',
        type: FileType.custom,
        allowedExtensions: ['conf', 'json'],
      );
      final path = res?.files.single.path;
      if (path == null) return;
      final raw = jsonDecode(await File(path).readAsString());
      if (raw is! Map<String, dynamic>) {
        _toast('Файл не похож на расписание');
        return;
      }
      _data.applyBase(raw);
      await _s.persist();
      _rebuildScheduleControllers();
      setState(() {});
      _toast('Расписание импортировано');
    } catch (e) {
      _toast('Ошибка импорта: $e');
    }
  }

  Future<void> _exportReport() async {
    try {
      final bytes = utf8.encode(buildReport(_data));
      final path = await FilePicker.saveFile(
        dialogTitle: 'Сохранить отчёт',
        fileName: 'skipkob_report.md',
        bytes: bytes,
      );
      if (path != null) {
        final f = File(path);
        if (!await f.exists() || await f.length() == 0) {
          await f.writeAsBytes(bytes);
        }
        _toast('Отчёт сохранён');
      }
    } catch (e) {
      _toast('Ошибка: $e');
    }
  }

  Widget _dangerCard() => Panel(
        borderColor: const Color(0xFFB71C1C),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SectionTitle('Опасная зона'),
            const SizedBox(height: 8),
            const Text(
              'Полный сброс удалит расписание, каникулы и все отметки прогулов.',
              style: TextStyle(fontSize: T.fsHint, color: T.textDim),
            ),
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: _resetFlow,
              icon: const Icon(Icons.delete_forever),
              label: const Text('Полный сброс'),
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFEF5350),
                side: const BorderSide(color: Color(0xFFEF5350)),
              ),
            ),
          ],
        ),
      );

  Future<void> _resetFlow() async {
    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => const _ResetDialog(),
    );
    if (confirmed != true) return;
    final fresh = await Store.reset();
    await _s.replace(fresh);
    _rebuildScheduleControllers();
    _yearCtl.text = '${_data.academicYearStart}';
    setState(() {});
    _toast('Все данные сброшены');
  }
}

/// Подтверждение сброса с обратным отсчётом — чтобы не нажать случайно.
class _ResetDialog extends StatefulWidget {
  const _ResetDialog();

  @override
  State<_ResetDialog> createState() => _ResetDialogState();
}

class _ResetDialogState extends State<_ResetDialog> {
  int _left = 3;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      setState(() => _left--);
      if (_left <= 0) t.cancel();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ready = _left <= 0;
    return AlertDialog(
      backgroundColor: T.surface,
      icon: const Icon(Icons.warning_amber_rounded,
          color: Color(0xFFEF5350), size: 40),
      title: const Text('Полный сброс', style: TextStyle(color: T.text)),
      content: Text(
        'Это действие необратимо. Все отметки, расписание и каникулы будут удалены.'
        '${ready ? '' : '\nКнопка станет активной через $_left с.'}',
        style: const TextStyle(color: T.textDim, fontSize: T.fsBody),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Отмена'),
        ),
        FilledButton(
          onPressed: ready ? () => Navigator.pop(context, true) : null,
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFFEF5350),
            foregroundColor: const Color(0xFF10101A),
          ),
          child: Text(ready ? 'Сбросить всё' : 'Подождите… $_left'),
        ),
      ],
    );
  }
}
