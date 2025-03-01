import 'package:flutter/cupertino.dart';
import 'package:pokecon/data/discovery.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/ui/widgets/macos_list_table.dart';
import 'package:pokecon/ui/widgets/macos_tab_page.dart';
import 'package:pokecon/ui/widgets/zone_view.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/ui_utils.dart';

class EVStopsPage extends StatelessWidget {
  final Player player;

  const EVStopsPage(this.player, {super.key});

  @override
  Widget build(BuildContext context) => MacosTabPage(
        actions: [
          MacosTabActionButton(icon: CupertinoIcons.add, onPressed: () {}),
          MacosTabActionButton(icon: CupertinoIcons.minus),
        ],
        child: StreamBuilder<List<EVStopDiscovery>>(
          stream: BackendService.playerEVStops(player.nickname).stream,
          initialData: [],
          builder: (context, evStops) => MacOSListTable(
            columnWidths: [FlexColumnWidth(1), FlexColumnWidth(1.5), FixedColumnWidth(30)],
            headers: [
              MacosListTableHeader(const Text('Identifier')),
              MacosListTableHeader(const Text('Name')),
              MacosListTableHeader(const Text('Zone')),
            ],
            children: [
              for (final EVStopDiscovery discovery in evStops.data!)
                TableRow(
                  children: [
                    Text(discovery.item.shortName),
                    Text(discovery.item.fullName, style: TextStyle(color: getSecondaryColor(context))),
                    ZonesView(zones: [discovery.item.zone]),
                  ],
                ),
            ],
          ),
        ),
      );
}
