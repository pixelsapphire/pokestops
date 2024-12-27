import re
import sys


class ArgumentError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def get_all_flags() -> set[str]:
    flags: set[str] = set()
    for arg in sys.argv[1:]:
        if re.match(r'^-[A-Za-z]+', arg):
            for flag in arg[1:]:
                flags.add(flag)
    return flags


def get_all_options() -> set[str]:
    options: set[str] = set()
    for arg in sys.argv[1:]:
        if re.match(r'^--[A-Za-z\-]+', arg):
            options.add(arg[2:])
    return options


__flags__: set[str] = get_all_flags()
__options__: set[str] = get_all_options()


def __prepare_flag__(flag: str) -> str:
    if not re.match(r'^-?[A-Za-z]$', flag):
        raise ValueError('Flag must be a single letter optionally preceded by a dash')
    if flag.startswith('-'):
        return flag[1:]


def __prepare_option__(option: str) -> str:
    if not re.match(r'^(--)?[A-Za-z\-]+$', option):
        raise ValueError('Option must be a string of letters and dashes optionally preceded by two dashes')
    if option.startswith('--'):
        return option[2:]
    return option


def validate_flags(*valid_flags: str) -> None:
    for flag in __flags__:
        for valid_flag in valid_flags:
            if __prepare_flag__(valid_flag) == flag:
                return
        raise ArgumentError(f'Invalid flag: -{flag}')


def validate_options(*valid_options: str) -> None:
    for option in __options__:
        for valid_option in valid_options:
            if __prepare_option__(valid_option) == option:
                return
        raise ArgumentError(f'Invalid option: --{option}')


def flag_present(flag: str) -> bool:
    return __prepare_flag__(flag) in __flags__


def option_present(option: str) -> bool:
    return __prepare_option__(option) in __options__


def one_of_present(*args: str) -> bool:
    for arg in args:
        if re.match(r'^-?[A-Za-z]$', arg):
            if flag_present(arg):
                return True
        elif re.match(r'^(--)?[A-Za-z\-]+$', arg):
            if option_present(arg):
                return True
    return False
