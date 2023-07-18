import datetime
import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Union, List, Dict, Optional

_logger = logging.getLogger(__name__)


class OutputType(str, Enum):
    DF = 'df'


class BaseScriptWriter(ABC):
    _default_footer = '\n# ~*~ End of script ~*~\n'
    _version = 0

    def __init__(
        self,
        path: Union[str, Path],
        ext: str,
        args: Optional[Dict] = None,
        author: Optional[str] = None,
        code_body: Optional[str] = None,
        date: Union[str, datetime.date, None] = None,
        description: Optional[str] = None,
        libs: Optional[List[str]] = None,
        output_type: Optional[str] = None,
        ret: Optional[bool] = False,
        ret_name: Optional[str] = None,
        suppress_warnings: bool = True,
        usage: Optional[str] = None,
        versioned: bool = True,
    ):
        self.path = Path(path) # TODO: Have default path be in pyrty/usr/scripts
        self.ext = ext
        self.versioned = versioned

        # -- When script exists, load it and update attributes ...
        if self.path.exists():
            _logger.info(f'Loading existing script {self.path}.')
            if self.versioned:
                _logger.info(f'Renaming existing script {self.path} to {self.versioned_path}.')
                self.path.rename(self.path.with_name(str(self.versioned_path)))
                    
        # -- When script doesn't exist, create it with given attributes ...
        else:
            _logger.info(f'Creating new script {self.path}')
        self.args = args or {}
        self.author = author or ''
        self.code_body = code_body or ''
        self.date = date or datetime.date.today().strftime('%Y-%m-%d')
        self.description = description or ''
        self.libs = libs or []
        self.output_type = OutputType(output_type.lower()) if output_type else None
        self.ret = ret
        self.ret_name = ret_name
        self.suppress_warnings = suppress_warnings
        self.usage = usage or "within `pyrty`"

    def __str__(self):
        return self.build_script()

    @abstractmethod
    def build_script(self) -> str:
        pass

    @abstractmethod
    def make_header(self) -> str:
        pass

    @abstractmethod
    def make_argparsing(self) -> str:
        pass

    @abstractmethod
    def make_body(self) -> str:
        pass

    @abstractmethod
    def make_footer(self) -> str:
        pass

    @abstractmethod
    def get_args(self) -> Dict[str, Union[str, bool]]:
        pass

    def add_arg(self, name: str, **kwargs) -> None:
        if name not in self.args:
            self.args[name] = kwargs

    def add_lib(self, lib: str) -> None:
        if lib not in self.libs:
            self.libs.append(lib)

    def make_header(self, exe) -> str:
        return '\n'.join(filter(None, [
            f'#!/usr/bin/env {exe}',
            f'# Path: {self.path}',
            f'# Author: {self.author}' if self.author else '',
            f'# Date: {self.date}',
            f'# Description: {self.description}' if self.description else '',
            f'# Usage: {self.usage}\n',
        ]))

    def write_to_file(self) -> None:
        if self.versioned:
            self._version += 1
        self.versioned_path.write_text(str(self))

    def delete_file(self) -> None:
        self.versioned_path.unlink()

    def delete_all_versions(self) -> None:
        # TODO: This method needs implementation
        pass

    @property
    def exists(self) -> bool:
        return self.versioned_path.exists()

    @property
    def versioned_path(self) -> Path:
        if not self.versioned:
            return self.path

        script_dir = self.path.parent
        script_path = self.path.stem
        versioned_path = script_dir / f'{str(script_path)}_v{self._version}.{self.ext}'
        return versioned_path