from dataclasses import dataclass, field

from pyrty.script_writers import RScriptWriter


class PyRScriptWriter(RScriptWriter):
    def __init__(self, path, libs: list = [], opts: dict = {}, code_body: str = '',
                 ret: str = None):
        super().__init__(path, libs=libs, opts=opts, code_body=code_body)
        self.ret = ret

    def make_header(self):
        return self.default_header
        
    def make_libraries(self):
        return self.default_libraries

    def make_optparsing(self):
        return self.default_optparsing

    def make_body(self):
        return self.default_body

    def make_footer(self):
        if self.ret:
            # TODO: Other footers for other return types
            return (
                "\n# Printing values\n"
                # TODO: Add support for other return types
                f"try(writeLines(readr::format_csv({self.ret}), stdout()), silent=TRUE)"
            )
        else:
            return self.default_footer

@dataclass
class PyRScript:
    path : str
    code_body : str
    libs : list = field(default_factory=list)
    opts : dict = field(default_factory=dict)
    capture_output : bool = False
    capture_obj_name : str = None
    capture_type : str = 'df'
    skip_out_lines : int = 0
    rscript_manager : RScriptWriter = field(init=False)
    _default_capture_obj_name : str = field(init=False, default='res')

    def write_to_file(self) -> None:
        """Writes the R script to a file using the selected script writer."""
        self.rscript_manager.write_to_file()

    def delete_file(self) -> None:
        """Removes the R script file from the filesystem."""
        self.rscript_manager.delete_file()

    def __post_init__(self):
        # TODO: Should this just error out if `capture_output` is True and `capture_obj_name` is None?
        if self.capture_output and not self.capture_obj_name:
            self.capture_obj_name = self._default_capture_obj_name

        self.rscript_manager = PyRScriptWriter(self.path, libs=self.libs, opts=self.opts,
                                               code_body=self.code_body, ret=self.capture_obj_name)
        self.write_to_file()
    
    def __str__(self):
        return str(self.rscript_manager)
