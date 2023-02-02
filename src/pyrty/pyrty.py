import logging
from pathlib import Path
import tempfile
from typing import Dict, List, Union

import pandas as pd

from .env import PyRFuncEnv
from .rscript import RScript
from .utils import run_rscript

__author__ = "t-silvers"
__copyright__ = "t-silvers"
__license__ = "MIT"
__all__ = ["PyRFunc"]

_logger = logging.getLogger(__name__)


class PyRFunc:
    def __init__(self, alias: str, **kwargs):
        self.alias = alias
        self.kwargs = kwargs
        if "libs" in kwargs:
            kwargs["pkgs"] = ["r-{}".format(lib.lower()) for lib in kwargs["libs"]]
        self._make_rscript(**kwargs)
        self._make_env(**kwargs)

    def _make_rscript(self, **kwargs) -> None:
        rscript = RScript(Path(f"{self.alias}.R"), **kwargs)
        if not Path(f"{self.alias}.R").exists():
            # TODO: Or if overwrite=True
            _logger.info("Creating R script")
            rscript.write(**kwargs)
        self.rscript = rscript.rscript

    def _make_env(self, **kwargs) -> None:
        func_env = PyRFuncEnv(name=self.alias, **kwargs)
        self.env = func_env.path.as_posix()

    def __call__(self, input: Dict = None, **kwargs) -> Union[pd.DataFrame, None]:
        with tempfile.TemporaryDirectory() as tmpdirname:
            path_args = dict()
            if input is not None:
                for fn, data in input.items():
                    if not isinstance(data, pd.DataFrame):
                        raise TypeError("Input must be a pandas DataFrame")

                    # Write input data to temporary file(s)
                    data.to_csv(Path(tmpdirname) / f"{fn}.csv", index=False)
                    path_args.update({fn: Path(tmpdirname) / f"{fn}.csv"})

            df = run_rscript(env=self.env, script=self.rscript, args=path_args, **kwargs)
        
        # Will just return None if ret is not specified
        return df

    def __repr__(self) -> str:
        args = ", ".join(self.kwargs.get("r_args", []))
        return f"{self.alias}({args})"