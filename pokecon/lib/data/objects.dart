import 'package:pokecon/util/extensions.dart';

class Stop {
  final String shortName, fullName;

  const Stop(this.shortName, this.fullName);

  Stop.fromJSON(dynamic json)
      : shortName = json['short_name'],
        fullName = json['full_name'];

  const Stop.unknown([String? shortName])
      : shortName = shortName ?? '(unknown)',
        fullName = '(unknown)';
}

enum VehicleType {
  tram,
  bus,
  minibus,
  unknown;
}

class Vehicle {
  final String vehicleId, brand, model;
  final VehicleType type;

  const Vehicle(this.vehicleId, this.type, this.brand, this.model);

  Vehicle.fromJSON(dynamic json)
      : vehicleId = json['vehicle_id'],
        type = VehicleType.values.tryByName(json['type'], VehicleType.unknown),
        brand = json['brand'] ?? '',
        model = json['model'] ?? '(unknown)';

  const Vehicle.unknown([String? vehicleId])
      : vehicleId = vehicleId ?? '(unknown)',
        type = VehicleType.unknown,
        brand = '',
        model = '(unknown)';

  String get fullName => '$brand $model'.trimLeft();
}

class Line {
  final String number, terminals, description;

  const Line(this.number, this.terminals, this.description);

  Line.fromJSON(dynamic json)
      : number = json['number'] ?? '(unknown)',
        terminals = json['terminals'] ?? '(unknown)',
        description = json['description'] ?? '(unknown)';

  const Line.unknown([String? number])
      : number = number ?? '(unknown)',
        terminals = '(unknown)',
        description = '(unknown)';
}
