import datetime
import os
import re
from abc import ABC, abstractmethod
from typing import Union


class RScriptWriter(ABC):
    def __init__(
        self,
        path,
        author: str = '',
        description: str = '',
        libs: list = [],
        opts: dict = {},
        code_body: str = '',
        date: Union[str, datetime.date, None] = None,
        usage: Union[str, None] = None,
        suppress_warnings: bool = True,
        versioned: bool = True
    ):
        self.path = path
        self.author = author
        self.description = description
        self.libs = libs
        self.opts = opts
        self._use_opts = len(self.opts) > 0
        if self._use_opts:
            self.libs = \
                ['optparse'] + self.libs if 'optparse' not in self.libs else self.libs
        self._ext_libs = len(self.libs) > 0
        self.code_body = code_body
        self.date = date if date is not None else datetime.date.today()
        self.usage = usage if usage is not None else "within `pyrty`"
        self.suppress_warnings = suppress_warnings
        self.versioned = versioned
        if self.versioned:
            self.version = 0

    @property
    def versioned_path(self) -> str:
        if not self.versioned:
            return self.path

        # TODO: Use pathlib.Path
        script_path, __ = os.path.splitext(self.path)
        versioned_path = f"{script_path}_v{self.version}.R"
        return versioned_path

    @property
    def _script(self) -> str:
        script = [self.header, self.libraries, self.optparsing, self.body, self.footer]
        return "\n".join(script)

    # -- Script elements as properties

    @property
    def header(self) -> str:
        return self.make_header()

    @property
    def libraries(self) -> str:
        return self.make_libraries()

    @property
    def optparsing(self) -> str:
        return self.make_optparsing()

    @property
    def body(self) -> str:
        return self.make_body()

    @property
    def footer(self) -> str:
        return self.make_footer()


    # -- Default values for script elements

    @property
    def default_header(self) -> str:
        return self._make_header(self.path, self.author, self.date, self.description, self.usage, self.suppress_warnings)
    
    @staticmethod
    def _make_header(path, author, date, description, usage, suppress_warnings) -> str:
        suppress_warnings_str = '# Suppress all output to keep stdout clean\noptions(warn=-1)' if suppress_warnings else ''
        return (
            '#!/usr/bin/env Rscript\n'
            f'# Path: {path}\n'
            f'# Author: {author}\n'
            f'# Date: {date}\n'
            f'# Description: {description}\n'
            f'# Usage: {usage}\n'
            '\n'
            f'{suppress_warnings_str}'
        )

    @property
    def default_libraries(self) -> str:
        if self._ext_libs:
            return self._make_libraries(self.libs)
        else:
            return ''

    @staticmethod
    def _make_libraries(libs: list) -> str:
        return '\n'.join(f"suppressPackageStartupMessages(library({lib}))" for lib in libs)

    @property
    def default_optparsing(self) -> str:
        if self._use_opts:
            return self._make_optparsing(self.opts)
        else:
            return ''

    @staticmethod
    def _make_optparsing(opts_config: dict) -> str:
        _option_str = (
            "make_option('--{name}', type = {type}, "
            "default = {default}, metavar = {metavar})"
        )

        _defaults = {
            'type': 'NULL',
            'default': 'NULL',
            'metavar': 'NULL'
        }

        opt_list = []
        for k, v in opts_config.items():
            try:
                v['name']
            except KeyError:
                v['name'] = k

            for key, default_value in _defaults.items():
                # TODO: Check that type, etc. are in quotes, especially for default value, which doesn't have to be a string
                # _enquoted_keys = ['type', 'default', 'metavar']
                # if key in _enquoted_keys and not is_string_in_quotes(v[key]):
                #     v[key] = f'"{v[key]}"'

                v.setdefault(key, default_value)
                if v[key] is None:
                    v[key] = default_value

            opt_list.append(_option_str.format(**v))
        opt_list = ",\n".join(opt_list)
        
        return (
            f'option_list <- list({opt_list})\n'
            'opt <- parse_args(OptionParser(option_list=option_list))'
        )        

    @property
    def default_body(self) -> str:
        return self.code_body

    @property
    def default_footer(self) -> str:
        # return (
        #     "\n# Printing values\n"
        #     # TODO: Add support for other return types
        #     "try(writeLines(readr::format_csv(res), stdout()), silent=TRUE)"
        # )
        return '\n# ~*~ End of script ~*~\n'

    # -- User defined script elements to overwrite (or use) defaults

    @abstractmethod
    def make_header(self):
        pass

    @abstractmethod
    def make_libraries(self):
        pass

    @abstractmethod
    def make_optparsing(self):
        pass

    @abstractmethod
    def make_body(self):
        pass

    @abstractmethod
    def make_footer(self):
        pass


    # -- Other basic functions

    def write_to_file(self) -> None:
        if self.versioned:
            self.version += 1

        # TODO: Use pathlib.Path write_text
        with open(self.versioned_path, 'w') as f:
            f.write(str(self))

    def delete_file(self) -> None:
        # TODO: Use pathlib.Path
        os.remove(self.versioned_path)

    def delete_all_versions(self) -> None:
        # TODO:
        pass

    def get_opts(self):
        return re.findall("'--(.*?)'", self._script)

    def __str__(self):
        return self._script
