import 'package:flutter/material.dart';

class ZonesView extends StatelessWidget {
  static const Map<String, Color> colors = {
    'A': Color.fromARGB(255, 0, 150, 61),
    'B': Color.fromARGB(255, 222, 3, 14),
    'C': Color.fromARGB(255, 253, 235, 6),
    'D': Color.fromARGB(255, 2, 158, 221),
  };

  final List<String> zones;

  const ZonesView({super.key, required this.zones});

  Widget _zoneView(String zone) {
    final Color zoneColor = colors[zone] ?? Colors.black;
    return SizedBox(
      width: 16,
      child: DecoratedBox(
        decoration: BoxDecoration(color: zoneColor, borderRadius: BorderRadius.circular(4)),
        child: Center(
          child: Text(
            zone,
            style: TextStyle(
              color: zoneColor.computeLuminance() < 0.5 ? Colors.white : Colors.black,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Row(children: zones.map((zone) => _zoneView(zone)).toList());
}
