# -*- coding: utf-8 -*-
from pathlib import Path
import xml.etree.ElementTree as ET
from .base_reader import BaseReader

class XmlReader(BaseReader):
    """
    Reader for XML files.
    """

    def read(self, path: Path) -> str:
        """
        Read and extract text content from an XML file.

        Parameters
        ----------
        path : Path
            Path to the XML file.

        Returns
        -------
        str
            Extracted text content from the XML file.
        """
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            def extract_text(el):
                """
                Recursively extract text from XML elements.

                Parameters
                ----------
                el : Element
                    XML element to extract text from.

                Returns
                -------
                str
                    Extracted text content.
                """
                text = el.text or ""
                for child in el:
                    text += extract_text(child)
                return text + (el.tail or "")

            return extract_text(root).strip()
        except Exception as e:
            return f"Error reading XML file: {str(e)}"

