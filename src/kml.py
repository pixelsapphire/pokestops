import jinja2
import ref
import util
from data import Raid
from database import Database
from log import *


def make_raid_kml(raid: Raid, output_path: str) -> None:
    log(f'Exporting raid {raid.raid_id} to {output_path}... ', end='')
    with open(util.prepare_file(output_path), 'w') as f:
        f.write(jinja2.Template(util.file_to_string(ref.codegen_template_kml_raid)).render(raid=raid))
    log('Done!')


def make_gtfs_kml(db: Database, output_path: str) -> None:
    log(f'Exporting GTFS data to {output_path}... ', end='')
    with open(util.prepare_file(output_path), 'w') as f:
        f.write(jinja2.Template(util.file_to_string(ref.codegen_template_kml_gtfs)).render(db=db))
    log('Done!')
