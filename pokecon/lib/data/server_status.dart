import 'dart:ui';

enum ServerStatus {
  online(Color(0xff00aa00)),
  offline(Color(0xffcc0000)),
  connecting(Color(0xffdddd00));

  final Color color;

  const ServerStatus(this.color);
}
