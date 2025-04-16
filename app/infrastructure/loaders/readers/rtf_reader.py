
from pathlib import Path
from .base_reader import BaseReader

class RtfReader(BaseReader):
    """
    Reader for Rich Text Format (.rtf) files.
    """

    def read(self, path: Path) -> str:
        """
        Read and extract text content from an RTF file.

        Parameters
        ----------
        path : Path
            Path to the RTF file.

        Returns
        -------
        str
            Extracted text content from the RTF file.

        Raises
        ------
        Exception
            If there's an error reading or processing the file.
        """
        try:
            import striprtf.striprtf as striprtf
            content = path.read_bytes().decode('utf-8', errors='replace')
            return striprtf.rtf_to_text(content)
        except Exception as e:
            return f"Error reading RTF file: {str(e)}"

