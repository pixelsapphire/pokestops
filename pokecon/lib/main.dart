import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/ui/main_window.dart';
import 'package:provider/provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  if (!kIsWeb && Platform.isMacOS) await MacosWindowUtilsConfig(toolbarStyle: NSWindowToolbarStyle.unified).apply();
  runApp(const PokeConApp());
}

class AppTheme extends ChangeNotifier {
  ThemeMode _mode = ThemeMode.system;

  ThemeMode get mode => _mode;

  set mode(ThemeMode mode) {
    _mode = mode;
    notifyListeners();
  }
}

class PokeConApp extends StatelessWidget {
  const PokeConApp({super.key});

  @override
  Widget build(BuildContext context) => ChangeNotifierProvider(
        create: (_) => AppTheme(),
        builder: (context, _) => MacosApp(
          title: 'macos_ui Widget Gallery',
          themeMode: context.watch<AppTheme>().mode,
          debugShowCheckedModeBanner: false,
          home: const MainWindow(),
        ),
      );
}
