import re
from pathlib import Path
from typing import Union, List

from pyrty.script_writers.base_script import OutputType, BaseScriptWriter


class RScriptWriter(BaseScriptWriter):
    _exe = 'Rscript'
    _ext = 'R'
    _suppress_warnings = '# Suppress all output to keep stdout clean\noptions(warn=-1)'

    def __init__(self, path: Union[str, Path], **kwargs):
        super().__init__(path, self._ext, **kwargs)

    def make_header(self, exe) -> str:
        return super().make_header(exe) + self._suppress_warnings if self.suppress_warnings else ''

    def build_script(self) -> str:
        return '\n'.join(filter(None, [
            self.make_header(self._exe),
            self.make_imports(),
            self.make_argparsing(),
            self.make_body(),
            self.make_footer()
        ]))

    def make_argparsing(self) -> str:
        if self.args:
            _option_str = ("make_option('--{name}', type = {type}, "
                           "default = {default}, metavar = {metavar})")
            _defaults = {'type': 'NULL', 'default': 'NULL', 'metavar': 'NULL'}

            opt_list = []
            for k, v in self.args.items():
                v['name'] = v.get('name', k)
                for key, default_value in _defaults.items():
                    v[key] = v.get(key, default_value)
                opt_list.append(_option_str.format(**v))
            opt_list = ",\n".join(opt_list)

            return (f'option_list <- list({opt_list})\n'
                    'opt <- parse_args(OptionParser(option_list=option_list))')

    def make_imports(self) -> str:
        return '\n'.join(f"suppressPackageStartupMessages(library({lib}))" for lib in self.libs)

    def make_body(self) -> str:
        return self.code_body

    def make_footer(self) -> str:
        footer = []
        if self.ret:
            footer.append("# Printing values")
            if self.output_type == OutputType.DF:
                footer.append(f"try(writeLines(readr::format_csv({self.ret_name}), stdout()), silent=TRUE)")
            else:
                raise NotImplementedError
        footer.append(self._default_footer)
        return '\n'.join(footer)

    def get_args(self) -> List[str]:
        return re.findall("'--(.*?)'", str(self))