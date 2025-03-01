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

void showResultDialog({required BuildContext context, required String title, String? error, List<String>? warnings}) =>
    showMacosSheet(
      context: context,
      barrierDismissible: true,
      builder: (context) => MacosSheet(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(title, style: getPrimaryTypography(context).title2.copyWith(fontWeight: FontWeight.bold)),
              if (error != null)
                Padding(padding: const EdgeInsets.all(16), child: Text(error!, style: TextStyle(fontWeight: FontWeight.bold))),
              (warnings?.isNotEmpty ?? false)
                  ? Expanded(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              for (final warning in warnings!)
                                Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Text(warning)),
                            ],
                          ),
                        ),
                      ),
                    )
                  : const SizedBox(height: 16),
              PushButton(
                controlSize: ControlSize.large,
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Done'),
              ),
            ],
          ),
        ),
      ),
    );
