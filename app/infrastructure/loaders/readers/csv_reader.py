
"""
Reader for comma-separated values (CSV) files.

This reader reads a CSV file and returns its content as a string, with each row
separated by a newline character and each column separated by a comma and a
space.

Example:
    >>> reader = CsvReader()
    >>> reader.read(Path('example.csv'))
    'column1, column2, column3\n1, 2, 3\n4, 5, 6\n'
"""

import csv
from pathlib import Path
from .base_reader import BaseReader


class CsvReader(BaseReader):
    """
    Reader for comma-separated values (CSV) files.
    """

    def read(self, path: Path) -> str:
        """
        Read a CSV file and return its content as a string.

        Parameters
        ----------
        path : Path
            Path to the CSV file.

        Returns
        -------
        str
            Content of the CSV file as a string.
        """
        try:
            with open(path, newline='', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f)
                return "\n".join(", ".join(row) for row in reader)
        except Exception as e:
            return f"Error reading CSV file: {str(e)}"
