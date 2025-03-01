import 'package:flutter/material.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:intl/intl.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/ui/pages/basic_page.dart';
import 'package:pokecon/ui/widgets/action_card.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/scope_functions.dart';
import 'package:pokecon/util/ui_utils.dart';

class UpdatePage extends StatelessWidget {
  const UpdatePage({super.key});

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
              _UpdateCard(
                image: 'assets/card_backgrounds/map.png',
                title: 'GTFS data',
                lastUpdateStream: BackendService.gtfsLastUpdate,
                updateAction: BackendService.updateGtfs,
              ),
              _UpdateCard(
                image: 'assets/card_backgrounds/announcement.png',
                title: 'Announcements',
                lastUpdateStream: BackendService.announcementsLastUpdate,
                updateAction: BackendService.updateAnnouncements,
              ),
              StaggeredGridTile.extent(
                crossAxisCellCount: 2,
                mainAxisExtent: 92,
                child: _UpdateCard(
                  image: 'assets/card_backgrounds/update.jpg',
                  backgroundAlignment: Alignment.centerRight,
                  title: 'Update everything',
                  updateAction: BackendService.updateAll,
                ),
              ),
              StaggeredGridTile.extent(
                crossAxisCellCount: 2,
                mainAxisExtent: 92,
                child: _UpdateCard(
                  image: 'assets/card_backgrounds/database_refresh.webp',
                  backgroundAlignment: Alignment.center,
                  title: 'Reload database',
                  updateAction: BackendService.reloadDatabase,
                  buttonText: 'Reload',
                ),
              ),
            ],
          ),
        ),
      );
}

class _UpdateCard extends StatelessWidget {
  final String image;
  final Alignment backgroundAlignment;
  final String title;
  final DynamicValue<DateTime>? lastUpdateStream;
  final Future<CommandResult> Function() updateAction;
  final String buttonText;

  const _UpdateCard({
    required this.image,
    this.backgroundAlignment = Alignment.topCenter,
    required this.title,
    this.lastUpdateStream,
    required this.updateAction,
    this.buttonText = 'Update',
  });

  @override
  Widget build(BuildContext context) => ActionCard(
        height: 128,
        imageAssetPath: image,
        backgroundAlignment: backgroundAlignment,
        title: title,
        subtitleWidget: lastUpdateStream?.let(
          (DynamicValue<DateTime> date) => StreamBuilder(
            stream: date.stream,
            builder: (_, snapshot) => Text(
              'Last update: ${snapshot.hasData ? DateFormat('yyyy-MM-dd, hh:mm a').format(snapshot.data!) : '...'}',
            ),
          ),
        ),
        buttonText: buttonText,
        action: () => updateAction().then(
          (result) => {
            if (context.mounted)
              showResultDialog(
                context: context,
                title: result.success
                    ? (result.errors.isEmpty ? 'Update finished' : 'Update finished with warnings')
                    : 'Update failed',
                error: result.failureCause,
                warnings: result.errors,
              ),
          },
        ),
      );
}
