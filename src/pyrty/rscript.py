from pathlib import Path
from typing import Any, List


class RScript:
    def __init__(self, rscript: Path):
        self.rscript = rscript

    @property
    def prelims(self):
        return [
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

    @property
    def _req_libraries(self):
        return ["optparse", "readr", "tibble"]

    # function to write the R script to a file
    def write(self, **kwargs):
        self._create_stub()
        self._add_libraries(**kwargs)

        if 'r_args' in kwargs:
            self._add_args(**kwargs)

        self._add_code(**kwargs)
        
        if 'ret' in kwargs:
            self._add_ret(**kwargs)

    def _create_stub(self):
        with open(self.rscript, 'w') as f:
            f.write('\n'.join(self.prelims))

    def _add_libraries(self, libraries: List[str] = [], **kwargs):
        self.libraries = self._req_libraries
        self.libraries += libraries
        with open(self.rscript, 'a') as f:
            f.write('\n'.join(map(lambda x: f"library({x})", self.libraries)))

    def _add_args(self, r_args: List[str] = [], **kwargs):
        args = ["", "option_list <- list("]
        for __ in r_args:
            arg_s = f"make_option('--{__}', type = 'character', metavar = 'character')"
            # TODO: Add comma if not last arg
            args.append(arg_s)

        args += [")", "opt <- parse_args(OptionParser(option_list=option_list))"]
        with open(self.rscript, 'a') as f:
            f.write('\n'.join(args))

    def _add_code(self, code: List[str] = [], **kwargs):
        with open(self.rscript, 'a') as f:
            f.write('\n'.join(code))

    def _add_ret(self, ret: str, **kwargs):
        ret_lines = [
            "",
            f"{ret}.df <- as_tibble({ret})",
            f"try(writeLines(readr::format_csv({ret}.df), stdout()), silent=TRUE)"
        ]

        with open(self.rscript, 'a') as f:
            f.write('\n'.join(ret_lines))

    def make_executable(self):
        self.rscript.chmod(0o755)