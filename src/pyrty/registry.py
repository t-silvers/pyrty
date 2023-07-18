import os
import pickle
import sqlite3
from pathlib import Path


class DBManager:
    def __init__(self, db_filename='registry.db', table_name='registry', db_dir: Path = None):
        self.db_filename = str(db_dir / db_filename) if db_dir is not None else str(_get_default_dir() / db_filename)
        self.table_name = table_name
        self._init_db()

    def entry_exists(self, name):
        with sqlite3.connect(self.db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name} WHERE name = ?", (name,))
            tbl_entries = cursor.fetchone()
            return tbl_entries[0] > 0

    def list_entries(self):
        with sqlite3.connect(self.db_filename) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM {self.table_name}")
            tbl_entries = cursor.fetchall()
            entry_names = [entry[0] for entry in tbl_entries]
            return entry_names

    def register(self, name, instance):
        with sqlite3.connect(self.db_filename) as conn:
            pickled_data = pickle.dumps(instance)
            conn.execute(f"INSERT OR REPLACE INTO {self.table_name} (name, data) VALUES (?, ?)",
                         (name, pickled_data))
            conn.commit()

    def from_registry(self, name):
        with sqlite3.connect(self.db_filename) as conn:
            cursor = conn.execute(f"SELECT data FROM {self.table_name} WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"No instance is registered with name {name}")
            return pickle.loads(row[0])

    def unregister(self, name):
        pyr_func = self.from_registry(name)
        pyr_func.cleanup() # Only generated files are removed
        with sqlite3.connect(self.db_filename) as conn:
            conn.execute(f"DELETE FROM {self.table_name} WHERE name = ?", (name,))
            conn.commit()

    def purge_registry(self):
        registry_names = self.list_entries()
        print(registry_names)
        for name in registry_names:
            pyr_func = self.from_registry(name)
            pyr_func.cleanup()
            pyr_func.unregister()

    def _init_db(self):
        with sqlite3.connect(self.db_filename) as conn:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    name TEXT PRIMARY KEY,
                    data BLOB
                )
            ''')

    def __str__(self):
        return f"DB filename: {self.db_filename}\n" \
               f"Table name: {self.table_name}"


class RegistryManager:
    def __init__(self, pyrty_dir=None, env_dir=None, script_dir=None):
        # TODO: Temporary for development
        self.pyrty_dir = pyrty_dir if pyrty_dir is not None else _get_default_dir()
        self.envs = env_dir if env_dir is not None else self.pyrty_dir / 'envs'
        self.scripts = script_dir if script_dir is not None else self.pyrty_dir / 'scripts'
        
    def set_pyrty_dir(self, path):
        self.pyrty_dir = Path(path)
        self.envs = self.pyrty_dir / 'envs'
        self.scripts = self.pyrty_dir / 'scripts'

    def set_env_dir(self, path):
        self.envs = Path(path)
        
    def set_script_dir(self, path):
        self.scripts = Path(path)
        
    def get_locations(self):
        return {
            "envs": str(self.envs.resolve()),
            "scripts": str(self.scripts.resolve())
        }

    def __str__(self):
        return f"PyRty directory: {self.pyrty_dir}\n" \
               f"Envs directory: {self.envs}\n" \
               f"Scripts directory: {self.scripts}"


def _get_default_dir():
    return Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))) / 'usr'

unregister_pyrty_func = DBManager().unregister
"""Convenience function for removing a PyRty function from the registry.

Args:
    name (str): The name of the PyRty function to remove.
"""