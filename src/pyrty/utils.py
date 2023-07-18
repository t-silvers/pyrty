import os
import shutil
from csv import reader
from io import TextIOWrapper
from os import linesep
from subprocess import PIPE, Popen
from typing import List, Union

import pandas as pd


def run_capture(cmd: str, skip: int = 0) -> pd.DataFrame:
    captured_stdout = []
    with Popen(cmd.split(' '), stdout=PIPE) as p:
        with TextIOWrapper(p.stdout, newline=linesep) as f:
            csv_reader = reader(f, delimiter=",")
            for r in csv_reader:
                if r:  # Check if line is not empty
                    captured_stdout.append(r)
    capture_df = (
        pd.concat([pd.Series(__) for __ in captured_stdout[skip:]], axis=1)
        # TODO: Why is stdout sometimes returned with two empty rows?
        .set_index(0).T#.iloc[:-2]
    )
    return capture_df

def get_conda_exe(mamba: bool = False) -> str:
    """
    Note:
        `conda` (and `mamba`) set up a `condabin` (or `mambabin`) such that even when
        `base` is not activated, `conda` (or `mamba`) can be called from the command line.
    """
    return shutil.which('mamba' if mamba else 'conda')

def get_rscript_exe() -> str:
    return shutil.which('Rscript')

def install_r_cli(pkgs: list, install_cmd: str) -> str:
    install_cmds = [install_cmd.format(pkg=pkg) for pkg in pkgs]
    return f"R -e \"{'; '.join(install_cmds)}\"\n"

def install_cran_cli(pkgs: list) -> str:
    return install_r_cli(pkgs, "install.packages('{pkg}', repos='http://cran.rstudio.com/')")

def install_bioc_cli(pkgs: list) -> str:
    return install_r_cli(pkgs, "BiocManager::install('{pkg}')")

def install_pip_cli(): ...