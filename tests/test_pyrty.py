import shutil
import subprocess
from pathlib import Path
from typing import Union

import pytest

from pyrty.env_managers.conda import write_conda_deploy_script
from pyrty.env_managers.utils import SHELL_EXE
from pyrty.pyr_env import PyREnv
from pyrty.pyr_script import PyRScript
from pyrty.script_writers import BaseScriptWriter


@pytest.fixture
def pyr_env_params():
    base_dir = Path(__file__).parent
    manager = 'mamba'
    name = 'test-env'
    prefix = base_dir / './envs/test-env'
    envfile = base_dir / './envs/test-env.yaml'
    deploy = base_dir / './envs/test.deploy.sh'
    pyscript = base_dir / './scripts/run_in_env.py'
    return manager, name, prefix, envfile, deploy, pyscript

def test_pyrenv_from_params(pyr_env_params):
    manager, name, prefix, __, __, pyscript = pyr_env_params
    pyr_env = PyREnv(manager, dict(name=name, prefix=prefix, dependencies=['tqdm']))
    _test_pyrenv(pyr_env, pyscript)

def test_pyrenv_from_envfile(pyr_env_params):
    manager, name, prefix, envfile, __, pyscript = pyr_env_params
    pyr_env = PyREnv(manager, dict(envfile=envfile, name=name, prefix=prefix))
    _test_pyrenv(pyr_env, pyscript)

def test_pyrenv_from_existing(pyr_env_params):
    manager, name, prefix, envfile, deploy, pyscript = pyr_env_params
    conda_exe = shutil.which(manager)
    write_conda_deploy_script(deploy, conda_exe, prefix, envfile)
    subprocess.run([SHELL_EXE, str(deploy)], check=True)
    pyr_env = PyREnv(manager, dict(name=name, prefix=prefix))
    _test_pyrenv(pyr_env, pyscript)

def _test_pyrenv(env: PyREnv, script: Union[Path, str]):
    # Test some properties and teardown
    assert env.env_exists
    subprocess.run(env.get_run_in_env_cmd(f'python {script}'), shell=True, check=True)
    env.remove_env()
    assert not env.env_exists

@pytest.fixture
def pyr_script_params():
    base_dir = Path(__file__).parent
    author = 'TestAuthor'
    description = 'TestDescription'
    args = {'arg1': {}, 'arg2': {}}
    return base_dir, author, description, args

def test_rscriptwriter():
    bdir, aut, descr, args = pyr_script_params
    path = bdir / 'test.R'
    libs = ['dplyr', 'ggplot2']
    pyr_script = PyRScript('R', dict(path=path, author=aut, description=descr, libs=libs, args=args))
    writer: BaseScriptWriter = pyr_script.script_writer
    assert writer.path == path
    _script_attrs(writer)
    assert writer.libs == libs
    input_args = dict()
    for k,v in writer.args.items():
        input_args[k] = [v for k,v in v.items() if v != 'NULL' and k != 'name']
    assert input_args == {'arg1': [], 'arg2': []}
    _script_write_remove(writer)

def test_pyscriptwriter():
    bdir, aut, descr, args = pyr_script_params
    path = bdir / 'test.py'
    libs = ['numpy', 'pandas']
    pyr_script = PyRScript('python', dict(path=path, author=aut, description=descr, libs=libs, args=args))
    writer: BaseScriptWriter = pyr_script.script_writer
    assert writer.path == path
    _script_attrs(writer)
    assert writer.libs == libs
    input_args = dict()
    for k,v in writer.args.items():
        input_args[k] = [v for k,v in v.items() if v != 'None' and k != 'name']
    assert input_args == {'arg1': ["''"], 'arg2': ["''"]} # TODO:
    _script_write_remove(writer)

def test_shscriptwriter():
    bdir, aut, descr, __ = pyr_script_params
    path = bdir / 'test.sh'
    libs = ['source1.sh', 'source2.sh']
    pyr_script = PyRScript('shell', dict(path=path, author=aut, description=descr, libs=libs))
    writer: BaseScriptWriter = pyr_script.script_writer
    assert writer.path == path
    _script_attrs(writer)
    _script_write_remove(writer)

def _script_attrs(writer: BaseScriptWriter):
    assert str(writer) is not None
    __, aut, descr, __ = pyr_script_params
    assert writer.author == aut
    assert writer.description == descr

def _script_write_remove(writer: BaseScriptWriter):
    writer.write_to_file()
    assert writer.versioned_path.exists()
    writer.delete_file()
    assert not writer.versioned_path.exists()