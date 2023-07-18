from importlib.metadata import PackageNotFoundError, version

try:
    dist_name = __name__
    __version__ = version(dist_name)
except PackageNotFoundError:
    __version__ = 'unknown'
finally:
    del version, PackageNotFoundError

# import logging
# _logger = logging.getLogger(__name__)

from pyrty.pyr_env import PyREnv
from pyrty.pyr_func import PyRFunc
from pyrty.pyr_script import PyRScript
from pyrty.registry import DBManager, RegistryManager, unregister_pyrty_func

__all__ = ['PyREnv', 'PyRScript', 'PyRFunc', 'DBManager', 'RegistryManager', 'unregister_pyrty_func']