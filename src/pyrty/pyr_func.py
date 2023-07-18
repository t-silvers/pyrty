import atexit
import logging
import re
from pathlib import Path
from typing import List, Union, Dict

from pyrty.pyr_env import PyREnv
from pyrty.pyr_script import PyRScript
from pyrty.registry import DBManager, RegistryManager
from pyrty.run_manager import RunManager
from pyrty.script_writers.base_script import OutputType

_logger = logging.getLogger(__name__)
_reg_manager = RegistryManager()
_db_manager = DBManager(db_dir=_reg_manager.pyrty_dir)


class PyRFunc:
    def __init__(self, alias: str, script: PyRScript = None, env: PyREnv = None, keep: bool = True):
        self.alias = alias
        self.script = script
        self.env = env
        self.keep = keep
        self.run_manager = None
        self._args = []
        self._delete_funcs = set()

    def __call__(self, input=None):
        output = self.run_manager.run(input)
        return output

    def __getstate__(self):
        if not all(hasattr(self, attr) for attr in ['env', 'script', 'run_manager', '_delete_funcs']):
            raise AttributeError("Object is missing required attributes for serialization.")
        return self.env, self.script, self.run_manager, self._delete_funcs

    def __setstate__(self, state):
        self.env, self.script, self.run_manager, self._delete_funcs = state

    def __repr__(self) -> str:
        return f'{self.alias}({self.args})'

    def add_env(self, manager: str, env_kwargs: Dict) -> None:
        self.env = PyREnv(manager, env_kwargs)

    def add_script(self, lang: str, script_kwargs: Dict) -> None:
        self.script = PyRScript(lang, script_kwargs)

    def register(self, overwrite: bool = False) -> None:
        if self.registered and not overwrite:
            raise ValueError(f'{self.alias} is already registered.')
        self._create_func()
        _db_manager.register(self.alias, self)

    def unregister(self):
        _db_manager.unregister(self.alias)

    def cleanup(self):
        if self._delete_funcs:
            for func in self._delete_funcs:
                func()
            self._delete_funcs.clear()

    def _create_func(self):
        # Check for conflicts
        self._resolve_conflicts()

        # Create components
        if not self.script.script_exists:
            self.script.create_script()
            self._delete_funcs.add(self.script.delete_script)

        if not self.env.env_exists:
            self.env.create_env()
            self._delete_funcs.add(self.env.remove_env)

        # Set up run manager
        self.run_manager = RunManager(self.env, self.script)

    def _resolve_conflicts(self):
        # --
        # TODO: Temp for development
        if self.script.lang == 'R':
            if (self.env.manager in ['conda', 'mamba'] and
                not self.env.env_manager.envfile and
                not self.env.env_exists):
                # If need to create env, but no envfile, add r-essentials and r-base
                self.env.env_manager.add_channel('r')
                self.env.env_manager.add_dependency = 'r-essentials'
                self.env.env_manager.add_dependency = 'r-base'

            if self.script.script_writer.args:
                self.script.script_writer.add_lib('optparse')

            if self.script.script_writer.ret:
                if self.script.script_writer.output_type == OutputType.DF:
                    self.script.script_writer.add_lib('readr')
        # --

    @classmethod
    def from_scratch(
        cls,
        alias: str,
        manager: str,
        lang: str,
        args: Dict[str, Dict] = None,
        code: str = None,
        deps: Dict[str, List] = None,
        envfile: Path = None,
        output_type: str = None,
        prefix: Path = None,
        ret_name: str = None,
        env_kwargs: Dict = None,
        script_kwargs: Dict = None,
        register: bool = True,
    ):        
        # --
        # TODO: Refactor this logic to use a builder pattern
        if not env_kwargs:
            env_kwargs = {}
            env_kwargs['envfile'] = envfile
            env_kwargs['name'] = f'{alias}-env'
            env_kwargs['prefix'] = prefix or _reg_manager.envs / f'{alias}-env'
            
            # `deps` parsing
            if isinstance(deps, dict):
                env_kwargs['dependencies'] = parse_dependency_config(deps)
            elif isinstance(deps, list):
                env_kwargs['dependencies'] = deps # Assume they're already parsed
            else:
                raise ValueError(f'Invalid type for `deps`: {type(deps)}')

        if not script_kwargs:
            script_kwargs = {}
            script_kwargs['args'] = args or {}
            script_kwargs['code_body'] = code
            script_kwargs['output_type'] = output_type
            script_kwargs['path'] = _reg_manager.scripts / f'{alias}.{lang.lower()}'
            script_kwargs['ret'] = bool(output_type)
            script_kwargs['ret_name'] = ret_name or parse_output_from_rscript(code) if output_type else None
            
            # `deps` parsing
            if isinstance(deps, dict):
                if lang == 'R':
                    script_kwargs['libs'] = deps.get('cran', []) + deps.get('bioc', []) if deps else []
                elif lang == 'python':
                    script_kwargs['libs'] = deps.get('pypi', []) + deps.get('conda', []) if deps else []
                else:
                    raise NotImplementedError
            elif isinstance(deps, list):
                script_kwargs['libs'] = deps # Assume they're already parsed
        
        # --
        
        # Create the function
        pyr_func = cls(alias, keep=register)
        pyr_func.add_env(manager, env_kwargs)
        pyr_func.add_script(lang, script_kwargs)
        pyr_func.register()

        return pyr_func

    @classmethod
    def from_registry(cls, alias: str, alias_new: str = None):
        """
        Notes:
            Can rename the registered alias by passing in `alias_new`. Might be useful
            to allow for multiple aliases to point to the same function, multiple versions
            but with different python class attributes, etc.
        """
        func = _db_manager.from_registry(alias)
        setattr(func, 'alias', alias_new or alias)
        return func

    @property
    def args(self) -> str:
        return ", ".join(self.script.script_args)

    @property
    def registered(self) -> bool:
        return _db_manager.entry_exists(self.alias)

    @property
    def script_path(self) -> str:
        return self.script.script_writer.versioned_path

    @atexit.register
    def cleanup_unregistered(self) -> None:
        """
        Notes:
            - This is called when the interpreter exits.
            - This is called after each cell runs when in iPython.
            - This is not called when the interpreter is killed by a signal.
            - This is not called when a thread exits.
        """
        if self.keep == False:
            self.cleanup()
            self.unregister()

def parse_output_from_rscript(s):
    # TODO: Handle '<-' or '=' (or ' <-')
    # TODO: Should add third case: when at start of line
    if len(s.split(' <-')) == 2:
        return s.split(' <-')[0].strip()
    else:
        return re.findall(r"(?:;|\n)\s*(.*?) <-", s)[-1]

def parse_dependency_config(conf: Dict):
    cran_deps = [f'r-{dep.lower()}' for dep in conf.get('cran', [])]
    bioc_deps = [f'bioconductor-{dep.lower()}' for dep in conf.get('bioc', [])]
    conda_deps = [dep.lower() for dep in conf.get('conda', [])]
    pip_deps = [dep.lower() for dep in conf.get('pypi', [])]
    
    return cran_deps + bioc_deps + conda_deps + pip_deps