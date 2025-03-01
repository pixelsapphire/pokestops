import 'package:flutter/cupertino.dart';
import 'package:intl/intl.dart';
import 'package:pokecon/data/discovery.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/ui/widgets/macos_list_table.dart';
import 'package:pokecon/ui/widgets/macos_tab_page.dart';
import 'package:pokecon/ui/widgets/zone_view.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/convert_case.dart';
import 'package:pokecon/util/ui_utils.dart';

class LinesPage extends StatelessWidget {
  final Player player;

  const LinesPage(this.player, {super.key});

  @override
  Widget build(BuildContext context) => MacosTabPage(
        actions: [
          MacosTabActionButton(icon: CupertinoIcons.add, onPressed: () {}),
          MacosTabActionButton(icon: CupertinoIcons.minus),
        ],
        child: StreamBuilder<List<LineDiscovery>>(
          stream: BackendService.playerLines(player.nickname).stream,
          initialData: [],
          builder: (context, vehicles) => MacOSListTable(
            columnWidths: [FlexColumnWidth(1), FlexColumnWidth(0.75), FlexColumnWidth(3), FixedColumnWidth(64)],
            headers: [
              MacosListTableHeader(const Text('Date')),
              MacosListTableHeader(const Text('Number')),
              MacosListTableHeader(const Text('Route')),
              MacosListTableHeader(const Text('Zones')),
            ],
            children: [
              for (final LineDiscovery discovery in vehicles.data!)
                TableRow(
                  children: [
                    Text(DateFormat('d MMM yyyy').format(discovery.date)),
                    Text(discovery.item.number),
                    Text(
                      discovery.item.terminals
                          .toCapitalizedCase()
                          .replaceAllMapped(RegExp(r'([A-Z][a-z]{2})(\s|$)'), (m) => m.group(0)!.toUpperCase()),
                      style: TextStyle(color: getSecondaryColor(context)),
                    ),
                    ZonesView(zones: discovery.item.zones),
                  ],
                ),
            ],
          ),
        ),
      );
}
