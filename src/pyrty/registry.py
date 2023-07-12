import os
import pickle
import sqlite3
from pathlib import Path


class DBManager:
    def __init__(self, db_filename='registry.db', table_name='registry'):
        self.db_filename = db_filename
        self.table_name = table_name
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_filename) as conn:
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    name TEXT PRIMARY KEY,
                    data BLOB
                )
            ''')

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
        # Remove associated files
        pyr_func = self.from_registry(name)
        pyr_func.env.remove_env()
        pyr_func.rscript.delete_file()
        
        # Remove from registry
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


class RegistryManager:
    def __init__(self, pyrty_dir=None, env_dir=None, script_dir=None):
        # TODO: Temporary for development
        default_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))) / 'usr'
        self.pyrty_dir = pyrty_dir if pyrty_dir is not None else default_dir
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
