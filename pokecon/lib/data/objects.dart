import 'dart:ui';
import 'package:pokecon/util/extensions.dart';

class Stop {
  final String shortName, fullName, zone;

  const Stop(this.shortName, this.fullName, this.zone);

  Stop.fromJSON(dynamic json)
      : shortName = json['short_name'],
        fullName = json['full_name'],
        zone = json['zone'];

  const Stop.unknown([String? shortName])
      : shortName = shortName ?? '(unknown)',
        fullName = '(unknown)',
        zone = '?';
}

class Carrier {
  final String symbol, name;
  final ({Color top, Color middle, Color bottom}) colors;

  const Carrier(this.symbol, this.name, this.colors);

  Carrier.fromJSON(dynamic json)
      : symbol = json['symbol'],
        name = json['name'],
        colors = (
          top: Color(int.parse(json['colors'][0], radix: 16)),
          middle: Color(int.parse(json['colors'][1], radix: 16)),
          bottom: Color(int.parse(json['colors'][2], radix: 16)),
        );

  Carrier.unknown([String? symbol])
      : symbol = symbol ?? '(unknown)',
        name = '(unknown)',
        colors = (top: Color(0xFF000000), middle: Color(0xFF000000), bottom: Color(0xFF000000));
}

enum VehicleType {
  tram,
  bus,
  minibus,
  unknown;
}

class Vehicle {
  final String vehicleId, brand, model, carrierSymbol;
  final VehicleType type;

  const Vehicle(this.vehicleId, this.type, this.brand, this.model, this.carrierSymbol);

  Vehicle.fromJSON(dynamic json)
      : vehicleId = json['vehicle_id'],
        type = VehicleType.values.tryByName(json['type'], VehicleType.unknown),
        brand = json['brand'] ?? '',
        model = json['model'] ?? '(unknown)',
        carrierSymbol = json['carrier'] ?? '?';

  Vehicle.unknown([String? vehicleId])
      : vehicleId = vehicleId ?? '(unknown)',
        type = VehicleType.unknown,
        brand = '',
        model = '(unknown)',
        carrierSymbol = '?';

  String get fullName => '$brand $model'.trimLeft();
}

class Line {
  final String number, terminals, description;
  final List<String> zones;

  const Line(this.number, this.terminals, this.description, this.zones);

  Line.fromJSON(dynamic json)
      : number = json['number'] ?? '(unknown)',
        terminals = json['terminals'] ?? '(unknown)',
        description = json['description'] ?? '(unknown)',
        zones = List<String>.from(json['zones'] ?? []);

  const Line.unknown([String? number])
      : number = number ?? '(unknown)',
        terminals = '(unknown)',
        description = '(unknown)',
        zones = const [];
}
