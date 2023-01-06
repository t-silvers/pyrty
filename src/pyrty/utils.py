import csv
import io
import os
from pathlib import Path
import subprocess
from typing import Dict, Union

import pandas as pd


def subprocess_cli_rscript(
    script: Path,
    env: Path = None,
    args: Dict = None,
    ret: str = None,
    skip_lines: int = 0,
) -> Union[None, pd.DataFrame]:
    """Run a command line interface (CLI) command in a subprocess.

    Parameters
    ----------
    cmd : str
        A command line interface (CLI) command.

    Returns
    -------
    None
    """
    cmd = f"Rscript {script} "
    if env is not None:
        cmd = f"source activate {env} && Rscript {script} "

    if args is not None:
        for k, v in args.items():
            cmd += f"--{k} {v} "

    if ret is not None:
        subprocess.run(cmd, shell=True, check=True)

    else:
        stdout = []
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True) as p:
            with io.TextIOWrapper(p.stdout, newline=os.linesep) as f:
                
                # Must write stdout lines as csv, eg w/ 
                # writeLines(readr::format_csv(mash.res), stdout())
                reader = csv.reader(f, delimiter=",")
                for r in reader:
                    stdout.append(pd.Series(r))
        
        # Convert to dataframe
        df = pd.concat(stdout[skip_lines:], axis=1).set_index(0).T
        df = df.iloc[:-1] # Remove last row of R output
        
        return df