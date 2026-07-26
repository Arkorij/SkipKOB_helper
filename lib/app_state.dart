import 'package:flutter/foundation.dart';

import 'core/store.dart';

/// Общее состояние: данные приложения + уведомление страниц об изменениях.
class AppState extends ChangeNotifier {
  AppData data;

  AppState(this.data);

  static Future<AppState> load() async => AppState(await Store.load());

  /// Сохранить на диск и перерисовать зависимые страницы.
  Future<void> persist({bool notify = true}) async {
    await Store.save(data);
    if (notify) notifyListeners();
  }

  Future<void> replace(AppData newData) async {
    data = newData;
    await persist();
  }

  void touch() => notifyListeners();
}
