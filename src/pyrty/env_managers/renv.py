import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from pyrty.env_managers.base_env import BaseEnvCreator
from pyrty.script_writers import RScriptWriter
from pyrty.utils import get_rscript_exe


class REnvDeployScriptWriter(RScriptWriter):
    def __init__(self, path: Union[str, Path], env_prefix: Union[str, Path], bioc_libs: list = [], cran_libs: list = []):
        self.path = path
        self.env_prefix = env_prefix
        if not Path(env_prefix).is_dir():
            raise ValueError(f'env_prefix must be a valid directory: {env_prefix}')
            
        self.bioc_libs = bioc_libs
        self._use_bioc = len(bioc_libs) > 0
        self.cran_libs = cran_libs
        if self._use_bioc:
            self.cran_libs = \
                ['BiocManager'] + self.cran_libs if 'BiocManager' not in self.cran_libs else self.cran_libs
        self._use_cran = len(cran_libs) > 0
        self.libs = ['renv']
        self.code_body = self._make_renv_code_body()
        super().__init__(path, libs=self.libs, code_body=self.code_body, versioned=False)

    def _make_renv_code_body(self):
        return (
            'renv::init()\n'
            f'setwd({self.env_prefix})\n'
            f'{self._make_cran_libs()}'
            '\n'
            f'{self._make_bioc_libs()}'
            '\n'
            'renv::snapshot()\n'
        )
    
    def _make_cran_libs(self) -> str:
        if self._use_cran:
            return '; '.join(f"install.packages('{pkg}', repos='http://cran.rstudio.com/')" for pkg in self.cran_libs)
        else:
            return ''

    def _make_bioc_libs(self) -> str:
        if self._use_bioc:
            
            return '; '.join(f"BiocManager::install('{pkg}')" for pkg in self.bioc_libs)
        else:
            return ''

    def make_header(self):
        return self.default_header
        
    def make_libraries(self):
        return self.default_libraries

    def make_optparsing(self):
        return ''

    def make_body(self):
        return self.default_body

    def make_footer(self):
        return ''


@dataclass
class REnvDeployRScript:
    path: str
    env_prefix: Union[str, Path]
    cran_libs: list
    bioc_libs: list
    rscript_manager: RScriptWriter = field(init=False)
    
    def __post_init__(self):
        self.cran_libs = self.cran_libs or []
        self.bioc_libs = self.bioc_libs or []
        self.rscript_manager = REnvDeployScriptWriter(self.path, self.env_prefix, cran_libs=self.cran_libs, bioc_libs=self.bioc_libs)
        self.rscript_manager.write_to_file()
    
    def __str__(self):
        return str(self.rscript_manager)


class RenvEnvCreator(BaseEnvCreator):
    def __init__(self, name: str, prefix: str, cran_packages: list[str], bioc_packages: list[str] = [], rscript_exe: str = None):
        self.name = name
        self.prefix = prefix
        self._exists = Path(self.prefix).is_dir()
        self.cran_packages = cran_packages
        self.bioc_packages = bioc_packages
        self.rscript_exe = rscript_exe if rscript_exe else get_rscript_exe()
        self.deploy_path = self._write_deploy_script()

    @property
    def exists(self) -> bool:
        return self._exists

    def _write_deploy_script(self) -> Path:
        deploy_path = Path(self.prefix).parent / f'{self.name}.deploy.R'

        # This class will create the deploy script after init
        deploy_rscript = REnvDeployRScript(deploy_path, f'{self.prefix}/{self.name}',
                                           cran_libs=self.cran_packages,
                                           bioc_libs=self.bioc_packages)

        if deploy_rscript.rscript_manager.versioned_path != deploy_path:
            raise ValueError(f'Expected deploy_path to be {deploy_rscript.rscript_manager.versioned_path}, got {deploy_path}')

        return deploy_path

    def create(self) -> None:
        subprocess.run([self.rscript_exe, str(self.deploy_path)], check=True)
    
    def remove(self) -> None:
        subprocess.run([self.rscript_exe, '-e', f"'unlink(\"{self.prefix}/{self.name}\", recursive = TRUE)'"], check=True)
        
    def get_run_cmd(self, cmd: str) -> str:
        return f'{self.rscript_exe} -e "renv::run(\'{cmd}\')"'
