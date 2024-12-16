import re
import rjsmin
from typing import Callable, Match

map_name: str = 'm'


def clean_html(html: str) -> str:
    def fold_tag(match: Match) -> str:
        tag_open: str = match.group(1)
        content: str = match.group(2)
        tag_close: str = match.group(3)
        return f'{tag_open}{content.strip()}{tag_close}'

    def strip_whitespace_around_br(match: Match) -> str:
        return f'{match.group(1)}<br>{match.group(2)}'

    def data_on_new_lines(match: Match) -> str:
        spaces: str = match.group(1)
        tag_open: str = match.group(2)
        tag_name: str = match.group(3)
        content: str = match.group(5)
        tag_close: str = match.group(6)
        indent: str = match.group(1) + ' ' * (len(tag_name))
        return f'{spaces}{tag_open.replace('data-', f'\n{indent}data-')}\n{spaces}{content.strip()}\n{spaces}{tag_close}'

    def fold_table_cell(match: Match) -> str:
        return f'{match.group(1)}{match.group(2).strip()}' if match.group(2).count('\n') <= 2 else match.group(0)

    html: str = re.sub(r'map_[0-9a-f]{32}', map_name, html)
    html = re.sub(r'(<[a-zA-Z0-9][^/>]*>)([^<]*)(</[a-zA-Z0-9]+>)', fold_tag, html)  # fold trivial tags
    html = re.sub(r'([^<\s]*)\s*<br\s*/?>\s*(<[a-zA-Z0-9][^/>]*>)', strip_whitespace_around_br, html)  # text<br><tag[stuff]>
    html = re.sub(r'(</[a-zA-Z0-9]*>)\s*<br\s*/?>\s*([^<\s]*)', strip_whitespace_around_br, html)  # </tag><br>text
    html = re.sub(r'( *)((<[a-zA-Z0-9]+ )[a-zA-Z][^/>]*(data-[a-zA-Z][^/>]*)+>)([^<]*)(</[a-zA-Z0-9]+>)', data_on_new_lines,
                  html)
    html = re.sub(r'(<td[^>]*>)([\s\S]*?)(?=</td>)', fold_table_cell, html)
    return html


def clean_js(js: str) -> str:
    def inline_function(function: str) -> Callable[[Match], str]:
        def inline(match: Match) -> str:
            icon: str = match.group(1)
            marker: str = match.group(2)
            return f'{marker}.{function}({icon});'

        return inline

    marker_id: int = 0
    popup_id: int = 0
    line_id: int = 0
    markers: dict[str, str] = {}
    popups: dict[str, str] = {}
    lines: dict[str, str] = {}

    def mangle(match: Match) -> str:
        nonlocal marker_id, popup_id, line_id
        object_name: str = match.group(0)
        object_type: str = object_name[0:3]
        if object_type == 'mar':
            if object_name not in markers:
                markers[object_name] = f'm{(marker_id := marker_id + 1)}'
            return markers[object_name]
        elif object_type == 'pop':
            if object_name not in popups:
                popups[object_name] = f'p{(popup_id := popup_id + 1)}'
            return popups[object_name]
        elif object_type == 'pol':
            if object_name not in lines:
                lines[object_name] = f'l{(line_id := line_id + 1)}'
            return lines[object_name]
        else:
            return object_name

    def insert_newline_after_semicolons(text: str) -> str:
        result = []
        inside_string = False
        i = 0
        while i < len(text):
            char = text[i]
            if char == '"':
                if i > 0 and text[i - 1] == '\\':
                    result.append(char)
                else:
                    inside_string = not inside_string
                    result.append(char)
            elif char == ';' and not inside_string:
                result.append(';')
                result.append('\n')
            else:
                result.append(char)
            i += 1
        return ''.join(result)

    js = re.sub(r'map_[0-9a-f]{32}', map_name, js)
    js = re.sub(r'tile_layer_[0-9a-f]{32}', 'tl', js)
    js = re.sub(r'var div_icon_[0-9a-f]{32} = (.*);\n\s+(marker_[0-9a-f]{32})\.setIcon\(div_icon_[0-9a-f]{32}\);',
                inline_function('setIcon'), js)
    js = re.sub(r'var html_[0-9a-f]{32} = (.*);\n\s+(popup_[0-9a-f]{32})\.setContent\(html_[0-9a-f]{32}\);',
                inline_function('setContent'), js)
    js = re.sub(r'(popup|marker|poly_line)_[0-9a-f]{32}', mangle, js)
    js = re.sub(r'id="html_[0-9a-f]{32}" ', '', js)
    js = rjsmin.jsmin(js)
    js = insert_newline_after_semicolons(js)
    return js
