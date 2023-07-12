import csv
import os
import shutil
from io import TextIOWrapper
from subprocess import PIPE, Popen
from typing import Union

import pandas as pd


def is_enquoted(s: str) -> bool:
    if not isinstance(s, str):
        return False
    
    if len(s) < 2:
        return False

    if s[0] == s[-1] == "'":
        return True

    if s[0] == s[-1] == '"':
        return True

    return False

def capture_line_df(stdout: str) -> pd.Series:
    return pd.Series(stdout)

def parse_stdout_df(stdout: list, skip_out_lines: int = 0) -> pd.DataFrame:
    """Parse stdout from R as a dataframe.
    
    Note:
        R stdout is formatted as a csv, eg:
        ```
        "","A","B","C"
        "1",1,2,3,
        "2",4,5,6,
        ```
    """
    df = pd.concat(stdout[skip_out_lines:], axis=1).set_index(0).T
    # TODO: Why is stdout being returned with two empty rows?
    df = df.iloc[:-2] # Remove last row of R output
    return df

def run_rscript(rscript_cmd: str, capture_output: bool = True, capture_type: str = 'df',
                skip_out_lines: int = 0) -> Union[None, pd.DataFrame]:
    """Run a command line interface (CLI) command in a subprocess.
    
    TODO: Should proceed from the Rscript executable, eg `Rscript -e "..."`.
    
    Optionally capture the stdout of the subprocess and return it as a pandas dataframe.
    TODO: Add support for other capture types, eg 'list', 'dict', 'str', 'json', etc.
    """
    if capture_output:
        captured_stdout = []
        if capture_type == 'df':
            capture_func = capture_line_df
            parse_func = parse_stdout_df
        
        with Popen(rscript_cmd, stdout=PIPE, shell=True) as p:
            with TextIOWrapper(p.stdout, newline=os.linesep) as f:
                # Must write stdout lines as csv, eg w/ writeLines(readr::format_csv(mash.res), stdout())
                reader = csv.reader(f, delimiter=",")
                for r in reader:
                    captured_stdout.append(capture_func(r))
        parsed_stdout = parse_func(captured_stdout, skip_out_lines)

        return parsed_stdout
    else:
        with Popen(rscript_cmd, shell=True) as p:
            p.wait()

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