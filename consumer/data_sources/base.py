from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseDataSource(ABC):
    """Abstract base class for data sources. Enables SOLID Open/Closed Principle."""

    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        """Load and return data as list of dictionaries."""
        pass
