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


def errors_present() -> bool:
    return len(__error_log__) > 0


def flush_errors() -> list[str]:
    errors: list[str] = list(__error_log__)
    __error_log__.clear()
    return errors


def print_errors() -> None:
    [print(message, file=sys.stderr) for message in flush_errors()]
