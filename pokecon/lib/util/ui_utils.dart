import 'package:flutter/cupertino.dart';
import 'package:macos_ui/macos_ui.dart';

MacosTypography _getTypography(BuildContext context, CupertinoDynamicColor base) =>
    MacosTypography(color: MacosTheme.brightnessOf(context).resolve(base, base.darkColor));

MacosTypography getPrimaryTypography(BuildContext context) => _getTypography(context, MacosColors.labelColor);

MacosTypography getSecondaryTypography(BuildContext context) => _getTypography(context, MacosColors.secondaryLabelColor);

MacosTypography getTertiaryTypography(BuildContext context) => _getTypography(context, MacosColors.tertiaryLabelColor);

Color getPrimaryColor(BuildContext context) => CupertinoDynamicColor.resolve(MacosColors.labelColor, context);

Color getSecondaryColor(BuildContext context) => CupertinoDynamicColor.resolve(MacosColors.secondaryLabelColor, context);

Color getTertiaryColor(BuildContext context) => CupertinoDynamicColor.resolve(MacosColors.tertiaryLabelColor, context);
