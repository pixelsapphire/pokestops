import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart';
import 'package:pokecon/data/discovery.dart';
import 'package:pokecon/data/player.dart';
import 'package:pokecon/data/server_status.dart';
import 'package:pokecon/data/objects.dart';
import 'package:pokecon/util/equiv_collections.dart';
import 'package:pokecon/util/scope_functions.dart';

class DynamicValue<T> {
  final String path;
  final FutureOr<T> Function(Response) parser;
  final T? fallbackValue;
  final Duration? refreshInterval;
  final StreamController<T> _controller = StreamController.broadcast();
  Completer<void>? _refreshCompleter;
  T? _cachedValue;
  bool _hasFetchedOnce = false;
  final List<DynamicValue> _subscribers = [];

  DynamicValue({
    required this.path,
    required this.parser,
    this.fallbackValue,
    this.refreshInterval,
    List<DynamicValue>? subscribeTo,
  }) {
    refreshInterval?.let((Duration it) => Timer.periodic(it, (_) async => await refresh()));
    for (final DynamicValue subscribed in subscribeTo ?? []) {
      if (subscribed == this) throw ArgumentError('Circular dependency');
      if (!subscribed._subscribers.contains(this)) subscribed._subscribers.add(this);
    }
  }

  Stream<T> get stream async* {
    if (!_hasFetchedOnce || _cachedValue == null) await refresh();
    if (_cachedValue != null) yield _cachedValue!;
    yield* _controller.stream;
  }

  Future<T> get future async {
    if (!_hasFetchedOnce || _cachedValue == null) await refresh();
    return _cachedValue!;
  }

  Future<void> refresh() async {
    if (_refreshCompleter != null) {
      await _refreshCompleter!.future;
      return;
    }
    _refreshCompleter = Completer();
    try {
      _cachedValue = await BackendService._fetch(path, parser, fallbackValue);
      _hasFetchedOnce = true;
      _controller.add(_cachedValue as T);
      for (final DynamicValue subscriber in _subscribers) {
        subscriber.refresh();
      }
      _refreshCompleter!.complete();
    } catch (e) {
      _refreshCompleter!.completeError(e);
      _controller.addError(e);
    } finally {
      _refreshCompleter = null;
    }
  }

  void dispose() => _controller.close();
}

class CommandResult {
  late final bool success;
  late final String? failureCause;
  late final List<String> errors;

  CommandResult.success([this.errors = const []])
      : success = true,
        failureCause = null;

  CommandResult.failure(this.failureCause, [this.errors = const []]) : success = false;

  CommandResult.fromResponse(Response response) {
    final Map<String, dynamic> responseJSON = jsonDecode(response.body);
    success = response.statusCode == 200 && responseJSON['success'];
    failureCause = responseJSON['error_message'];
    errors = List<String>.from(responseJSON['errors']);
  }
}

class BackendService {
  static const String _serverUrl = 'http://localhost:39610';
  static final Map<String, Map<EquivMap<String, String>, dynamic>> _parametrizedDynamicValues = {};

  static void _printResponseInfo(String method, String url, Response response) {
    if (kDebugMode && response.body != 'online') {
      print('$method $url');
      print('response status code: ${response.statusCode}');
      print('response headers: ${response.headers}');
      print('response body: ${response.body}');
    }
  }

  static Future<T> _fetch<T>(String url, FutureOr<T> Function(Response) parser, T? onError) async =>
      get(Uri.parse('$_serverUrl/$url')).then(
        (response) async {
          _printResponseInfo('GET', url, response);
          try {
            return await parser(response);
          } catch (e, stackTrace) {
            if (kDebugMode) {
              print('Error parsing response from $url: $e');
              print(stackTrace);
            }
            return Future.value(onError);
          }
        },
        onError: (e) {
          if (kDebugMode) print('Error fetching from $url: $e');
          return onError;
        },
      );

  static Future<CommandResult> _command(String url) async => post(Uri.parse('$_serverUrl/$url')).then(
        (response) {
          _printResponseInfo('POST', url, response);
          return CommandResult.fromResponse(response);
        },
        onError: (e) {
          if (kDebugMode) print('Error fetching from $url: $e');
          return CommandResult.failure(e.toString());
        },
      );

  static DynamicValue<T> _parametrizedDynamicValue<T>({
    required String path,
    required Map<String, String> parameters,
    List<DynamicValue>? subscribeTo,
    required FutureOr<T> Function(Response) parser,
    T? fallbackValue,
    Duration? refreshInterval,
  }) {
    final key = EquivMap<String, String>.from(parameters);
    if (!_parametrizedDynamicValues.containsKey(path)) _parametrizedDynamicValues[path] = {};
    if (!_parametrizedDynamicValues[path]!.containsKey(key)) {
      _parametrizedDynamicValues[path]![key] = DynamicValue<T>(
        path: '$path?${key.entries.map((e) => '${e.key}=${e.value}').join('&')}',
        subscribeTo: subscribeTo,
        parser: parser,
        fallbackValue: fallbackValue,
        refreshInterval: refreshInterval,
      );
    }
    return _parametrizedDynamicValues[path]![key] as DynamicValue<T>;
  }

  static final DynamicValue<ServerStatus> serverStatus = DynamicValue(
    path: '/info/status',
    parser: (response) => (response.body == 'online') ? ServerStatus.online : ServerStatus.offline,
    fallbackValue: ServerStatus.offline,
    refreshInterval: const Duration(seconds: 1),
  );

  static final DynamicValue<List<Player>> players = DynamicValue(
    path: '/info/players',
    parser: (r) => jsonDecode(r.body).map<Player>(Player.fromJSON).toList(),
  );

  static final DynamicValue<DateTime> gtfsLastUpdate = DynamicValue(
    path: '/info/last_update/gtfs',
    parser: (response) => DateTime.parse(response.body),
  );
  static final DynamicValue<DateTime> announcementsLastUpdate = DynamicValue(
    path: '/info/last_update/announcements',
    parser: (response) => DateTime.parse(response.body),
  );

  static Future<CommandResult> updateGtfs() async => _command('/update/gtfs').then((result) {
        if (result.success) gtfsLastUpdate.refresh();
        return result;
      });

  static Future<CommandResult> updateAnnouncements() async => _command('/update/announcements').then((result) {
        if (result.success) announcementsLastUpdate.refresh();
        return result;
      });

  static Future<CommandResult> updateAll() async => _command('/update/all').then((result) {
        if (result.success) {
          gtfsLastUpdate.refresh();
          announcementsLastUpdate.refresh();
        }
        return result;
      });

  static Future<CommandResult> reloadDatabase() async => _command('/reload');

  static DynamicValue<Map<String, Stop>> domainStops = DynamicValue(
    path: '/domain/stops',
    parser: (response) {
      final Map<String, dynamic> stops = jsonDecode(response.body);
      return stops.map((key, value) => MapEntry(key, Stop.fromJSON(value)));
    },
  );
  static DynamicValue<Map<String, Carrier>> domainCarriers = DynamicValue(
    path: '/domain/carriers',
    parser: (response) {
      final Map<String, dynamic> carriers = jsonDecode(response.body);
      return carriers.map((key, value) => MapEntry(key, Carrier.fromJSON(value)));
    },
  );
  static DynamicValue<Map<String, Vehicle>> domainVehicles = DynamicValue(
    path: '/domain/vehicles',
    parser: (response) async {
      final Map<String, dynamic> vehicles = jsonDecode(response.body);
      return vehicles.map((key, value) => MapEntry(key, Vehicle.fromJSON(value)));
    },
  );
  static DynamicValue<Map<String, Line>> domainLines = DynamicValue(
    path: '/domain/lines',
    parser: (response) {
      final Map<String, dynamic> lines = jsonDecode(response.body);
      return lines.map((key, value) => MapEntry(key, Line.fromJSON(value)));
    },
  );

  static DynamicValue<List<StopDiscovery>> playerStops(String nickname) => _parametrizedDynamicValue(
        path: '/playerdata/stops',
        parameters: {'player': nickname},
        parser: (response) => Future.wait(jsonDecode(response.body)
            .map<Future<StopDiscovery>>((d) async => StopDiscovery(
                DateTime.parse(d['date']), await domainStops.future.then((s) => s[d['item']] ?? Stop.unknown(d['item']))))
            .toList()),
      );

  static DynamicValue<List<EVStopDiscovery>> playerEVStops(String nickname) => _parametrizedDynamicValue(
        path: '/playerdata/ev_stops',
        parameters: {'player': nickname},
        parser: (response) => Future.wait(jsonDecode(response.body)
            .map<Future<EVStopDiscovery>>(
                (d) async => EVStopDiscovery(await domainStops.future.then((s) => s[d['item']] ?? Stop.unknown(d['item']))))
            .toList()),
      );

  static DynamicValue<List<VehicleDiscovery>> playerVehicles(String nickname) => _parametrizedDynamicValue(
        path: '/playerdata/vehicles',
        parameters: {'player': nickname},
        parser: (response) => Future.wait(jsonDecode(response.body)
            .map<Future<VehicleDiscovery>>((d) async => VehicleDiscovery(
                DateTime.parse(d['date']), await domainVehicles.future.then((v) => v[d['item']] ?? Vehicle.unknown(d['item']))))
            .toList()),
      );

  static DynamicValue<List<LineDiscovery>> playerLines(String nickname) => _parametrizedDynamicValue(
        path: '/playerdata/lines',
        parameters: {'player': nickname},
        parser: (response) => Future.wait(jsonDecode(response.body)
            .map<Future<LineDiscovery>>((d) async => LineDiscovery(
                DateTime.parse(d['date']), await domainLines.future.then((l) => l[d['item']] ?? Line.unknown(d['item']))))
            .toList()),
      );

  static Future<CommandResult> compileMap() async => _command('/compile/map');

  static Future<CommandResult> compileArchive() async => _command('/compile/archive');

  static Future<CommandResult> compileAnnouncements() async => _command('/compile/announcements');

  static Future<CommandResult> compileRaids() async => _command('/compile/raids');

  static Future<CommandResult> compileAll() async => _command('/compile/all');
}
