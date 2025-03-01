import 'package:flutter/cupertino.dart';
import 'package:intl/intl.dart';
import 'package:pokecon/data/discovery.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/ui/widgets/macos_list_table.dart';
import 'package:pokecon/ui/widgets/macos_tab_page.dart';
import 'package:pokecon/ui/widgets/zone_view.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/ui_utils.dart';

class PlayerStopsPage extends StatelessWidget {
  final Player player;

  const PlayerStopsPage(this.player, {super.key});

  @override
  Widget build(BuildContext context) => MacosTabPage(
        actions: [
          MacosTabActionButton(icon: CupertinoIcons.add, onPressed: () {}),
          MacosTabActionButton(icon: CupertinoIcons.minus),
        ],
        child: StreamBuilder<List<StopDiscovery>>(
          stream: BackendService.playerStops(player.nickname).stream,
          initialData: [],
          builder: (context, stops) => MacOSListTable(
            columnWidths: [FlexColumnWidth(1), FlexColumnWidth(1), FlexColumnWidth(3), FixedColumnWidth(30)],
            headers: [
              MacosListTableHeader(const Text('Date')),
              MacosListTableHeader(const Text('Identifier')),
              MacosListTableHeader(const Text('Name')),
              MacosListTableHeader(const Text('Zone')),
            ],
            children: [
              for (final StopDiscovery discovery in stops.data!)
                TableRow(
                  children: [
                    Text(DateFormat('d MMM yyyy').format(discovery.date)),
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
