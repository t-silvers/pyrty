import copy
import csv
import logging
from csv import reader
from functools import wraps
from io import TextIOWrapper
from os import linesep
from pathlib import Path
from subprocess import PIPE, Popen
from tempfile import TemporaryDirectory
from typing import List, Union

import pandas as pd

from pyrty.utils import run_capture
from pyrty.pyr_env import PyREnv
from pyrty.pyr_script import PyRScript
from pyrty.script_writers.base_script import OutputType

_logger = logging.getLogger(__name__)


def in_run_dir(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with TemporaryDirectory() as tmpdirname:
            # Save the temporary directory name to the instance
            self.tmpdirname = Path(tmpdirname)
            return func(self, *args, **kwargs)
    return wrapper


class RunManager:
    def __init__(self, env: PyREnv, script: PyRScript, skip_lines_output: int = 0):
        self.env = env
        self.script = script
        self.skip_lines_output = skip_lines_output
        self._has_args = bool(script.script_args)
        self._has_ret = script.script_ret
        if self._has_ret:
            self._output_type = script.script_writer.output_type

        # TODO:
        # Set executable for script to environment's executable
        import subprocess
        script_exe_stem = self.script.script_writer._exe
        ret = subprocess.run(self.make_run_cmd(f'which {script_exe_stem}').split(' '), capture_output=True)
        script_exe = ret.stdout.decode('utf-8').replace('\n', '')
        self.script.script_writer._exe = script_exe

    def make_run_cmd(self, cmd):
        return self.env.get_run_in_env_cmd(cmd)

    def parse_argval_intermediates(self, input):
        input_copy = copy.deepcopy(input)
        for arg_name, arg_val in input_copy.items():
            if isinstance(arg_val, pd.DataFrame):
                arg_tmpfile = self.tmpdirname / f'{arg_name}.csv'
                arg_val.to_csv(arg_tmpfile, index=False)
                input_copy[arg_name] = arg_tmpfile
        return input_copy

    def add_args(self, args):
        cmd_w_args = [self.cmd_stub]
        for arg in args:
            cmd_w_args.append(f'--{arg} {{{arg}}}')
        return ' '.join(cmd_w_args)
    
    @in_run_dir
    def run(self, input={}, dry_run=False):
        if self._has_args:
            cmd_stub = self.add_args(input.keys())
            if input:
                input_parsed = self.parse_argval_intermediates(input)
                cmd_stub = cmd_stub.format(**input_parsed)
            else:
                raise ValueError('Script has arguments, but none were provided.')
        else:
            cmd_stub = self.cmd_stub            

        run_cmd = self.make_run_cmd(cmd_stub)
        _logger.info(f'Running ...\n\tCommand: {run_cmd}')
        if dry_run:
            return run_cmd
        return self._run_script(run_cmd)
    
    def _run_script(self, cmd: str) -> Union[OutputType, None]:
        if not self._has_ret:
            with Popen(cmd.split(' ')) as p:
                p.wait()
        elif self._has_ret and self._output_type == OutputType.DF:
            return run_capture(cmd, skip=self.skip_lines_output)
        else:
            raise NotImplementedError

    @property
    def cmd_stub(self):
        return f'{self.script.script_exe} {self.script.script_path}'

    def __str__(self):
        return f'RunManager for {self.script.script_path} in {self.env.env_name}'