import 'package:flutter/material.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/ui/widgets/macos_divider.dart';
import 'package:pokecon/util/ui_utils.dart';

class MacosTabPage extends StatelessWidget {
  final EdgeInsets padding;
  final Widget child;
  final List<MacosTabActionButton> actions;

  const MacosTabPage({
    super.key,
    this.padding = const EdgeInsets.only(top: 16),
    required this.child,
    this.actions = const [],
  });

  @override
  Widget build(BuildContext context) {
    final Brightness brightness = MacosTheme.of(context).brightness;
    return Column(
      children: [
        Expanded(child: Padding(padding: padding, child: child)),
        if (actions.isNotEmpty)
          DecoratedBox(
            decoration: BoxDecoration(
                border: Border(top: BorderSide(color: brightness.resolve(Colors.black, Colors.white).withAlpha(24))),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(4)),
                color: brightness.resolve(Colors.black, Colors.white).withAlpha(16)),
            child: Row(
              children: List.generate(
                actions.length * 2 - 1,
                (index) => index.isEven ? actions[index ~/ 2] : const MacosDivider(),
              ),
            ),
          ),
      ],
    );
  }
}

class MacosTabActionButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onPressed;

  const MacosTabActionButton({super.key, required this.icon, this.onPressed});

  @override
  Widget build(BuildContext context) => MacosIconButton(
        backgroundColor: Colors.transparent,
        disabledColor: Colors.transparent,
        icon: Icon(icon, color: onPressed != null ? getPrimaryColor(context) : getSecondaryColor(context)),
        boxConstraints: BoxConstraints.tightFor(width: 24, height: 24),
        padding: EdgeInsets.all(6),
        onPressed: onPressed,
      );
}
