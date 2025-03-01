extension ScopeFunctions on Object {
  T apply<T>(T Function() block) {
    block();
    return this as T;
  }

  R let<T, R>(R Function(T) block) => block(this as T);

  T? takeIf<T>(bool Function(T) block) => block(this as T) ? this as T : null;

  T? takeUnless<T>(bool Function(T) block) => !block(this as T) ? this as T : null;
}
