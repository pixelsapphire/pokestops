import 'dart:io';
import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/data/server_status.dart';
import 'package:pokecon/ui/pages/compilation_page.dart';
import 'package:pokecon/ui/pages/domain_page.dart';
import 'package:pokecon/ui/pages/player_page/player_page.dart';
import 'package:pokecon/ui/pages/raid_page.dart';
import 'package:pokecon/ui/pages/update_page.dart';
import 'package:pokecon/ui/pages/vehicles_page.dart';
import 'package:pokecon/ui/pages/welcome_page.dart';
import 'package:pokecon/ui/widgets/circle_indicator.dart';
import 'package:pokecon/util/backend_service.dart';
import 'package:pokecon/util/ui_utils.dart';

class Navigation extends StatelessWidget {
  const Navigation({super.key});

  @override
  Widget build(BuildContext context) {
    return const Placeholder();
  }
}

class MainWindow extends StatefulWidget {
  const MainWindow({super.key});

  @override
  State<MainWindow> createState() => _MainWindowState();
}

class _MainWindowState extends State<MainWindow> {
  int pageIndex = 0;

  late final searchFieldController = TextEditingController();

  @override
  Widget build(BuildContext context) => PlatformMenuBar(
        menus: (kIsWeb || !Platform.isMacOS)
            ? []
            : const [
                PlatformMenu(
                  label: 'PokeCon',
                  menus: [
                    PlatformProvidedMenuItem(type: PlatformProvidedMenuItemType.about),
                    PlatformProvidedMenuItem(type: PlatformProvidedMenuItemType.quit),
                  ],
                ),
                PlatformMenu(
                  label: 'View',
                  menus: [
                    PlatformProvidedMenuItem(type: PlatformProvidedMenuItemType.toggleFullScreen),
                  ],
                ),
                PlatformMenu(
                  label: 'Window',
                  menus: [
                    PlatformProvidedMenuItem(type: PlatformProvidedMenuItemType.minimizeWindow),
                    PlatformProvidedMenuItem(type: PlatformProvidedMenuItemType.zoomWindow),
                  ],
                ),
              ],
        child: FutureBuilder<List<Player>>(
          future: BackendService.players.future,
          initialData: [],
          builder: (context, players) => MacosWindow(
            sidebarState: NSVisualEffectViewState.active,
            sidebar: Sidebar(
              minWidth: 200,
              builder: (context, scrollController) => SidebarItems(
                currentIndex: pageIndex,
                onChanged: (i) => setState(() => pageIndex = i),
                scrollController: scrollController,
                itemSize: SidebarItemSize.large,
                items: [
                  SidebarItem(
                    leading: MacosIcon(CupertinoIcons.home),
                    label: Text('Home'),
                  ),
                  SidebarItem(
                    leading: MacosIcon(Icons.cloud_sync_outlined),
                    label: Text('Data update'),
                  ),
                  SidebarItem(
                    leading: MacosIcon(CupertinoIcons.gear),
                    label: Text('Page compilation'),
                  ),
                  SidebarItem(
                    leading: MacosIcon(Icons.route_outlined),
                    label: Text('Raid tools'),
                  ),
                  SidebarItem(
                    leading: MacosIcon(Icons.table_chart_outlined),
                    label: Text('Domain'),
                    section: true,
                    expandDisclosureItems: true,
                    disclosureItems: [
                      SidebarItem(
                        leading: MacosIcon(Icons.map_outlined),
                        label: Text('Overview'),
                      ),
                      SidebarItem(
                        leading: MacosIcon(Icons.directions_bus_outlined),
                        label: Text('Vehicles'),
                      ),
                    ],
                  ),
                  SidebarItem(
                    leading: MacosIcon(CupertinoIcons.person_2),
                    label: Text('Players data'),
                    section: true,
                    expandDisclosureItems: true,
                    disclosureItems: [
                      if (players.hasData)
                        ...players.data!.map(
                          (player) => SidebarItem(
                            leading: CircleIndicator(size: 10, color: player.color),
                            label: Text(player.nickname),
                          ),
                        )
                    ],
                  ),
                ],
              ),
              bottom: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const MacosListTile(
                    leading: MacosIcon(CupertinoIcons.profile_circled),
                    title: Text('Sapphire'),
                    subtitle: Text('@pixelsapphire'),
                  ),
                  const SizedBox(height: 16),
                  StreamBuilder(
                    stream: BackendService.serverStatus.stream,
                    initialData: ServerStatus.connecting,
                    builder: (context, status) {
                      return Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleIndicator(size: 8, color: status.data!.color),
                          const SizedBox(width: 6),
                          Text('server status: ${status.data!.name}', style: getTertiaryTypography(context).caption2),
                        ],
                      );
                    },
                  ),
                ],
              ),
            ),
            child: [
              const WelcomePage(),
              const UpdatePage(),
              const CompilationPage(),
              const RaidPage(),
              const DomainOverviewPage(),
              const VehiclesPage(),
              if (players.hasData) ...players.data!.map((player) => PlayerPage(player: player)),
            ][pageIndex],
          ),
        ),
      );
}
