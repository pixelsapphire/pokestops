import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/ui/pages/basic_page.dart';
import 'package:pokecon/ui/widgets/action_card.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/ui_utils.dart';

class CompilationPage extends StatelessWidget {
  const CompilationPage({super.key});

  @override
  Widget build(BuildContext context) => BasicPage(
        title: 'Data update',
        padding: 32,
        child: LayoutBuilder(
          builder: (context, constraints) => StaggeredGrid.count(
            crossAxisCount: constraints.maxWidth >= 600 ? 2 : 1,
            mainAxisSpacing: 32,
            crossAxisSpacing: 32,
            children: [
              _CompileCard(
                image: 'assets/card_backgrounds/map.png',
                title: 'Pokestops Map',
                compileAction: BackendService.compileMap,
              ),
              _CompileCard(
                image: 'assets/card_backgrounds/archive.png',
                title: 'Pokestops Archive',
                compileAction: BackendService.compileArchive,
              ),
              _CompileCard(
                image: 'assets/card_backgrounds/steambird.png',
                title: 'The Steambird',
                compileAction: BackendService.compileAnnouncements,
              ),
              _CompileCard(
                image: 'assets/card_backgrounds/raids.png',
                backgroundAlignment: Alignment.topRight,
                title: 'Raider\'s Logbook',
                compileAction: BackendService.compileRaids,
              ),
              StaggeredGridTile.extent(
                crossAxisCellCount: 2,
                mainAxisExtent: 92,
                child: _CompileCard(
                  image: 'assets/card_backgrounds/code.png',
                  backgroundAlignment: Alignment.centerLeft,
                  title: 'Compile everything',
                  compileAction: BackendService.compileAll,
                ),
              ),
            ],
          ),
        ),
      );
}

class _CompileCard extends StatelessWidget {
  final String image;
  final Alignment backgroundAlignment;
  final String title;
  final Future<CommandResult> Function() compileAction;

  const _CompileCard({
    required this.image,
    this.backgroundAlignment = Alignment.topCenter,
    required this.title,
    required this.compileAction,
  });

  @override
  Widget build(BuildContext context) => ActionCard(
        height: 128,
        imageAssetPath: image,
        backgroundAlignment: backgroundAlignment,
        title: title,
        buttonText: 'Compile',
        action: () => compileAction().then((result) => {
              if (result.errors.isNotEmpty && context.mounted) _displayWarningsPane(context, result.errors),
            }),
      );
}

void _displayWarningsPane(BuildContext context, List<String> errors) {
  showMacosSheet(
    context: context,
    barrierDismissible: true,
    builder: (context) => MacosSheet(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Compilation finished with warnings', style: getPrimaryTypography(context).title2),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final error in errors)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Text(error),
                        ),
                    ],
                  ),
                ),
              ),
            ),
            TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Close')),
          ],
        ),
      ),
    ),
  );
}
