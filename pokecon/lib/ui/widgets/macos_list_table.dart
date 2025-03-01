import 'package:flutter/material.dart';
import 'package:flutter/widgets.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/ui/widgets/macos_divider.dart';
import 'package:pokecon/util/extensions.dart';
import 'package:pokecon/util/ui_utils.dart';

class MacosListTableHeader {
  final Widget label;

  const MacosListTableHeader(this.label);
}

class MacOSListTable extends StatefulWidget {
  final List<TableColumnWidth> columnWidths;
  final List<MacosListTableHeader>? headers;
  final List<TableRow> children;

  const MacOSListTable({
    super.key,
    required this.columnWidths,
    this.headers,
    required this.children,
  });

  @override
  State<MacOSListTable> createState() => _MacOSListTableState();
}

class _MacOSListTableState extends State<MacOSListTable> {
  int? _selectedRow;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          if (widget.headers != null)
            Table(
              columnWidths: [FixedColumnWidth(16), ...widget.columnWidths, FixedColumnWidth(16)].asMap(),
              children: [
                TableRow(
                  decoration: BoxDecoration(border: Border(bottom: BorderSide(color: getPrimaryColor(context).withAlpha(48)))),
                  children: [
                    const SizedBox(height: 30),
                    ...widget.headers!.mapIndexed(
                      (index, header) => TableCell(
                        verticalAlignment: TableCellVerticalAlignment.middle,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            DefaultTextStyle(style: getPrimaryTypography(context).caption2, child: header.label),
                            if (index < widget.headers!.length - 1)
                              Padding(padding: const EdgeInsets.only(right: 8), child: const MacosDivider(opacity: 0.25))
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(),
                  ],
                ),
              ],
            ),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  const SizedBox(height: 4),
                  Table(
                    columnWidths: [FixedColumnWidth(16), ...widget.columnWidths, FixedColumnWidth(16)].asMap(),
                    children: [
                      ...widget.children.mapIndexed(
                        (index, row) => TableRow(
                          key: row.key,
                          decoration: BoxDecoration(
                              color: index == _selectedRow
                                  ? SelectedColorProvider.getColor(context).withAlpha(128)
                                  : (index.isOdd ? getPrimaryColor(context).withAlpha(12) : null)),
                          children: [
                            const SizedBox(),
                            ...row.children.map(
                              (child) => GestureDetector(
                                behavior: HitTestBehavior.translucent,
                                onTap: () => setState(() => _selectedRow = index),
                                child: ConstrainedBox(
                                  constraints: BoxConstraints(minHeight: 24),
                                  child: Align(
                                    alignment: Alignment.centerLeft,
                                    child: SizedBox(width: double.infinity, child: child),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox()
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      );
}

// copied from the macos_ui package, where it is private
class SelectedColorProvider {
  static Color getColor(BuildContext context) {
    return getSelectedColor(
      accentColor: MacosTheme.of(context).accentColor ?? AccentColor.blue,
      isDarkModeEnabled: MacosTheme.of(context).brightness.isDark,
      isWindowMain: WindowMainStateListener.instance.isMainWindow,
    );
  }

  static Color getSelectedColor({
    required AccentColor accentColor,
    required bool isDarkModeEnabled,
    required bool isWindowMain,
  }) {
    if (isDarkModeEnabled) {
      if (!isWindowMain) {
        return const MacosColor.fromRGBO(76, 78, 65, 1.0);
      }

      switch (accentColor) {
        case AccentColor.blue:
          return const MacosColor.fromRGBO(22, 105, 229, 0.749);

        case AccentColor.purple:
          return const MacosColor.fromRGBO(204, 45, 202, 0.749);

        case AccentColor.pink:
          return const MacosColor.fromRGBO(229, 74, 145, 0.749);

        case AccentColor.red:
          return const MacosColor.fromRGBO(238, 64, 68, 0.749);

        case AccentColor.orange:
          return const MacosColor.fromRGBO(244, 114, 0, 0.749);

        case AccentColor.yellow:
          return const MacosColor.fromRGBO(233, 176, 0, 0.749);

        case AccentColor.green:
          return const MacosColor.fromRGBO(76, 177, 45, 0.749);

        case AccentColor.graphite:
          return const MacosColor.fromRGBO(129, 129, 122, 0.824);
      }
    }

    if (!isWindowMain) {
      return const MacosColor.fromRGBO(213, 213, 208, 1.0);
    }

    switch (accentColor) {
      case AccentColor.blue:
        return const MacosColor.fromRGBO(9, 129, 255, 0.749);

      case AccentColor.purple:
        return const MacosColor.fromRGBO(162, 28, 165, 0.749);

      case AccentColor.pink:
        return const MacosColor.fromRGBO(234, 81, 152, 0.749);

      case AccentColor.red:
        return const MacosColor.fromRGBO(220, 32, 40, 0.749);

      case AccentColor.orange:
        return const MacosColor.fromRGBO(245, 113, 0, 0.749);

      case AccentColor.yellow:
        return const MacosColor.fromRGBO(240, 180, 2, 0.749);

      case AccentColor.green:
        return const MacosColor.fromRGBO(66, 174, 33, 0.749);

      case AccentColor.graphite:
        return const MacosColor.fromRGBO(174, 174, 167, 0.847);
    }
  }
}
