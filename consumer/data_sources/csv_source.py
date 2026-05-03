import csv
import logging
from pathlib import Path
from typing import List, Dict, Any

from .base import BaseDataSource

logger = logging.getLogger(__name__)


class CSVDataSource(BaseDataSource):
    """Load data from CSV file."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> List[Dict[str, Any]]:
        """Load CSV file and return rows as list of dicts."""
        if not self.file_path.exists():
            logger.error(f"CSV file not found: {self.file_path}")
            return []

        rows = []
        try:
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = [dict(row) for row in reader]
            logger.info(f"Loaded {len(rows)} rows from CSV: {self.file_path.name}")
        except Exception as e:
            logger.error(f"Error loading CSV: {e}", exc_info=True)

        return rows
