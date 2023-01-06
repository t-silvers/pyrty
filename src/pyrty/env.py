import logging
import os
from pathlib import Path
import subprocess
from typing import List

_logger = logging.getLogger(__name__)
_conda_prefix = Path(os.environ["CONDA_PREFIX"]).parent


def create_env(
    manager: str,
    prefix: str = None,
    name: str = None,
    pkgs: List[str] = None,
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
        
    pkg_string = " ".join(pkgs)
    cmd = f"{manager} create {env_name} {pkg_string} -c conda-forge --yes"
    
    process = subprocess.Popen(cmd,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               shell=True,
                               encoding='utf-8',
                               errors='replace'
                               )

    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        
        if output:
            print(output.strip(), flush=True)

class PyRFuncEnv:
    _base_env = _conda_prefix / "pyr"
    _pkgs = ["r-base", "r-optparse", "r-readr", "r-tibble"]

    def __init__(self, name: str = None, pkgs: list = []):
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

        pkgs : list
            List of packages to install in the environment.

        base_env : Path
            Path to the conda environment to use as the base for the new
            environment. If not specified, the root environment will be used.
        """
        self.name = name
        self.pkgs = pkgs + self._pkgs

        # Make conda env for pyrty
        if not (self._base_env).exists():
            # Use "pyrty-envs" instead of "envs"?
            create_env("conda", prefix="pyr", pkgs=["mamba"])

        if not (self._base_env / "envs" / self.name).exists():
            self._create_env()

    @property
    def path(self) -> str:
        return (self._base_env / "envs" / self.name).as_posix()

    def _create_env(self):
        _logger.info("Creating conda environment")
        create_env("mamba",
                   name=self.name,
                   pkgs=self.pkgs,
                   base_env=self._base_env
                   )

    def __repr__(self):
        return f"PyRFuncEnv(name={self.name})"
