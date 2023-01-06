import logging
from pathlib import Path

from pyrty import __version__
from pyrty.env import create_env, _conda_prefix
from pyrty.rscript import RScript
from pyrty.utils import subprocess_cli_rscript

__author__ = "t-silvers"
__copyright__ = "t-silvers"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


class PyRFunc:
    _base_env = _conda_prefix / "pyr"
    _pkgs = ["r-base", "r-optparse", "r-readr", "r-tibble"]

    def __init__(self, alias: str, **kwargs):
        self.alias = alias
        self._make_rscript(**kwargs)

        # Make conda env for pyrty
        if not (self._base_env).exists():
            create_env("conda", prefix="pyr", packages=["mamba"])

        # Make env for function
        if not (self._base_env / "envs" / self.alias).exists():
            self._make_env(**kwargs)        
        
    def _make_rscript(self, **kwargs) -> None:
        rscript = RScript(Path(f"{self.alias}.R"), **kwargs)
        rscript.write(**kwargs)
        setattr(self, "rscript", rscript.rscript)

    def _make_env(self, **kwargs) -> None:
        rfunc_pkgs = kwargs.get("r_packages", [])
        rfunc_pkgs += self._pkgs
        create_env("mamba", name=self.alias, packages=rfunc_pkgs, base_env=self._base_env)

    def __call__(self, input, **kwargs):
        # TODO: Convert input to Path as temp files
        input.to_csv()
        
        # TODO: Activate correct environment
        df = subprocess_cli_rscript(script=self.rscript, **kwargs)
        df = df.iloc[:-1] # Remove last row of R output
        
        return df

    def __repr__(self) -> str:
        return f"{self.alias}"