import os
from pathlib import Path
import subprocess
from typing import List


_conda_prefix = Path(os.environ["CONDA_PREFIX"]).parent


def create_env(
    manager: str,
    prefix: str = None,
    name: str = None,
    packages: List[str] = None,
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
        
    pkg_string = " ".join(packages)
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