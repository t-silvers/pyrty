from pathlib import Path
from typing import Union, Optional

from pyrty.script_writers.base_script import BaseScriptWriter


class ShScriptWriter(BaseScriptWriter):
    _exe = 'bash'
    _ext = 'sh'
    
    def __init__(self, path: Union[str, Path], **kwargs):
        super().__init__(path, self._ext, **kwargs)

    def make_sources(self) -> Optional[str]:
        if self.libs:
            return '\n'.join(f"source {src}" for src in self.libs)

    def make_argparsing(self):
        pass

    def make_body(self) -> str:
        return self.code_body

    def make_footer(self) -> str:
        return self._default_footer

    # override build_script to include new methods
    def build_script(self) -> str:
        return '\n'.join(filter(None, [
            self.make_header(self._exe),
            self.make_sources(),
            self.make_body(),
            self.make_footer()
        ]))
    
    def get_args(self):
        pass