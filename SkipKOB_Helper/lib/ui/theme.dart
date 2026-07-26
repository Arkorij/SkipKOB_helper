import 'package:flutter/material.dart';

/// Палитра тёмной темы — те же цвета, что в Python-версии.
class T {
  static const bg = Color(0xFF0F0F17);
  static const surface = Color(0xFF1A1A26);
  static const surface2 = Color(0xFF232333);
  static const surface3 = Color(0xFF2D2D40);
  static const accent = Color(0xFF7C8CF8);
  static const text = Color(0xFFECECF2);
  static const textCons = Color(0xFFC7C7D6);
  static const textDim = Color(0xFF9A9AB0);
  static const border = Color(0xFF33334A);

  static const oddColor = Color(0xFFFFD54F); // янтарный
  static const evenColor = Color(0xFF4DB6AC); // бирюзовый

  static const radius = 16.0;

  // размеры шрифтов
  static const fsTitle = 22.0;
  static const fsValue = 28.0;
  static const fsSection = 17.0;
  static const fsBody = 15.0;
  static const fsLabel = 14.0;
  static const fsHint = 13.0;
  static const fsChip = 11.0;
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: T.accent,
    brightness: Brightness.dark,
  ).copyWith(surface: T.bg);

  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    colorScheme: scheme,
    scaffoldBackgroundColor: T.bg,
    fontFamily: 'Roboto',
    splashFactory: InkSparkle.splashFactory,
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: T.surface,
      indicatorColor: T.accent.withValues(alpha: 0.25),
      labelTextStyle: WidgetStateProperty.all(
        const TextStyle(fontSize: 12, color: T.text),
      ),
      iconTheme: WidgetStateProperty.resolveWith(
        (states) => IconThemeData(
          color: states.contains(WidgetState.selected) ? T.accent : T.textDim,
        ),
      ),
    ),
    dialogTheme: const DialogThemeData(backgroundColor: T.surface),
    snackBarTheme: const SnackBarThemeData(
      backgroundColor: T.surface3,
      contentTextStyle: TextStyle(color: T.text),
      behavior: SnackBarBehavior.floating,
    ),
  );
}

/// Карточка — базовый блок интерфейса.
class Panel extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;

  const Panel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: T.surface,
        borderRadius: BorderRadius.circular(T.radius),
        border: Border.all(color: borderColor ?? T.border),
      ),
      child: child,
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;

  const SectionTitle(this.text, {super.key});

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: const TextStyle(
          fontSize: T.fsSection,
          fontWeight: FontWeight.bold,
          color: T.textDim,
        ),
      );
}

/// Цветная плашка: тип занятия, чётность недели и т.п.
class Chip2 extends StatelessWidget {
  final String label;
  final Color color;
  final double fontSize;

  const Chip2(this.label, this.color, {super.key, this.fontSize = T.fsChip});

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: fontSize,
            fontWeight: FontWeight.bold,
            color: const Color(0xFF10101A),
          ),
        ),
      );
}
