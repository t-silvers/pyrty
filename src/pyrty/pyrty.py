import logging
from pathlib import Path

from pyrty import __version__
from pyrty.env import PyRFuncEnv
from pyrty.rscript import RScript
from pyrty.utils import subprocess_cli_rscript

__author__ = "t-silvers"
__copyright__ = "t-silvers"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


class PyRFunc:
    def __init__(self, alias: str, **kwargs):
        self.alias = alias
        self._make_rscript(**kwargs)
        self._make_env(**kwargs)
        
    def _make_rscript(self, **kwargs) -> None:
        _logger.info("Creating R script")
        rscript = RScript(Path(f"{self.alias}.R"), **kwargs)
        rscript.write(**kwargs)
        setattr(self, "rscript", rscript.rscript)

    def _make_env(self, **kwargs) -> None:
        func_env = PyRFuncEnv(name=self.alias, **kwargs)
        self.env = func_env.path

    def __call__(self, input, **kwargs):
        # TODO: Convert input to Path as temp files
        input.to_csv()
        
        # TODO: Activate correct environment
        df = subprocess_cli_rscript(script=self.rscript, **kwargs)
        df = df.iloc[:-1] # Remove last row of R output
        
        return df

    def __repr__(self) -> str:
        return f"{self.alias}"