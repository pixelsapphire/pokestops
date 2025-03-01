import 'package:flutter/cupertino.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/ui/pages/basic_page.dart';
import 'package:pokecon/ui/pages/player_page/player_ev_stops_page.dart';
import 'package:pokecon/ui/pages/player_page/player_lines_page.dart';
import 'package:pokecon/ui/pages/player_page/player_stops_page.dart';
import 'package:pokecon/ui/pages/player_page/player_vehicles_page.dart';

class PlayerPage extends StatelessWidget {
  final Player player;

  const PlayerPage({super.key, required this.player});

  @override
  Widget build(BuildContext context) => BasicPage(
        scrollable: false,
        title: player.nickname,
        child: MacosTabView(
          controller: MacosTabController(length: 5),
          tabs: const [
            MacosTab(label: 'Stops'),
            MacosTab(label: 'EV stops'),
            MacosTab(label: 'Vehicles'),
            MacosTab(label: 'Lines'),
            MacosTab(label: 'Terminals'),
          ],
          children: [
            PlayerStopsPage(player),
            EVStopsPage(player),
            VehiclesPage(player),
            LinesPage(player),
            Placeholder(),
          ],
        ),
      );
}
