from pathlib import Path

from pyrty.env_managers import _env_managers, BaseEnvManager


class PyREnv:
    def __init__(self, manager: str, env_kwargs: dict):
        self.manager = manager
        self.env_manager = fetch_env_manager(manager)(**env_kwargs)

    def create_env(self) -> None:
        """Creates the environment using the selected environment creator.
        
        Raises:
            FileExistsError: If the environment already exists.
        """
        self.env_manager.create()

    def remove_env(self) -> None:
        """Removes the environment using the selected environment creator.
        
        Raises:
            FileNotFoundError: If the environment does not exist.
        """
        self.env_manager.remove()

    def get_run_in_env_cmd(self, cmd: str) -> str:
        """Executes a command in the environment using the selected environment creator."""
        return self.env_manager.get_run_cmd(cmd)
    
    @classmethod
    def from_existing(cls, manager: str, name: str, prefix: str) -> 'PyREnv':
        """Creates a PyREnv object from an existing environment."""
        return cls(manager, dict(name=name, prefix=prefix))

    @property
    def env_exists(self) -> bool:
        """Whether the environment exists."""
        return self.env_manager.exists

    @property
    def prefix(self) -> Path:
        return self.env_manager.prefix

def fetch_env_manager(manager: str) -> BaseEnvManager:
    try:
        return _env_managers[manager]
    except KeyError:
        raise ValueError(f'Package manager {manager} is not supported.')
