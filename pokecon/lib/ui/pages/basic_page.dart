import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:macos_ui/macos_ui.dart';

class BasicPage extends StatelessWidget {
  final String title;
  final Widget child;
  final bool scrollable;
  final double padding;

  const BasicPage({super.key, required this.title, this.scrollable = true, this.padding = 0.0, required this.child});

  @override
  Widget build(BuildContext context) => MacosScaffold(
        toolBar: ToolBar(
          leading: MacosTooltip(
            message: 'Toggle Sidebar',
            useMousePosition: false,
            child: MacosIconButton(
              icon: MacosIcon(
                CupertinoIcons.sidebar_left,
                size: 20.0,
                color: MacosTheme.brightnessOf(context).resolve(Colors.black, Colors.white).withAlpha(128),
              ),
              boxConstraints: const BoxConstraints(minHeight: 20, minWidth: 20, maxWidth: 48, maxHeight: 38),
              onPressed: () => MacosWindowScope.of(context).toggleSidebar(),
            ),
          ),
          title: Text(title),
          titleWidth: 250.0,
        ),
        children: [
          ContentArea(
            builder: (context, scrollController) => Padding(
              padding: EdgeInsets.all(padding),
              child: scrollable ? SingleChildScrollView(child: child) : child,
            ),
          )
        ],
      );
}
