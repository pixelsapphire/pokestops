import 'package:flutter/cupertino.dart';

class CircleIndicator extends StatelessWidget {
  final double size;
  final Color color;

  const CircleIndicator({super.key, required this.size, required this.color});

  @override
  Widget build(BuildContext context) => SizedBox(
        width: size,
        height: size,
        child: DecoratedBox(decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      );
}
