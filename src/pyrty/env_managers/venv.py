import shutil
import subprocess
import venv
from pathlib import Path

from pyrty.env_managers.base_env import BaseEnvCreator


class VenvEnvCreator(BaseEnvCreator):
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
