import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:pokecon/ui/pages/basic_page.dart';
import 'package:pokecon/util/ui_utils.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final typography = getSecondaryTypography(context);
    return BasicPage(
      scrollable: false,
      title: 'Pokestops Admin Console',
      child: Center(
        child: Opacity(
          opacity: 0.5,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Welcome to the Pokestops Admin Console!', style: typography.largeTitle),
              Text('Select an option from the sidebar to get started.', style: typography.title1),
            ],
          ),
        ),
      ),
    );
  }
}
