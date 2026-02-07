"""
ファクトリパターン - データソースの生成

config.pyの設定に基づいて、適切なデータソース（HILS/実機）を生成します。
"""

import logging
from interfaces import IDataSource
from simulator import HILSSimulatorSource
from hardware import RealHardwareSource
import config

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """
    データソースファクトリ
    
    Strategyパターンに基づき、設定ファイルのフラグで
    HILS/実機を切り替えます。
    """
    
    @staticmethod
    def create() -> IDataSource:
        """
        データソースを生成
        
        config.USE_REAL_HARDWARE の値に基づいて、
        適切な実装を返します。
        
        Returns:
            IDataSource: HILSシミュレータまたは実機ドライバ
        """
        if config.USE_REAL_HARDWARE:
            logger.info("実機ハードウェアモードで起動します")
            return RealHardwareSource()
        else:
            # HILSモード - サーバー or ローカル
            if getattr(config, 'USE_HILS_SERVER', False):
                from hils_client import HILSClientSource
                logger.info("HILSクライアントモード（サーバー接続）で起動します")
                return HILSClientSource()
            else:
                logger.info("HILSシミュレータモード（ローカル計算）で起動します")
                return HILSSimulatorSource()
    
    @staticmethod
    def get_mode_name() -> str:
        """
        現在のモード名を取得
        
        Returns:
            str: "Real Hardware" または "HILS Simulator" または "HILS Client"
        """
        if config.USE_REAL_HARDWARE:
            return "Real Hardware"
        elif getattr(config, 'USE_HILS_SERVER', False):
            return "HILS Client (Server)"
        else:
            return "HILS Simulator (Local)"
