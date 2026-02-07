"""
gelNN - Ion Gel Touch Position Estimation System

イオンゲルのタッチ位置をインピーダンス測定から推定するシステムです。
"""

__version__ = '1.0.0'

# 主要モジュールのインポートを簡易化
from src.core import IDataSource, MeasurementResult, DataSourceFactory
from src.utils import config

__all__ = [
    'IDataSource',
    'MeasurementResult', 
    'DataSourceFactory',
    'config',
]
