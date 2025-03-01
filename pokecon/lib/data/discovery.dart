import 'package:pokecon/data/objects.dart';

abstract class Discovery<T> {
  final DateTime date;
  final T item;

  const Discovery(this.date, this.item);
}

class StopDiscovery extends Discovery<Stop> {
  const StopDiscovery(super.date, super.item);

  StopDiscovery.fromJSON(dynamic json) : super(DateTime.parse(json['date']), Stop.fromJSON(json['item']));
}

class EVStopDiscovery extends Discovery<Stop> {
  EVStopDiscovery(Stop item) : super(DateTime(0), item);
}

class VehicleDiscovery extends Discovery<Vehicle> {
  const VehicleDiscovery(super.date, super.item);

  VehicleDiscovery.fromJSON(dynamic json) : super(DateTime.parse(json['date']), Vehicle.fromJSON(json['item']));
}

class LineDiscovery extends Discovery<Line> {
  const LineDiscovery(super.date, super.item);

  LineDiscovery.fromJSON(dynamic json) : super(DateTime.parse(json['date']), Line.fromJSON(json['item']));
}
