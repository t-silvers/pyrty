from pathlib import Path
from typing import List


class BaseRScript:
    _libraries = ["optparse", "readr", "tibble"]
    _header = [
        "#!/usr/bin/env Rscript",
        "# Path: ",
        "# Author: ",
        "# Date: ",
        "# Description: ",
        "# Usage: ",
        "",
        
        # Suppress all output to keep stdout clean
        "options(warn=-1)",
        "",
        "",        
    ]

class RScript(BaseRScript):
    def __init__(self, rscript: Path, overwrite: bool = True):
        self.rscript = Path(rscript)
        if not self.rscript.exists():
            self._create_stub()
        elif overwrite:
            self._create_stub()

    # function to write the R script to a file
    def write(self, **kwargs):
        self._add_libraries(**kwargs)

        if "r_args" in kwargs:
            self._add_args(**kwargs)

        self._add_code(**kwargs)
        
        if "ret" in kwargs:
            self._add_ret(**kwargs)

    def _create_stub(self):
        with open(self.rscript, "w") as f:
            f.write("\n".join(self._header))

    def _add_libraries(self, libraries: List[str] = [], **kwargs):
        self.libraries = self._libraries
        self.libraries += libraries
        with open(self.rscript, "a") as f:
            f.write("\n".join(map(lambda x: f"library({x})", self.libraries)))

    def _add_args(self, r_args: List[str] = [], **kwargs):
        args = ["", "option_list <- list("]
        for __ in r_args:
            arg_s = f"make_option('--{__}', type = 'character', metavar = 'character')"
            # TODO: Add comma if not last arg
            args.append(arg_s)

        args += [")", "opt <- parse_args(OptionParser(option_list=option_list))"]
        with open(self.rscript, "a") as f:
            f.write("\n".join(args))

    def _add_code(self, code: List[str] = [], **kwargs):
        with open(self.rscript, "a") as f:
            f.write("\n".join(code))

    def _add_ret(self, ret: str, **kwargs):
        ret_lines = [
            "",
            f"{ret}.df <- as_tibble({ret})",
            f"try(writeLines(readr::format_csv({ret}.df), stdout()), silent=TRUE)"
        ]

        with open(self.rscript, "a") as f:
            f.write("\n".join(ret_lines))

    def make_executable(self):
        self.rscript.chmod(0o755)