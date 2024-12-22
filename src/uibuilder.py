import os.path
import util
from data import *
from markupsafe import Markup
from jinja2 import Environment, FileSystemLoader, Template


class JinjaLoader(FileSystemLoader):
    def __init__(self):
        super().__init__('templates')

    def get_source(self, environment: Environment, template_id: str) -> tuple[str, str, Callable]:
        template_path: str = template_id.replace('.', '/')
        template_path += '/_root.jinja' if os.path.isdir(f'templates/{template_path}') else '.jinja'
        return super().get_source(environment, template_path)


class UIBuilder(Environment):
    def __init__(self, database: Database, lexmap_file: str):
        super().__init__(loader=JinjaLoader())
        self.__lexmap__: dict[str, float] = util.create_lexicographic_mapping(util.file_to_string(lexmap_file))
        self.__database__: Database = database
        self.filters['lexicographic_sort'] = self.__lexicographic_sort__
        self.globals.update(ref=ref)
        self.globals.update(util=util)
        self.globals.update(include_file=self.__include_file__)

    def __lexicographic_sort__[T](self, sequence: list[T], attribute: str | int | None = None) -> list[T]:
        return sorted(sequence, key=lambda item: util.lexicographic_sequence(self.getitem(item, attribute), self.__lexmap__))

    def __include_file__(self, file: str) -> Markup:
        return Markup(self.loader.get_source(self, file)[0])

    def create_map(self, initial_html: str) -> Template:
        folium_head: str = re.search(r'<head>(.*)</head>', initial_html, re.DOTALL).group(1).strip()
        folium_body: str = re.search(r'<body>(.*)</body>', initial_html, re.DOTALL).group(1).strip()
        map_template: Template = self.get_template('map')
        map_template.globals.update(db=self.__database__, folium_head=folium_head, folium_body=folium_body)
        return map_template

    def create_archive(self) -> Template:
        archive_template: Template = self.get_template('archive')
        archive_template.globals.update(db=self.__database__, util=util)
        return archive_template

    def create_announcements(self) -> Template:
        announcements_template: Template = self.get_template('announcements')
        announcements_template.globals.update(db=self.__database__)
        return announcements_template
