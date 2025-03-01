import 'package:flutter/cupertino.dart';
import 'package:intl/intl.dart';
import 'package:pokecon/data/discovery.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/ui/widgets/macos_list_table.dart';
import 'package:pokecon/ui/widgets/macos_tab_page.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/ui_utils.dart';

class VehiclesPage extends StatelessWidget {
  final Player player;

  const VehiclesPage(this.player, {super.key});

  @override
  Widget build(BuildContext context) => MacosTabPage(
        actions: [
          MacosTabActionButton(icon: CupertinoIcons.add, onPressed: () {}),
          MacosTabActionButton(icon: CupertinoIcons.minus),
        ],
        child: StreamBuilder<List<VehicleDiscovery>>(
          stream: BackendService.playerVehicles(player.nickname).stream,
          initialData: [],
          builder: (context, vehicles) => MacOSListTable(
            columnWidths: [FlexColumnWidth(1), FlexColumnWidth(1), FlexColumnWidth(3)],
            headers: [
              MacosListTableHeader(const Text('Date')),
              MacosListTableHeader(const Text('Number')),
              MacosListTableHeader(const Text('Brand & model')),
            ],
            children: [
              for (final VehicleDiscovery discovery in vehicles.data!)
                TableRow(
                  children: [
                    Text(DateFormat('yyyy-MM-dd').format(discovery.date)),
                    Text(discovery.item.vehicleId),
                    Text(discovery.item.fullName, style: TextStyle(color: getSecondaryColor(context))),
                  ],
                ),
            ],
          ),
        ),
      );
}
