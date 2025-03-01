extension StringExt on String {
  String last(int n) => substring(length - n);
}

extension IterableExt<T> on Iterable<T> {
  Iterable<R> mapIndexed<R>(R Function(int index, T value) f) sync* {
    var index = 0;
    for (final value in this) {
      yield f(index++, value);
    }
  }
}

extension EnumExt<T extends Enum> on Iterable<T> {
  T tryByName(String? name, T orElse) {
    return firstWhere((value) => value.name == name, orElse: () => orElse);
  }
}
