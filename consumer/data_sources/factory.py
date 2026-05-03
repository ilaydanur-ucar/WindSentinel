import logging
import os
from typing import List, Dict, Any

from .base import BaseDataSource
from .csv_source import CSVDataSource
from .excel_source import ExcelDataSource

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """Factory to create data source instances based on DATA_SOURCE_TYPE ENV variable."""

    @staticmethod
    def get(file_path: str) -> BaseDataSource:
        """
        Get data source instance based on DATA_SOURCE_TYPE.

        Args:
            file_path: Path to the data file

        Returns:
            DataSource instance (CSV or Excel)
        """
        source_type = os.environ.get("DATA_SOURCE_TYPE", "csv").lower().strip()

        if source_type == "csv":
            return CSVDataSource(file_path)
        elif source_type == "excel":
            return ExcelDataSource(file_path)
        else:
            logger.warning(f"Unknown DATA_SOURCE_TYPE: {source_type}, defaulting to CSV")
            return CSVDataSource(file_path)

    @staticmethod
    def load(file_path: str) -> List[Dict[str, Any]]:
        """
        Convenience method: get source instance and load data in one call.

        Args:
            file_path: Path to the data file

        Returns:
            List of data rows as dictionaries
        """
        source = DataSourceFactory.get(file_path)
        return source.load()
