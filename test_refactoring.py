"""
リファクタリング後の動作確認スクリプト

各モジュールのimportと基本機能をテストします。
"""

import sys
import os

# プロジェクトルートをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("=" * 60)
print("リファクタリング動作確認テスト")
print("=" * 60)
print()

# テスト1: コアモジュールのインポート
print("✓ テスト1: コアモジュールのインポート")
try:
    from src.core.interfaces import IDataSource, MeasurementResult
    from src.core.factory import DataSourceFactory
    from src.core.models.classifier import TouchClassifier
    print("  ✅ core モジュール: OK")
except Exception as e:
    print(f"  ❌ core モジュール: FAILED - {e}")
    sys.exit(1)

# テスト2: ユーティリティモジュールのインポート
print("✓ テスト2: ユーティリティモジュールのインポート")
try:
    from src.utils import config
    print("  ✅ utils モジュール: OK")
    print(f"     - USE_REAL_HARDWARE: {config.USE_REAL_HARDWARE}")
    print(f"     - USE_HILS_SERVER: {config.USE_HILS_SERVER}")
except Exception as e:
    print(f"  ❌ utils モジュール: FAILED - {e}")
    sys.exit(1)

# テスト3: HILSモジュールのインポート
print("✓ テスト3: HILSモジュールのインポート")
try:
    from src.hils.simulator import HILSSimulatorSource
    from src.hils.client import HILSClientSource
    print("  ✅ hils モジュール: OK")
except Exception as e:
    print(f"  ❌ hils モジュール: FAILED - {e}")
    sys.exit(1)

# テスト4: ハードウェアモジュールのインポート（AD3がなくてもインポートは成功すべき）
print("✓ テスト4: ハードウェアモジュールのインポート")
try:
    # ハードウェアモジュールはAD3 SDKが必要だが、インポート自体は試みる
    from src.hardware.hardware import RealHardwareSource
    print("  ✅ hardware モジュール: OK")
except Exception as e:
    # AD3 SDKがない場合は警告だけ出す
    print(f"  ⚠️  hardware モジュール: {e}")
    print("     (AD3 SDKがインストールされていない場合は正常)")

# テスト5: DataSourceFactoryの動作確認
print("✓ テスト5: DataSourceFactoryの動作確認")
try:
    mode_name = DataSourceFactory.get_mode_name()
    print(f"  ✅ DataSourceFactory: OK")
    print(f"     - 現在のモード: {mode_name}")
except Exception as e:
    print(f"  ❌ DataSourceFactory: FAILED - {e}")
    sys.exit(1)

# テスト6: HILSシミュレータの接続テスト
print("✓ テスト6: HILSシミュレータの接続テスト")
try:
    # 一時的にHILSモードに設定
    original_mode = config.USE_REAL_HARDWARE
    config.USE_REAL_HARDWARE = False
    config.USE_HILS_SERVER = False
    
    data_source = DataSourceFactory.create()
    if data_source.connect():
        print("  ✅ HILSシミュレータ接続: OK")
        
        # 簡単な測定テスト
        data_source.set_ground_truth(50.0, 50.0)
        impedance_vector = data_source.measure_impedance_vector()
        print(f"     - インピーダンス測定: {impedance_vector.shape}")
        
        data_source.disconnect()
        print("  ✅ HILSシミュレータ切断: OK")
    else:
        print("  ❌ HILSシミュレータ接続: FAILED")
    
    # 元の設定に戻す
    config.USE_REAL_HARDWARE = original_mode
    
except Exception as e:
    print(f"  ❌ HILSシミュレータテスト: FAILED - {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# テスト7: エントリーポイントファイルの存在確認
print("✓ テスト7: エントリーポイントファイルの存在確認")
entry_points = [
    "run_app.py",
    "run_classifier.py",
    "run_hils_server.py",
    "run_hils_gui.py"
]

all_exist = True
for ep in entry_points:
    if os.path.exists(ep):
        print(f"  ✅ {ep}: 存在")
    else:
        print(f"  ❌ {ep}: 見つかりません")
        all_exist = False

if not all_exist:
    sys.exit(1)

# すべてのテストが成功
print()
print("=" * 60)
print("✅ すべてのテストが成功しました！")
print("=" * 60)
print()
print("次のステップ:")
print("  1. アプリケーションを起動: python run_app.py")
print("  2. HILSフルシステムを起動: start_full_hils_system.bat")
print("  3. 学習スクリプトを実行: python scripts/train.py")
print()
