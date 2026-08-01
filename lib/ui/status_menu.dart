import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/models.dart';
import 'theme.dart';

/// Появление меню статусов.
///
/// Штатный [DropdownButton] раскрывается 300 мс: список разворачивается,
/// подсвечивается выбранный пункт, всё это едет с затуханием. На паре, где
/// таких полей десяток, ожидание читается как «залипло». Здесь простое
/// проявление за 80 мс — глаз воспринимает его как мгновенное, но без мигания.
const _openDuration = Duration(milliseconds: 80);
const _closeDuration = Duration(milliseconds: 60);

/// Зазор между полем и меню.
const _gap = 4.0;

/// Отступ меню от краёв экрана.
const _screenPad = 8.0;

/// Поле выбора статуса пары.
///
/// Заменяет `DropdownButtonFormField`: тот на каждую пару строит `FormField`
/// с фокус-нодой и собственным маршрутом меню, а нужен всего лишь список из
/// восьми пунктов.
class StatusField extends StatelessWidget {
  final String value;
  final List<Status> options;
  final ValueChanged<String> onChanged;
  final double width;

  const StatusField({
    super.key,
    required this.value,
    required this.options,
    required this.onChanged,
    this.width = 168,
  });

  @override
  Widget build(BuildContext context) {
    final current = options.firstWhere(
      (s) => s.key == value,
      orElse: () => options.first,
    );
    return SizedBox(
      width: width,
      child: InkWell(
        onTap: () => _open(context),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          decoration: BoxDecoration(
            border: Border.all(color: T.border),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  current.label,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: T.fsLabel, color: T.text),
                ),
              ),
              const Icon(Icons.arrow_drop_down, size: 20, color: T.textDim),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _open(BuildContext context) async {
    final navigator = Navigator.of(context);
    final box = context.findRenderObject() as RenderBox?;
    final overlay =
        navigator.overlay?.context.findRenderObject() as RenderBox?;
    if (box == null || overlay == null || !box.hasSize) return;

    final anchor = box.localToGlobal(Offset.zero, ancestor: overlay) & box.size;
    final picked = await navigator.push(_StatusMenuRoute(
      anchor: anchor,
      options: options,
      current: value,
      width: math.max(width, 180),
    ));
    if (picked != null && picked != value) onChanged(picked);
  }
}

class _StatusMenuRoute extends PopupRoute<String> {
  final Rect anchor;
  final List<Status> options;
  final String current;
  final double width;

  _StatusMenuRoute({
    required this.anchor,
    required this.options,
    required this.current,
    required this.width,
  });

  @override
  Color? get barrierColor => null;

  @override
  bool get barrierDismissible => true;

  @override
  String? get barrierLabel => 'Закрыть меню';

  @override
  Duration get transitionDuration => _openDuration;

  @override
  Duration get reverseTransitionDuration => _closeDuration;

  @override
  Widget buildPage(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
  ) {
    final padding = MediaQuery.paddingOf(context);
    return CustomSingleChildLayout(
      delegate: _MenuLayout(anchor: anchor, safe: padding),
      child: _MenuPanel(options: options, current: current, width: width),
    );
  }

  @override
  Widget buildTransitions(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    // Только прозрачность: разворачивание по высоте — как раз то, что делает
    // штатный дропдаун медленным на вид.
    return FadeTransition(
      opacity: CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
      child: child,
    );
  }
}

/// Кладёт меню под поле, а если снизу не помещается — над ним.
class _MenuLayout extends SingleChildLayoutDelegate {
  final Rect anchor;
  final EdgeInsets safe;

  const _MenuLayout({required this.anchor, required this.safe});

  @override
  BoxConstraints getConstraintsForChild(BoxConstraints constraints) {
    return BoxConstraints.loose(Size(
      constraints.maxWidth - _screenPad * 2,
      constraints.maxHeight - safe.top - safe.bottom - _screenPad * 2,
    ));
  }

  @override
  Offset getPositionForChild(Size size, Size childSize) {
    final top = safe.top + _screenPad;
    final bottom = size.height - safe.bottom - _screenPad;

    var y = anchor.bottom + _gap;
    if (y + childSize.height > bottom) {
      final above = anchor.top - childSize.height - _gap;
      y = above >= top ? above : math.max(top, bottom - childSize.height);
    }

    var x = anchor.left;
    if (x + childSize.width > size.width - _screenPad) {
      x = size.width - _screenPad - childSize.width;
    }
    return Offset(math.max(_screenPad, x), y);
  }

  @override
  bool shouldRelayout(_MenuLayout old) =>
      anchor != old.anchor || safe != old.safe;
}

class _MenuPanel extends StatelessWidget {
  final List<Status> options;
  final String current;
  final double width;

  const _MenuPanel({
    required this.options,
    required this.current,
    required this.width,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: T.surface2,
      elevation: 8,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: T.border),
      ),
      child: SizedBox(
        width: width,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final s in options) _item(context, s),
            ],
          ),
        ),
      ),
    );
  }

  Widget _item(BuildContext context, Status s) {
    final selected = s.key == current;
    return InkWell(
      onTap: () => Navigator.pop(context, s.key),
      child: Container(
        color: selected ? T.surface3 : null,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        child: Row(
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(color: s.color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                s.label,
                style: TextStyle(
                  fontSize: T.fsLabel,
                  color: T.text,
                  fontWeight: selected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
