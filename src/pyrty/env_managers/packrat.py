import shutil
import subprocess
import venv
from abc import ABC, abstractmethod
from pathlib import Path

from pyrty.env_managers.base_env import BaseEnvCreator
from pyrty.utils import get_rscript_exe


class PackratEnvCreator(BaseEnvCreator):
    def __init__(self, name, prefix, cran_packages: list[str], rscript_exe: str = None):
        self.name = name
        self.prefix = prefix
        self._exists = Path(self.prefix).is_dir()
        self.cran_packages = cran_packages
        self.rscript_exe = rscript_exe if rscript_exe else get_rscript_exe()
        self.deploy_path = self._write_deploy_script(self.cran_packages)

    @property
    def exists(self) -> bool:
        return self._exists

    def _write_deploy_script(self, cran_packages) -> Path:
        deploy_path = Path(self.prefix).parent / f'{self.name}.deploy.R'
        deploy_commands = (
            'library(packrat)\n'
            f'setwd("{self.prefix}/{self.name}")\n'
            'packrat::init()\n'
            # '; '.join(f"install.packages('{pkg}', repos='http://cran.rstudio.com/')" for pkg in cran_packages)
            '\n'
            'packrat::snapshot()\n'
        )
        deploy_path.write_text(deploy_commands)
        return deploy_path

    def create(self) -> None:
        subprocess.run([self.rscript_exe, str(self.deploy_path)], check=True)

    def remove(self) -> None:
        subprocess.run([self.rscript_exe, '-e', f"'unlink(\"{self.prefix}/{self.name}\", recursive = TRUE)'"], check=True)

    def get_run_cmd(self, cmd: str) -> str:
        return f'{self.rscript_exe} -e "packrat::run(\'{cmd}\')"'
