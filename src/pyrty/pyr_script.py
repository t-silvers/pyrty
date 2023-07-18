import pprint
import shutil

from pyrty.script_writers import _script_writers, BaseScriptWriter


class PyRScript:
    def __init__(self, lang: str, script_kwargs: dict):
        self.lang = lang
        self.script_writer = fetch_script_writer(lang)(**script_kwargs)

    def create_script(self) -> None:
        self.script_writer.write_to_file()

    def delete_script(self) -> None:
        self.script_writer.delete_file()

    def print(self) -> None:
        pprint.pprint(str(self))

    @property
    def script_args(self) -> list:
        return self.script_writer.get_args()

    @property
    def script_exe(self) -> str:
        return shutil.which(self.script_writer._exe)

    @property
    def script_exists(self) -> bool:
        """Whether the environment exists."""
        return self.script_writer.exists

    @property
    def script_path(self) -> str:
        return self.script_writer.versioned_path

    @property
    def script_ret(self) -> bool:
        return self.script_writer.ret

    def __str__(self) -> str:
        return str(self.script_writer)

def fetch_script_writer(lang: str) -> BaseScriptWriter:
    try:
        return _script_writers[lang]
    except KeyError:
        raise ValueError(f'Script writer for {lang} is not supported.')
