import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from pyrty.env_managers.utils import SHELL_EXE


class BaseEnvManager(ABC):

    def __str__(self) -> str:
        return super().__str__()

    def get_run_cmd(self, cmd: str) -> str:
        return self.run_cmd_template.format(cmd=cmd)

    def create(self) -> None:
        subprocess.run([SHELL_EXE, str(self.deploy_script_path)], check=True)
        if self.postdeploy_script_path.exists():
            subprocess.run([SHELL_EXE, str(self.postdeploy_script_path)], check=True)

    def remove(self) -> None:
        if self.exists:
            subprocess.run(self.remove_cmd, check=True, shell=True)
            
            # TODO: Something strange happening here on unregistering
            if self.deploy_script_path.exists():
                self.deploy_script_path.unlink()
            
            if self.postdeploy_script_path.exists():
                self.postdeploy_script_path.unlink()
        else:
            raise FileNotFoundError(f'Environment {self.prefix} does not exist.')        

    @property
    @abstractmethod
    def deploy_script_path(self):
        pass

    @property
    @abstractmethod
    def env(self):
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def postdeploy_script_path(self):
        pass

    @property
    @abstractmethod
    def prefix(self):
        pass

    @property
    @abstractmethod
    def remove_cmd(self):
        pass

    @property    
    @abstractmethod
    def run_cmd_template(self):
        pass
    
    @property
    def exe(self) -> str:
        return self._exe

    @property
    def exists(self) -> bool:
        if self.prefix:
            return Path(self.prefix).is_dir()
        else:
            return False