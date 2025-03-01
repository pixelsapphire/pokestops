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
        action: () => compileAction().then(
          (result) => {
            if (context.mounted)
              showResultDialog(
                context: context,
                title: result.success
                    ? (result.errors.isEmpty ? 'Compilation finished' : 'Compilation finished with warnings')
                    : 'Compilation failed',
                error: result.failureCause,
                warnings: result.errors,
              ),
          },
        ),
      );
}
