import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import seaborn as sns
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 日本語フォント設定（必要に応じて）
plt.rcParams['font.family'] = 'MS Gothic'  # Windows用日本語フォント
plt.rcParams['axes.unicode_minus'] = False

def load_csv_file(filepath):
    """CSVファイルを読み込む（データ改変なし）"""
    # 様々なエンコーディングを試す
    encodings = ['cp932', 'shift-jis', 'utf-8', 'utf-8-sig', 'euc-jp']
    
    for encoding in encodings:
        try:
            # まずヘッダーありで試す
            df = pd.read_csv(filepath, encoding=encoding, header=0)
            # 列数が4列か確認
            if len(df.columns) >= 4:
                # 列名を標準化
                if len(df.columns) == 4:
                    df.columns = ['trial', 'time_sec', 'displacement_mm', 'force_N']
                return df
        except Exception as e:
            continue
    
    # どのエンコーディングも失敗した場合、ヘッダーなしで読み込み
    for encoding in encodings:
        try:
            df = pd.read_csv(filepath, encoding=encoding, header=None)
            # 列数が4列か確認
            if len(df.columns) >= 4:
                # 最初の4列を使用
                df = df.iloc[:, :4]
                df.columns = ['trial', 'time_sec', 'displacement_mm', 'force_N']
                return df
        except Exception as e:
            continue
    
    # 最終手段：バイナリで読み込み
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        # 適当なエンコーディングでデコード
        try:
            content_str = content.decode('cp932')
        except:
            content_str = content.decode('utf-8', errors='ignore')
        
        # 手動でパース
        lines = content_str.strip().split('\n')
        data = []
        for line in lines:
            if line.strip():
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    data.append([float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])])
        
        df = pd.DataFrame(data, columns=['trial', 'time_sec', 'displacement_mm', 'force_N'])
        return df
    except Exception as e:
        print(f"エラー: {filepath} を読み込めません: {e}")
        return None

def extract_peak_force(df):
    """データフレームからピーク力（最大絶対値）を抽出"""
    # 力の絶対値の最大値を求める
    peak_force = df['force_N'].abs().max()
    return peak_force

def analyze_concentration_files(file_dict, concentration_name):
    """濃度ごとのファイルを分析"""
    all_data = []
    peak_forces = []
    
    for filename, label in file_dict.items():
        if not os.path.exists(filename):
            print(f"警告: ファイル {filename} が見つかりません")
            continue
            
        df = load_csv_file(filename)
        
        if df is None:
            print(f"警告: ファイル {filename} を読み込めませんでした")
            continue
        
        # 試行番号ごとに処理（複数試行がある場合）
        trials = df['trial'].unique()
        
        for trial in trials:
            trial_df = df[df['trial'] == trial].copy()
            trial_df['source'] = f"{label}_trial{trial}"
            all_data.append(trial_df)
            
            # ピーク力を計算
            peak_force = extract_peak_force(trial_df)
            peak_forces.append({
                'source': label,
                'trial': trial,
                'peak_force': peak_force,
                'concentration': concentration_name
            })
    
    if not all_data:
        return None, None
    
    all_data_df = pd.concat(all_data, ignore_index=True)
    peak_forces_df = pd.DataFrame(peak_forces)
    
    return all_data_df, peak_forces_df

def create_combined_plot(force_displacement_data, peak_forces_data, concentration, output_path):
    """外形グラフと箱ひげ図を組み合わせたグラフを作成（濃度ごとにまとめた表示）"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 1. 外形グラフ（力-変位曲線）- 濃度ごとにまとめて表示
    ax1 = axes[0]
    
    # より明確な色の設定
    concentration_colors = {
        '2 mol/L': ('darkblue', 'lightblue'),
        '3 mol/L': ('darkgreen', 'lightgreen'), 
        '4 mol/L': ('darkred', 'lightcoral')
    }
    line_color, box_color = concentration_colors.get(concentration, ('black', 'lightgray'))
    
    # シンプルな力-変位曲線：全データをまとめて表示
    # 変位の順に並べ替え
    sorted_data = force_displacement_data.sort_values('displacement_mm').reset_index(drop=True)
    
    # シンプルな折れ線グラフを描画（線を細く）
    ax1.plot(sorted_data['displacement_mm'], sorted_data['force_N'], 
            color=line_color, alpha=0.8, linewidth=1.0, label=f'{concentration} データ')
    
    # ピーク位置をマーク
    peak_idx = sorted_data['force_N'].abs().idxmax()
    peak_displacement = sorted_data.loc[peak_idx, 'displacement_mm']
    peak_force = sorted_data.loc[peak_idx, 'force_N']
    
    ax1.plot(peak_displacement, peak_force, 'o', color='red', markersize=8, 
            label=f'ピーク: {peak_force:.3f} N')
    
    # 線形近似（一次回帰）を追加
    if len(sorted_data) > 1:
        # 線形回帰を計算
        x = sorted_data['displacement_mm'].values
        y = sorted_data['force_N'].values
        
        # 回帰直線を計算
        coeffs = np.polyfit(x, y, 1)
        poly = np.poly1d(coeffs)
        
        # 決定係数（R²）を計算
        y_pred = poly(x)
        y_mean = np.mean(y)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        # 近似直線を描画（破線）
        x_fit = np.linspace(x.min(), x.max(), 100)
        y_fit = poly(x_fit)
        
        ax1.plot(x_fit, y_fit, '--', color='darkgray', linewidth=1.5, 
                alpha=0.7, label=f'線形近似 (R²={r_squared:.3f})')
        
        # 回帰式を表示
        slope = coeffs[0]
        intercept = coeffs[1]
        eq_text = f'y = {slope:.4f}x + {intercept:.4f}'
        ax1.text(0.05, 0.95, eq_text, transform=ax1.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax1.set_xlabel('変位 [mm]', fontsize=12)
    ax1.set_ylabel('力 [N]', fontsize=12)
    ax1.set_title(f'{concentration} - 力-変位曲線', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8, loc='best')
    
    # 2. 箱ひげ図（ピーク力の分布）- 濃度ごとにまとめて表示
    ax2 = axes[1]
    
    # 濃度内の全ピーク力を1つのボックスで表示
    all_peaks = peak_forces_data['peak_force']
    
    # 箱ひげ図をプロット（1つのボックス）
    bp = ax2.boxplot([all_peaks], labels=[concentration], patch_artist=True, widths=0.6, showfliers=False)
    
    # 箱の色を設定
    for patch in bp['boxes']:
        patch.set_facecolor(box_color)
        patch.set_alpha(0.7)
    
    # 平均値をプロット（横方向の広がりなし）
    mean_val = np.mean(all_peaks)
    ax2.plot(1, mean_val, 'D', color='red', markersize=8, markeredgecolor='black', label=f'平均: {mean_val:.3f} N')
    
    # 各データポイントを散布図で表示（横方向に少し広げる）
    jitter = 0.05  # 横方向の広がり
    for i, peak in enumerate(all_peaks):
        x_jitter = 1 + (np.random.rand() - 0.5) * jitter
        ax2.plot(x_jitter, peak, 'o', color='darkblue', markersize=6, alpha=0.6, label='データ点' if i == 0 else "")
    
    ax2.set_xlabel('モノマー濃度', fontsize=12)
    ax2.set_ylabel('ピーク力 [N]', fontsize=12)
    ax2.set_title(f'{concentration} - ピーク力の分布（箱ひげ図+散布図）', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # 統計情報をテキストで返す（グラフには表示しない）
    stats_text = f"{concentration} 統計情報:\n"
    stats_text += f"  試行数: {len(all_peaks)}\n"
    stats_text += f"  平均: {np.mean(all_peaks):.4f} N\n"
    stats_text += f"  標準偏差: {np.std(all_peaks):.4f} N\n"
    stats_text += f"  分散: {np.var(all_peaks):.6f} N²\n"
    stats_text += f"  最大値: {np.max(all_peaks):.4f} N\n"
    stats_text += f"  最小値: {np.min(all_peaks):.4f} N\n"
    stats_text += f"  範囲: {np.max(all_peaks) - np.min(all_peaks):.4f} N\n"
    stats_text += f"  変動係数: {(np.std(all_peaks)/np.mean(all_peaks)*100):.1f} %\n"
    
    return stats_text

def main():
    # ファイルの分類
    concentration_files = {
        '2 mol/L': {
            'file.csv': 'file1',
            'file2.csv': 'file2', 
            'file3.csv': 'file3'
        },
        '3 mol/L': {
            '3_1.csv': '3_1',
            '3_2-6.csv': '3_2-6'  # 複数試行を含む
        },
        '4 mol/L': {
            '4_1-5.csv': '4_1-5'  # 複数試行を含む
        }
    }
    
    # 結果を保存するディレクトリを作成
    output_dir = Path('analysis_results')
    output_dir.mkdir(exist_ok=True)
    
    all_stats = {}
    
    # 各濃度ごとに分析
    for concentration, files in concentration_files.items():
        print(f"\n分析中: {concentration}")
        print("=" * 50)
        
        # ファイルを分析
        force_displacement_data, peak_forces_data = analyze_concentration_files(files, concentration)
        
        if force_displacement_data is None or peak_forces_data is None:
            print(f"警告: {concentration} のデータが見つかりません")
            continue
        
        # 出力ファイル名
        output_filename = f"{concentration.replace(' ', '_').replace('/', '_')}_analysis.png"
        output_path = output_dir / output_filename
        
        # グラフを作成
        stats_text = create_combined_plot(
            force_displacement_data, 
            peak_forces_data, 
            concentration, 
            output_path
        )
        
        all_stats[concentration] = stats_text
        
        # 基本統計情報を表示
        print(f"データポイント数: {len(force_displacement_data)}")
        print(f"試行数: {len(peak_forces_data)}")
        print(f"ピーク力の平均: {peak_forces_data['peak_force'].mean():.4f} N")
        print(f"ピーク力の標準偏差: {peak_forces_data['peak_force'].std():.4f} N")
        print(f"グラフを保存しました: {output_path}")
    
    # 統計情報をファイルに保存
    stats_file = output_dir / 'statistics_summary.txt'
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("フォースメーターデータ分析結果\n")
        f.write("=" * 50 + "\n\n")
        
        for concentration, stats in all_stats.items():
            f.write(f"{concentration}\n")
            f.write("-" * 30 + "\n")
            f.write(stats)
            f.write("\n")
    
    print(f"\n分析完了！")
    print(f"統計サマリー: {stats_file}")
    
    # 全濃度のピーク力を比較するグラフも作成
    print("\n全濃度の比較グラフを作成中...")
    create_comparison_plot(concentration_files, output_dir)

def create_comparison_plot(concentration_files, output_dir):
    """全濃度のピーク力を比較するグラフ"""
    all_peak_data = []
    
    for concentration, files in concentration_files.items():
        force_displacement_data, peak_forces_data = analyze_concentration_files(files, concentration)
        
        if peak_forces_data is not None:
            peak_forces_data['concentration'] = concentration
            all_peak_data.append(peak_forces_data)
    
    if not all_peak_data:
        return
    
    all_peaks_df = pd.concat(all_peak_data, ignore_index=True)
    
    # 濃度ごとの比較グラフ
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 1. 濃度ごとの箱ひげ図
    ax1 = axes[0]
    
    concentrations = all_peaks_df['concentration'].unique()
    box_data = []
    
    for conc in concentrations:
        conc_data = all_peaks_df[all_peaks_df['concentration'] == conc]['peak_force']
        box_data.append(conc_data)
    
    bp1 = ax1.boxplot(box_data, labels=concentrations, patch_artist=True)
    
    # 箱の色を設定
    colors = ['lightblue', 'lightgreen', 'lightcoral']
    for i, patch in enumerate(bp1['boxes']):
        if i < len(colors):
            patch.set_facecolor(colors[i])
    
    ax1.set_xlabel('モノマー濃度', fontsize=12)
    ax1.set_ylabel('ピーク力 [N]', fontsize=12)
    ax1.set_title('濃度別ピーク力の比較', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 2. 濃度ごとの平均と標準偏差
    ax2 = axes[1]
    
    means = []
    stds = []
    
    for conc in concentrations:
        conc_data = all_peaks_df[all_peaks_df['concentration'] == conc]['peak_force']
        means.append(conc_data.mean())
        stds.append(conc_data.std())
    
    x_pos = np.arange(len(concentrations))
    bars = ax2.bar(x_pos, means, yerr=stds, capsize=10, 
                  color=colors[:len(concentrations)], alpha=0.7, edgecolor='black')
    
    ax2.set_xlabel('モノマー濃度', fontsize=12)
    ax2.set_ylabel('平均ピーク力 [N]', fontsize=12)
    ax2.set_title('濃度別平均ピーク力と標準偏差', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(concentrations)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # バー上に数値を表示
    for i, (mean, std) in enumerate(zip(means, stds)):
        ax2.text(i, mean + std + 0.01, f'{mean:.3f} ± {std:.3f}', 
                ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    comparison_path = output_dir / 'concentration_comparison.png'
    plt.savefig(comparison_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"比較グラフを保存しました: {comparison_path}")

if __name__ == "__main__":
    main()