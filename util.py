import os
import zipfile

__roman_num__: dict[int, str] = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'}


def roman_numeral(n: int) -> str:
    return __roman_num__[n] if 1 <= n <= 10 else f'{n}'


class zip_file(zipfile.ZipFile):
    def extract_as(self, member: str | zipfile.ZipInfo, output: str | os.PathLike[str],
                   path: str | os.PathLike[str] | None = None, pwd: bytes | None = None):
        self.extract(member, path, pwd)
        member_name = member.filename if isinstance(member, zipfile.ZipInfo) else member
        os.rename(member_name, output)
