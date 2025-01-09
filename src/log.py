import sys
from typing import Any

__error_log__: list[str] = []
__logging_enabled__: bool = True


def enable_logging(enabled: bool) -> None:
    global __logging_enabled__
    __logging_enabled__ = enabled


def log(*args: Any, **kwargs: Any) -> None:
    if __logging_enabled__:
        print(*args, **kwargs)


def error(*args: Any) -> None:
    __error_log__.append(' '.join(map(str, args)))


def print_errors() -> None:
    for message in __error_log__:
        print(message, file=sys.stderr)
