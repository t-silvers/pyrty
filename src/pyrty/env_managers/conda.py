import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pyrty.env_managers.base_env import BaseEnvManager
from pyrty.env_managers.utils import (
    DEFAULT_CHANNELS,
    default_env_name,
    default_env_prefix,
    write_conda_deploy_script,
)

_logger = logging.getLogger(__name__)


@dataclass
class CondaEnv:
    """Represents a Conda environment."""

    name: str
    dependencies: list
    channels: list = field(default_factory=lambda: DEFAULT_CHANNELS)

    def __str__(self):
        return self.to_yaml()

    def to_yaml(self) -> str:
        """Convert the CondaEnv object to a YAML string.

        Returns:
            str: The YAML representation of the object.
        """
        return yaml.safe_dump(self.__dict__, default_flow_style=False)

    def write(self, path: str) -> None:
        """Write the CondaEnv object to a YAML file.

        Args:
            path (str): The path of the file to write to.
        """
        yaml_string = self.to_yaml()
        with open(path, 'w') as file:
            file.write(yaml_string)

    @classmethod
    def from_yaml(cls, path: str):
        """Create a CondaEnv instance from a YAML file.

        Args:
            path (str): The path of the YAML file.

        Returns:
            CondaEnv: The created CondaEnv instance.
        """
        with open(path, 'r') as file:
            yaml_data = yaml.safe_load(file)

        return cls(yaml_data.get('name', ''),
                   yaml_data.get('dependencies', []),
                   yaml_data.get('channels', []))

    @classmethod
    def from_existing(cls, exe: Path, prefix: Path, path: Path):
        """Create a CondaEnv instance from an existing Conda env.

        Args:
            prefix (str): The path of the Conda env.

        Returns:
            CondaEnv: The created CondaEnv instance.
        """
        subprocess.run(f'{str(exe)} run -p {str(prefix)} {str(exe)} env export > {str(path)}', shell=True, check=True)
        return cls.from_yaml(path)

    @property
    def r_packages(self) -> list:
        """List of R packages (including CRAN and Bioconductor) in the environment.

        Returns:
            list: List of R packages.
        """
        return self.cran_packages + self.bioc_packages

    @property
    def cran_packages(self) -> list:
        """List of CRAN packages in the environment.

        Returns:
            list: List of CRAN packages.
        """
        return [dep for dep in self.dependencies if dep.startswith('r-')]

    @property
    def bioc_packages(self) -> list:
        """List of Bioconductor packages in the environment.

        Returns:
            list: List of Bioconductor packages.
        """
        return [dep for dep in self.dependencies if dep.startswith('bioconductor-')]


class CondaEnvManager(BaseEnvManager):
    def __init__(
        self,
        exe: Path = None,
        prefix: Path = None,
        envfile: Path = None,
        name: str = None,
        dependencies: list = None,
        channels: list = None,
        postdeploy_cmds: list[str] = None,
    ):
        self._exe = exe if exe else shutil.which("conda")
        self._prefix = prefix
        self.envfile = envfile
        self._name = name
        self._dependencies = dependencies
        self.channels = channels or DEFAULT_CHANNELS
        self.postdeploy_cmds = postdeploy_cmds

    def create(self):
        # Overwrite
        self._process_env_specs(self.prefix, self.envfile, self.name,
                                self.dependencies, self.channels)
        self._write_deploy_script()
        self._process_postdeploy_cmds(self.postdeploy_cmds)
        super().create()

    def _process_env_specs(self, prefix, envfile, name, dependencies, channels):
        if not envfile and name:
            envfile = Path(f"{name}.yaml")
        elif not envfile and not name:
            raise ValueError("Must provide either a path (to `envfile`) or name.")
        self.envfile = Path(envfile)
        
        # -- When environment already exists ...
        self._prefix = prefix # May be None
        if self.exists:
            _logger.info(f"Environment exists at {self.prefix}.")
            self._env = CondaEnv.from_existing(self.exe, self.prefix, self.envfile)

        else:
            if not self.prefix: # Now must be provided or generated
                if name:
                    self._prefix = default_env_prefix(name)
                elif not name and envfile:
                    # Parse name from envfile
                    with open(self.envfile, 'r') as file:
                        yaml_data = yaml.safe_load(file)
                        name = yaml_data['name'] # Should error if name not in yaml_data
                    self._prefix = name
                else:
                    raise ValueError("Must provide either an envfile or name and dependencies.")

            # -- When environment file exists ...
            if self.envfile.exists():
                _logger.info(f"Environment file {self.envfile} exists.")
                self._env = CondaEnv.from_yaml(self.envfile)

            # -- When environment dependencies are provided ...
            elif name and dependencies:
                name_ = default_env_name(name)
                _logger.info(f"Creating environment {name_} with dependencies {dependencies}.")
                self._env = CondaEnv(name_, dependencies, channels)
                self._env.write(self.envfile)
            
            # -- Else ...
            else:
                raise ValueError("Must provide either an envfile or name and dependencies.")

        self._name = self.env.name

    def add_channel(self, channel) -> None:
        if channel not in self.channels:
            self.channels.append(channel)

    # def add_dependency(self, dependency) -> None:
    #     if dependency not in self.dependencies:
    #         self.dependencies.append(dependency)

    @property
    def deploy_script_path(self) -> Path:
        return Path(self.prefix).parent / f"{self.name}.deploy.sh"

    @property
    def dependencies(self):
        return self._dependencies

    @dependencies.setter
    def add_dependency(self, dependency):
        if dependency not in self._dependencies:
            self._dependencies.append(dependency)

    @property
    def env(self):
        return self._env

    @property
    def name(self):
        return self._name

    @property
    def postdeploy_script_path(self) -> Path:
        return Path(self.prefix).parent / f"{self.name}.post-deploy.sh"

    @property
    def prefix(self):
        return self._prefix

    @property
    def remove_cmd(self):
        return f"{self.exe} env remove --prefix {self.prefix} -y"

    @property
    def run_cmd_template(self) -> str:
        return f"{self.exe} run -p {self.prefix} {{cmd}}"

    def _write_deploy_script(self) -> None:
        write_conda_deploy_script(self.deploy_script_path, self.exe, self.prefix, self.envfile)

    def _process_postdeploy_cmds(self, postdeploy_cmds):
        if postdeploy_cmds:
            self._write_postdeploy_script(postdeploy_cmds)

    def _write_postdeploy_script(self, cmds: list[str]) -> None:
        postdeploy_commands = "\n".join([self.get_run_cmd(cmd) for cmd in cmds])
        self.postdeploy_script_path.write_text(postdeploy_commands)

class MambaEnvManager(CondaEnvManager):
    def __init__(
        self,
        exe: Path = None,
        prefix: Path = None,
        envfile: Path = None,
        name: str = None,
        dependencies: list = None,
        channels: list = None,
        postdeploy_cmds: list[str] = None,
    ):
        super().__init__(exe=exe or shutil.which("mamba"), prefix=prefix,
                         envfile=envfile, name=name, dependencies=dependencies,
                         channels=channels, postdeploy_cmds=postdeploy_cmds)