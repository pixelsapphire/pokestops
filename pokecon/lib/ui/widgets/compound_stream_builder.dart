import 'package:flutter/widgets.dart';

class BiStreamBuilder<T, U> extends StatelessWidget {
  final Stream<T> stream1;
  final Stream<U> stream2;
  final Widget Function(BuildContext context, AsyncSnapshot<T> snapshot1, AsyncSnapshot<U> snapshot2) builder;

  const BiStreamBuilder({super.key, required this.stream1, required this.stream2, required this.builder});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<T>(
      stream: stream1,
      builder: (context, snapshot1) => StreamBuilder(
        stream: stream2,
        builder: (context, snapshot2) => builder(context, snapshot1, snapshot2),
      ),
    );
  }
}
