# app/infrastructure/cleaners/base_cleaner.py
from abc import ABC, abstractmethod

class BaseCleaner(ABC):
    @abstractmethod
    def clean(self, text: str) -> str:
        """
        Cleans the input text.
        """
        pass

class DefaultTextCleaner(BaseCleaner):
    def clean(self, text: str) -> str:
        """
        Default cleaner that performs no cleaning.
        """
        return text