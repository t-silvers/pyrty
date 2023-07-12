import atexit
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Union
from enum import Enum

import pandas as pd

from pyrty.pyr_env import PyREnv
from pyrty.pyr_rscript import PyRScript
from pyrty.registry import DBManager, RegistryManager
from pyrty.utils import run_rscript

_logger = logging.getLogger(__name__)
_reg_manager = RegistryManager()

class Cleanup(Enum):
    ENV = 'env'
    RSCRIPT = 'rscript'


class PyRFunc:
    _db_manager = DBManager()
    
    def __init__(self, alias, env, rscript):
        self.alias = alias
        self.env = env
        self.rscript = rscript
        self._delete_funcs = set()
        self._is_registered = self._db_manager.entry_exists(self.alias)
        
        # TODO: Allow for user-specified directory
        self.reg_manager = _reg_manager


    def __call__(self, finput=None) -> Union[pd.DataFrame, None]:
        with TemporaryDirectory() as tmpdirname:
            opts = []
            if finput:
                for opt_name, opt_val in finput.items():
                    if isinstance(opt_val, pd.DataFrame):
                        tmpfile = Path(tmpdirname) / f'{opt_name}.csv'
                        opt_val.to_csv(tmpfile, index=False)
                        opts.append(f"--{opt_name} {tmpfile}")
                    else:
                        opts.append(f"--{opt_name} {opt_val}")

            run_cmd = f'Rscript {self.rscript_path} {" ".join(opts)}'
            foutput = self.run(run_cmd)
        return foutput

    def __getstate__(self):
        if not all(hasattr(self, attr) for attr in ['env', 'rscript', '_delete_funcs']):
            raise AttributeError("Object is missing required attributes for serialization.")
        return self.env, self.rscript, self._delete_funcs

    def __setstate__(self, state):
        self.env, self.rscript, self._delete_funcs = state

    def __repr__(self) -> str:
        return f'{self.alias}({", ".join(self.args)})'

    @staticmethod
    def _default_env_name(s) -> str:
        return f'{s}-env'

    @staticmethod
    def _default_env_prefix(s) -> Path:
        return _reg_manager.envs / PyRFunc._default_env_name(s)

    @staticmethod
    def _default_rscript_path(s) -> Path:
        return _reg_manager.scripts / f'{s}.R'
    
    @staticmethod
    def _check_obj(obj, cls_type):
        if isinstance(obj, (str, Path)):
            raise NotImplementedError
        elif isinstance(obj, cls_type):
            return obj
        else:
            raise NotImplementedError

    @classmethod
    def _initialize(cls, alias, env, rscript, register, overwrite, cleanup):
        func = cls(alias, env, rscript)
        if register:
            func.register(overwrite)
        else:
            for clean in cleanup:
                if clean == Cleanup.ENV:
                    func._delete_funcs.add(func.env.remove_env()) # remove env on exit
                elif clean == Cleanup.RSCRIPT:
                    func._delete_funcs.add(func.rscript.delete_file()) # remove R script on exit

        return func

    @classmethod
    def _create_rscript(cls, rscript_or_code, opts=None, libs=None, capture_output=False, capture_obj_name=None, 
                        capture_type='df', skip_out_lines=0):
        if isinstance(rscript_or_code, PyRScript):
            return rscript_or_code
        else:
            code = rscript_or_code
            return PyRScript(cls._default_rscript_path(alias), code, libs=libs, opts=opts,
                             capture_output=capture_output, capture_obj_name=capture_obj_name,
                             capture_type=capture_type, skip_out_lines=skip_out_lines)
    
    @classmethod
    def _create_env(cls, env_or_manager, env_kwargs=None):
        if isinstance(env_or_manager, PyREnv):
            return env_or_manager
        else:
            manager = env_or_manager
            return PyREnv(cls._default_env_name(alias), cls._default_env_prefix(alias), manager, env_kwargs=env_kwargs)

    @classmethod
    def from_data(cls, alias, rscript_or_code, env_or_manager='mamba', opts=None, libs=None, capture_output=False, 
                  capture_obj_name=None, capture_type='df', skip_out_lines=0, env_kwargs=None, register=True, 
                  overwrite=False, cleanup=None) -> 'PyRFunc':
        cls_rscript = cls._create_rscript(rscript_or_code, opts=opts, libs=libs, capture_output=capture_output,
                                          capture_obj_name=capture_obj_name, capture_type=capture_type, 
                                          skip_out_lines=skip_out_lines)
        cls_env = cls._create_env(env_or_manager, env_kwargs=env_kwargs)
        return cls._initialize(alias, cls_env, cls_rscript, register, overwrite=overwrite, cleanup=cleanup)

    @classmethod
    def from_rscript(cls, alias, rscript, manager: str = 'mamba', env_kwargs: Union[Dict, None] = None,
                     register: bool = True, overwrite: bool = False) -> 'PyRFunc':
        return cls.from_data(alias, rscript, manager, env_kwargs=env_kwargs, register=register, 
                             overwrite=overwrite, cleanup=['env'])

    @classmethod
    def from_env(cls, alias, env, code: str, opts: Union[List, None] = None, libs: Union[List, None] = None,
                 capture_output: bool = False, capture_obj_name : str = None,
                 capture_type: str = 'df', skip_out_lines: int = 0, register: bool = True, 
                 overwrite: bool = False) -> 'PyRFunc':
        return cls.from_data(alias, code, env, opts=opts, libs=libs, capture_output=capture_output,
                             capture_obj_name=capture_obj_name, capture_type=capture_type, 
                             skip_out_lines=skip_out_lines, register=register, overwrite=overwrite, 
                             cleanup=['rscript'])

    @classmethod
    def from_scratch(cls, alias, code, opts: Union[List, None] = None, libs: Union[List, None] = None,
                     capture_output: bool = False, capture_obj_name : str = None, capture_type: str = 'df',
                     skip_out_lines: int = 0, manager: str = 'mamba', env_kwargs: Union[Dict, None] = None,
                     register: bool = True, overwrite: bool = False) -> 'PyRFunc':
        return cls.from_data(alias, code, manager, opts=opts, libs=libs, capture_output=capture_output,
                             capture_obj_name=capture_obj_name, capture_type=capture_type, 
                             skip_out_lines=skip_out_lines, env_kwargs=env_kwargs, register=register, 
                             overwrite=overwrite, cleanup=['rscript', 'env'])

    @classmethod
    def from_registry(cls, alias: str, alias_new: str = None):
        """
        Notes:
            Can rename the registered alias by passing in `alias_new`. Might be useful
            to allow for multiple aliases to point to the same function, multiple versions
            but with different python class attributes, etc.
        """
        func = cls._db_manager.from_registry(alias)
        setattr(func, 'alias', alias_new or alias)
        return func

    @property
    def args(self) -> List[str]:
        return self.rscript.rscript_manager.get_opts()
    
    @property
    def run_kwargs(self) -> Dict:
        # TODO: Temp for development
        return dict(
            capture_output = self.rscript.capture_output,
            capture_type = self.rscript.capture_type,
            skip_out_lines = self.rscript.skip_out_lines
        )
    
    @property
    def rscript_path(self) -> str:
        return self.rscript.rscript_manager.versioned_path

    def register(self, overwrite: bool = False) -> None:
        if self._is_registered and not overwrite:
            raise ValueError(f'{self.alias} is already registered.')
        PyRFunc._db_manager.register(self.alias, self)
        self._is_registered = True

    def run(self, cmd) -> Union[None, pd.DataFrame]:
        _logger.info(f'Running {self.alias}...\n\tCommand: {cmd}')
        return run_rscript(self.env.get_run_in_env_cmd(cmd), **self.run_kwargs)
    
    def unregister(self):
        self._db_manager.unregister(self.alias)
        self._is_registered = False

    @atexit.register
    def cleanup(self) -> None:
        """
        Notes:
            - This is called when the interpreter exits.
            - This is called after each cell runs when in iPython.
            - This is not called when the interpreter is killed by a signal.
            - This is not called when a thread exits.
        """
        if self._delete_funcs:
            print('Cleaning up...')
            for func in self._delete_funcs:
                func()
            self._delete_funcs.clear()
