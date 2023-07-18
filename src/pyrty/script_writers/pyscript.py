import re
from pathlib import Path
from typing import Union, List, Dict, Optional

from pyrty.script_writers.base_script import OutputType, BaseScriptWriter


class PyScriptWriter(BaseScriptWriter):
    _exe = 'python'
    _ext = 'py'
    
    def __init__(self, path: Union[str, Path], **kwargs):
        super().__init__(path, self._ext, **kwargs)

    def build_script(self) -> str:
        return '\n'.join(filter(None, [
            self.make_header(self._exe),
            self.make_imports(),
            self.make_argparsing(),
            self.make_body(),
            self.make_footer()
        ]))

    def make_imports(self) -> Optional[str]:
        if self.libs:
            return '\n'.join(f"import {lib}" for lib in self.libs)
    
    def make_argparsing(self) -> Optional[str]:
        if self.args:
            arg_str = []
            _arg_str = ("parser.add_argument('--{name}', type={type}, "
                        "default={default}, help={metavar})")
            _defaults = {'type': 'None', 'default': 'None', 'metavar': "''"}

            for k, v in self.args.items():
                v['name'] = v.get('name', k)
                for key, default_value in _defaults.items():
                    v[key] = v.get(key, default_value)
                arg_str.append(_arg_str.format(**v))
            arg_parsing_script = '\n'.join(arg_str)
            
            return ('import argparse\n'
                    'parser = argparse.ArgumentParser()\n'
                    f'{arg_parsing_script}\n'
                    'args = parser.parse_args()')

    def make_body(self) -> str:
        return self.code_body

    def make_footer(self) -> str:
        return self._default_footer

    def get_args(self) -> List[str]:
        return re.findall("'--(.*?)'", str(self))