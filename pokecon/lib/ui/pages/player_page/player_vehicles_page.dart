import 'package:flutter/cupertino.dart';
import 'package:intl/intl.dart';
import 'package:pokecon/data/discovery.dart';
import 'package:pokecon/data/objects.dart';
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
            columnWidths: [FlexColumnWidth(1), FlexColumnWidth(0.75), FlexColumnWidth(3), FlexColumnWidth(1)],
            headers: [
              MacosListTableHeader(const Text('Date')),
              MacosListTableHeader(const Text('Number')),
              MacosListTableHeader(const Text('Brand & model')),
              MacosListTableHeader(const Text('Carrier')),
            ],
            children: [
              for (final VehicleDiscovery discovery in vehicles.data!)
                TableRow(
                  children: [
                    Text(DateFormat('d MMM yyyy').format(discovery.date)),
                    Text(discovery.item.vehicleId),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: Image.asset(
                            'assets/brands/${discovery.item.brand.toLowerCase()}.webp',
                            width: 16,
                            height: 16,
                            color: getSecondaryColor(context),
                          ),
                        ),
                        Text(discovery.item.fullName, style: TextStyle(color: getSecondaryColor(context)))
                      ],
                    ),
                    StreamBuilder<Map<String, Carrier>>(
                      stream: BackendService.domainCarriers.stream,
                      builder: (context, carriers) {
                        final Carrier carrier = carriers.data?[discovery.item.carrierSymbol] ?? Carrier.unknown();
                        return Text(carrier.name);
                      },
                    ),
                  ],
                ),
            ],
          ),
        ),
      );
}
