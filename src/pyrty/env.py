import logging
import os
from pathlib import Path
import subprocess
from typing import List

__all__ = ["PyRFuncEnv"]

_logger = logging.getLogger(__name__)
_conda_prefix = Path(os.environ["CONDA_PREFIX"]).parent


def create_env(
    manager: str,
    prefix: str = None,
    name: str = None,
    conda_pkgs: List[str] = None,
    channels: List[str] = None,
    r_pkgs: List[str] = None,
    base_env: Path = None,
) -> None:
    """Create a conda environment."""
    if manager not in ["conda", "mamba"]:
        raise ValueError("Env manager must be either conda or mamba")
    
    if name is not None and prefix is not None:
        raise ValueError("Cannot specify both name and prefix")
    
    elif name is not None:
        env_name = f"-n {name}"

    elif prefix is not None:
        env_name = f"--prefix {_conda_prefix}/{prefix}"
    
    else:
        raise ValueError("Must specify either name or prefix")
    
    cmd = ""
    if base_env is not None:
        cmd = "source activate {} && ".format(base_env.as_posix())
        
    pkg_string = " ".join(conda_pkgs)
    
    default_channels = ["-c conda-forge"]
    if channels is not None:
        if not isinstance(channels, list):
            raise TypeError
        for channel in channels:
            default_channels.append(f"-c {channel}")
    channels_string = " ".join(default_channels)
    
    cmd = f"{manager} create {env_name} {pkg_string} {channels_string} --yes"
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               shell=True,
                               encoding='utf-8',
                               errors='replace')

    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        
        if output:
            print(output.strip(), flush=True)
            
    if r_pkgs is not None:
        # TODO: add note that r_pkgs should be install commands
        # TODO: set mirror or check for mirror
        r_pkg_instructions = ";".join(r_pkgs)
        # TODO: Will fail in the prefix=None case        
        cmd = f"source activate {_conda_prefix}/{prefix} && R -e '{r_pkg_instructions}'"
        
        process = subprocess.Popen(cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   shell=True,
                                   encoding='utf-8',
                                   errors='replace')

        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            
            if output:
                print(output.strip(), flush=True)
        

class PyRFuncEnv:
    _base_env = _conda_prefix / "pyr"
    _pkgs = ["r-base", "r-optparse", "r-readr", "r-tibble"]

    def __init__(
        self,
        name: str = None,
        conda_pkgs: list = [],
        channels: list = [],
        r_pkgs: list = [],
        r_ver: str = "default",
        **kwargs,
    ):
        """
        Create a conda environment to run R scripts in.

        Parameters
        ----------
        name : str
            Name of the conda environment. If not specified, a random name
            will be generated.

        prefix : str
            Name of the subdirectory to create the environment in. If not
            specified, a random name will be generated.

        conda_pkgs : list
            List of packages to install in the environment from a conda distribution.

        r_pkgs : list
            List of packages to install in the environment from an R distribution.

        base_env : Path
            Path to the conda environment to use as the base for the new
            environment. If not specified, the root environment will be used.
        """
        self.name = name
        self.conda_pkgs = conda_pkgs + self._pkgs
        self.channels = channels
        self.r_pkgs = r_pkgs
        self.r_ver = r_ver
        if self.r_ver != "default":
            self.r_pkgs[0] = self.r_pkgs[0] + f"=={self.r_ver}"

        # Make conda env for pyrty
        if not (self._base_env).exists():
            create_env("conda", prefix="pyr", conda_pkgs=["mamba"])

        if not self.path.exists():
            self._create_env()

    @property
    def path(self) -> str:
        return (self._base_env / "pyrty-envs" / self.name)

    def _create_env(self):
        _logger.info("Creating conda environment")
        create_env("mamba",
                   prefix=f"pyr/pyrty-envs/{self.name}",
                   conda_pkgs=self.conda_pkgs,
                   channels=self.channels,
                   r_pkgs=self.r_pkgs,
                   base_env=self._base_env)

    def __repr__(self):
        return f"PyRFuncEnv(name={self.name})"
