import 'dart:ui';
import 'package:pokecon/util/extensions.dart';

class Player {
  final String nickname;
  final Color color;

  const Player(this.nickname, this.color);

  Player.fromJSON(dynamic json)
      : nickname = json['nickname']!,
        color = Color(0xFF000000 + int.parse((json['color'] as String).last(6), radix: 16));
}
