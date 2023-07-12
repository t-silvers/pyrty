import shutil
import subprocess
import venv
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from pyrty.script_writers import RScriptWriter
from pyrty.utils import get_conda_exe, get_rscript_exe


class EnvCreator(ABC):
    @abstractmethod
    def exists(self):
        pass

    @abstractmethod
    def create(self):
        pass
    
    @abstractmethod
    def remove(self):
        pass
    
    @abstractmethod
    def get_run_cmd(self, cmd: str):
        pass


class PackratEnvCreator(EnvCreator):
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


class VenvEnvCreator(EnvCreator):
    def __init__(self, name, prefix, packages: list[str]):
        self.name = name
        self.prefix = prefix
        self._exists = Path(self.prefix).is_dir()
        self.packages = packages
        self.env_path = self.create()

    @property
    def exists(self) -> bool:
        return self._exists

    def create(self) -> Path:
        env_path = Path(self.prefix) / self.name
        venv.create(env_path, with_pip=True)
        pip_path = env_path / "bin" / "pip"
        for package in self.packages:
            subprocess.check_call([str(pip_path), "install", package])
        return env_path

    def remove(self) -> None:
        shutil.rmtree(self.env_path)

    def get_run_cmd(self, cmd: str) -> str:
        python_path = self.env_path / "bin" / "python"
        return f'{str(python_path)} -c {cmd}'


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


class RenvEnvCreator(EnvCreator):
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


class CondaEnvCreator(EnvCreator):
    def __init__(
        self,
        name: str,
        prefix: str,
        conda_exe: str = None,
        envfile: str = None,
        postdeploy_cmds: list[str] = None,
        **kwargs
    ):
        self.name = name
        self.prefix = prefix
        self._exists = Path(self.prefix).is_dir()
        self.conda_exe = conda_exe if conda_exe else get_conda_exe(False)
        self._prepare_deploy(envfile, postdeploy_cmds)

    @property
    def exists(self) -> bool:
        return self._exists

    @property
    def _conda_run_cmd(self) -> str:
        """The CLI command to run scripts in env."""
        return f'{self.conda_exe} run -p {self.prefix} {{cmd}}'

    def _prepare_deploy(self, envfile, postdeploy_cmds) -> None:
        if not self.exists:
            if not envfile:
                raise ValueError(f'envfile must be provided if env does not exist: {self.prefix}')
            self.envfile = envfile
            self.deploy_path = self._write_deploy_script()
            self.postdeploy_path = self._write_postdeploy_script(postdeploy_cmds) if postdeploy_cmds else None
        else:
            self.envfile = None
            self.deploy_path = None
            self.postdeploy_path = None

    def _write_deploy_script(self) -> Path:
        deploy_path = Path(self.prefix).parent / f'{self.name}.deploy.sh'
        deploy_commands = (
            f"{self.conda_exe} create -p {self.prefix} --no-default-packages -y\n"
            f"{self.conda_exe} env update -p {self.prefix} --file {self.envfile}\n"
        )
        deploy_path.write_text(deploy_commands)
        return deploy_path

    def _write_postdeploy_script(self, cmds: list[str]) -> Path:
        postdeploy_path = Path(self.prefix).parent / f'{self.name}.post-deploy.sh'
        postdeploy_commands = ''.join([self._conda_run_cmd.format(cmd=cmd) + '\n' for cmd in cmds])
        postdeploy_path.write_text(postdeploy_commands)
        return postdeploy_path

    def create(self) -> None:
        subprocess.run(['bash', str(self.deploy_path)], check=True)
        if self.postdeploy_path:
            subprocess.run(['bash', str(self.postdeploy_path)], check=True)
        self._exists = True
    
    def remove(self) -> None:
        if self.exists:
            remove_env_cmd = f'{self.conda_exe} env remove --prefix {self.prefix} -y'
            subprocess.run(remove_env_cmd, check=True, shell=True)
            self._exists = False
        else:
            raise FileNotFoundError(f'Environment {self.name} does not exist.')

    def get_run_cmd(self, cmd: str) -> str:
        return self._conda_run_cmd.format(cmd=cmd)

    def __str__(self):
        return f'{self.deploy_path}'


class MambaEnvCreator(CondaEnvCreator):
    def __init__(
        self,
        name: str,
        prefix: str,
        conda_exe: str = None,
        envfile: str = None,
        postdeploy_cmds: list[str] = None,
        **kwargs
    ):
        super().__init__(name, prefix, conda_exe=conda_exe, envfile=envfile,
                         postdeploy_cmds=postdeploy_cmds)
        self.conda_exe = conda_exe if conda_exe else get_conda_exe(True)
        self._prepare_deploy(envfile, postdeploy_cmds)
        

class PyREnv:
    """A class to manage the creation of an environment."""

    ENV_CREATORS = {
        'conda': CondaEnvCreator,
        'mamba': MambaEnvCreator,
        'renv': RenvEnvCreator,
        'packrat': PackratEnvCreator,
        'venv': VenvEnvCreator,
    }

    def __init__(
        self,
        name: str,
        prefix: str,
        manager: str,
        env_kwargs: dict,
        create: bool = True,
    ):
        self.name = name
        self.prefix = prefix
        self.manager = manager
        self.env_creator = self._get_env_creator(manager, env_kwargs)
        self.create_env(create)

    def _get_env_creator(self, manager: str, env_kwargs: dict) -> EnvCreator:
        """Returns the environment creator based on the package manager."""
        if manager in self.ENV_CREATORS:
            if manager in ['venv']:
                raise NotImplementedError(f'Package manager {manager} is not supported.')
            return self.ENV_CREATORS[manager](self.name, self.prefix, **env_kwargs)
        else:
            raise ValueError(f'Package manager {manager} is not supported.')

    def create_env(self, create: bool) -> None:
        """Creates the environment if it does not exist."""
        # TODO: Can deprecate this
        if not create:
            pass
        elif create and not self.env_creator.exists:
            self._create_env()
        elif self.env_creator.exists:
            print(f'Environment {self.name} already exists.')
        else:
            raise FileNotFoundError(f'Environment {self.name} does not exist.')

    def _create_env(self) -> None:
        """Creates the environment using the selected environment creator.
        
        Raises:
            FileExistsError: If the environment already exists.
        """
        self.env_creator.create()

    def remove_env(self) -> None:
        """Removes the environment using the selected environment creator.
        
        Raises:
            FileNotFoundError: If the environment does not exist.
        """
        self.env_creator.remove()

    def get_run_in_env_cmd(self, cmd: str) -> str:
        """Executes a command in the environment using the selected environment creator."""
        return self.env_creator.get_run_cmd(cmd)
    
    @classmethod
    def from_existing(cls, name: str, prefix: str, manager: str) -> 'PyREnv':
        """Creates a PyREnv object from an existing environment."""
        return cls(name, prefix, manager, {}, create=False)