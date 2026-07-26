import 'package:flutter/material.dart';

import 'app_state.dart';
import 'ui/pages/schedule_page.dart';
import 'ui/pages/settings_page.dart';
import 'ui/pages/stats_page.dart';
import 'ui/theme.dart';

/// Переход по кнопке нижней панели.
const navDuration = Duration(milliseconds: 130);

/// Пружина доводки свайпа.
///
/// Ровно то, ради чего затевалась версия на Dart: у Flutter в PageScrollPhysics
/// пружина намеренно тяжёлая (масса 80, жёсткость 100) — палец отпускаешь, а
/// страница ещё долго доезжает, и следующее касание перехватывается. Через Flet
/// её было не достать. Здесь ставим свою: лёгкую, жёсткую и слегка
/// передемпфированную, чтобы доводка добивалась быстро и без отскока.
final snappySpring = SpringDescription.withDampingRatio(
  mass: 0.26,
  stiffness: 820,
  ratio: 1.15,
);

class SnappyPageScrollPhysics extends PageScrollPhysics {
  const SnappyPageScrollPhysics({super.parent});

  @override
  SnappyPageScrollPhysics applyTo(ScrollPhysics? ancestor) =>
      SnappyPageScrollPhysics(parent: buildParent(ancestor));

  @override
  SpringDescription get spring => snappySpring;
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final state = await AppState.load();
  runApp(SkipKobApp(state: state));
}

class SkipKobApp extends StatelessWidget {
  final AppState state;

  const SkipKobApp({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SkipKOB Helper',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: HomeShell(state: state),
    );
  }
}

class HomeShell extends StatefulWidget {
  final AppState state;

  const HomeShell({super.key, required this.state});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _controller = PageController();
  int _index = 0;

  @override
  void initState() {
    super.initState();
    widget.state.addListener(_onStateChanged);
  }

  @override
  void dispose() {
    widget.state.removeListener(_onStateChanged);
    _controller.dispose();
    super.dispose();
  }

  void _onStateChanged() => setState(() {});

  void _goTo(int index) {
    _controller.animateToPage(
      index,
      duration: navDuration,
      curve: Curves.easeOutCubic,
    );
  }

  @override
  Widget build(BuildContext context) {
    final swipeOn = widget.state.data.swipePages;
    return Scaffold(
      backgroundColor: T.bg,
      body: SafeArea(
        bottom: false,
        child: PageView(
          controller: _controller,
          // Соседние страницы строятся заранее и остаются живыми. Без этого
          // PageView создаёт страницу в тот момент, когда начинается жест, —
          // а страницы тяжёлые (списки строятся целиком, много выпадающих
          // списков), отсюда заминка в самом начале свайпа.
          allowImplicitScrolling: true,
          // свайп можно выключить: страницы останутся, листаются только кнопками
          physics: swipeOn
              ? const SnappyPageScrollPhysics()
              : const NeverScrollableScrollPhysics(),
          onPageChanged: (i) => setState(() => _index = i),
          children: [
            StatsPage(state: widget.state),
            SchedulePage(state: widget.state),
            SettingsPage(state: widget.state),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _goTo,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.insights_outlined),
            selectedIcon: Icon(Icons.insights),
            label: 'Статистика',
          ),
          NavigationDestination(
            icon: Icon(Icons.calendar_month_outlined),
            selectedIcon: Icon(Icons.calendar_month),
            label: 'Расписание',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Настройки',
          ),
        ],
      ),
    );
  }
}
