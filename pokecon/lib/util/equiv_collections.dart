import 'dart:collection';

extension ListExt<E> on List<E> {
  bool equivalent(List<E> other) {
    if (identical(this, other)) return true;
    if (runtimeType != other.runtimeType || length != other.length) return false;
    for (int i = 0; i < length; i++) {
      final E thisElement = this[i];
      final E otherElement = other[i];
      if (thisElement is List && otherElement is List) {
        if (thisElement.equivalent(otherElement as List)) {
          continue;
        } else {
          return false;
        }
      } else if (thisElement is Map && otherElement is Map) {
        if (thisElement.equivalent(otherElement as Map)) {
          continue;
        } else {
          return false;
        }
      } else if (thisElement != otherElement) {
        return false;
      }
    }
    return true;
  }
}

class EquivList<E> extends ListBase<E> {
  final List<E> _this;

  EquivList() : _this = [];

  EquivList.from(Iterable<E> other) : _this = List<E>.from(other);

  @override
  set length(int newLength) => _this.length = newLength;

  @override
  int get length => _this.length;

  @override
  E operator [](int index) => _this[index];

  @override
  void operator []=(int index, E value) => _this[index] = value;

  @override
  bool operator ==(Object other) {
    if (other is! List<E>) return false;
    return equivalent(other);
  }

  @override
  int get hashCode {
    int result = 1;
    for (final E element in this) {
      result = 31 * result + element.hashCode;
    }
    return result;
  }
}

extension MapExt<K, V> on Map<K, V> {
  bool equivalent(Map<K, V> other) {
    if (identical(this, other)) return true;
    if (runtimeType != other.runtimeType || length != other.length) return false;
    for (final K key in keys) {
      if (!other.containsKey(key)) return false;
      final V thisValue = this[key] as V;
      final V otherValue = other[key] as V;
      if (thisValue is Map && otherValue is Map) {
        if (thisValue.equivalent(otherValue as Map)) {
          continue;
        } else {
          return false;
        }
      } else if (thisValue is List && otherValue is List) {
        if (thisValue.equivalent(otherValue as List)) {
          continue;
        } else {
          return false;
        }
      } else if (thisValue != otherValue) {
        return false;
      }
    }
    return true;
  }
}

class EquivMap<K, V> extends MapBase<K, V> {
  final Map<K, V> _this;

  EquivMap() : _this = {};

  EquivMap.from(Map<K, V> other) : _this = Map<K, V>.from(other);

  @override
  V? operator [](Object? key) => _this[key];

  @override
  void operator []=(K key, V value) => _this[key] = value;

  @override
  void clear() => _this.clear();

  @override
  Iterable<K> get keys => _this.keys;

  @override
  V? remove(Object? key) => _this.remove(key);

  @override
  bool operator ==(Object other) {
    if (other is! Map<K, V>) return false;
    return equivalent(other);
  }

  @override
  int get hashCode {
    int result = 1;
    for (final K key in keys) {
      result = 31 * result + key.hashCode;
      result = 31 * result + _this[key]!.hashCode;
    }
    return result;
  }
}
