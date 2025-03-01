import 'package:flutter/cupertino.dart';
import 'package:hue_rotation/hue_rotation.dart';
import 'package:macos_ui/macos_ui.dart';
import 'package:pokecon/util/ui_utils.dart';

class ActionCard extends StatelessWidget {
  final double height;
  final String imageAssetPath;
  final Alignment backgroundAlignment;
  final double hueRotation;
  final bool colorsInverted;
  final String? title, subtitle;
  final Widget? titleWidget, subtitleWidget;
  final String buttonText;
  final VoidCallback? action;

  const ActionCard({
    super.key,
    required this.height,
    required this.imageAssetPath,
    this.backgroundAlignment = Alignment.center,
    this.hueRotation = 0,
    this.colorsInverted = false,
    this.title,
    this.subtitle,
    this.titleWidget,
    this.subtitleWidget,
    required this.buttonText,
    this.action,
  })  : assert((title == null) != (titleWidget == null), 'Either title or titleWidget must be provided (and not both)'),
        assert(subtitle == null || subtitleWidget == null, 'Subtitle and subtitleWidget cannot be provided at the same time');

  @override
  Widget build(BuildContext context) {
    final brightness = MacosTheme.of(context).brightness;
    return SizedBox(
      height: height,
      child: HueRotation(
        degrees: hueRotation,
        child: DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(color: brightness.resolve(Color(0x18000000), Color(0x18ffffff)), width: 1),
            borderRadius: BorderRadius.circular(16),
            image: DecorationImage(
              image: AssetImage(imageAssetPath),
              fit: BoxFit.cover,
              alignment: backgroundAlignment,
              invertColors: colorsInverted,
            ),
          ),
          child: Column(
            children: [
              const Expanded(child: SizedBox()),
              DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.vertical(bottom: Radius.circular(16)),
                  color: brightness.resolve(Color(0xccffffff), Color(0xcc444444)),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (title != null) _buildTitleText(context, title, MacosTypography.of(context).title2),
                            if (subtitle != null) _buildTitleText(context, subtitle, getSecondaryTypography(context).caption1),
                            if (titleWidget != null)
                              DefaultTextStyle(style: MacosTypography.of(context).title2, child: titleWidget!),
                            if (subtitleWidget != null)
                              DefaultTextStyle(style: getSecondaryTypography(context).caption1, child: subtitleWidget!),
                          ],
                        ),
                      ),
                      const SizedBox(width: 6),
                      PushButton(
                        secondary: true,
                        controlSize: ControlSize.large,
                        onPressed: action ?? () {},
                        child: Text(buttonText),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Text _buildTitleText(BuildContext context, String? value, TextStyle style) =>
      Text(value ?? '', style: style, maxLines: 1, softWrap: false, overflow: TextOverflow.fade);
}
