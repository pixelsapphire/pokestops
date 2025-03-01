import 'package:flutter/material.dart';
import 'package:macos_ui/macos_ui.dart';

class MacosDivider extends StatelessWidget {
  final double opacity;

  const MacosDivider({super.key, this.opacity = 0.125})
      : assert(opacity >= 0 && opacity <= 1, 'opacity must be between 0 and 1');

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(color: MacosTheme.of(context).dividerColor.withAlpha((255 * opacity).round())),
        child: const SizedBox(height: 16, width: 1),
      );
}
