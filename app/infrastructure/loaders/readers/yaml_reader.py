
"""
Reader for YAML files.

Reads the content of a YAML file and returns it as a string, indented and sorted
by key.
from pathlib import Path
import yaml
from .base_reader import BaseReader

Parameters
----------
path : Path
    Path to the YAML file.
class YamlReader(BaseReader):
    def read(self, path: Path) -> str:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                data = yaml.safe_load(f)
                return yaml.dump(data, default_flow_style=False, sort_keys=True)
        except Exception as e:
            return f"Error reading YAML file: {str(e)}"

Returns
-------
str
    Content of the YAML file as a string.

Raises
------
Exception
    If there's an error reading or processing the file.
"""

from pathlib import Path
import yaml
from .base_reader import BaseReader

class YamlReader(BaseReader):
    def read(self, path: Path) -> str:
        """
        Read the content of a YAML file and return it as a string, indented and
        sorted by key.
        """
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                data = yaml.safe_load(f)
                return yaml.dump(data, default_flow_style=False, sort_keys=True)
        except Exception as e:
            return f"Error reading YAML file: {str(e)}"

