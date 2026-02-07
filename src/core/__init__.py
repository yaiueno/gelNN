"""
コアモジュール - システムの中核となるインターフェースとファクトリ

このパッケージには、HILS/実機の抽象化レイヤーとファクトリパターンが含まれます。
"""

from .interfaces import IDataSource, MeasurementResult
from .factory import DataSourceFactory

__all__ = [
    'IDataSource',
    'MeasurementResult',
    'DataSourceFactory',
]
