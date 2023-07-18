from pathlib import Path

from pyrty.registry import RegistryManager

_reg_manager = RegistryManager()


DEFAULT_CHANNELS = ['defaults', 'conda-forge']

SHELL_EXE = 'bash'

def default_env_name(s) -> str:
    return f'{s}-env'

def default_env_prefix(s) -> Path:
    return _reg_manager.envs / default_env_name(s)

def write_conda_deploy_script(script_path, conda_exe, prefix, envfile) -> None:
    if not isinstance(script_path, Path):
        script_path = Path(script_path)
    cmds = f'{conda_exe} create -p {prefix} --no-default-packages -y\n{conda_exe} env update -p {prefix} --file {envfile}'
    script_path.write_text(cmds)
