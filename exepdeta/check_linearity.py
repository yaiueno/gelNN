"""
時間-変位の線形性確認スクリプト
各試行で時間と変位の関係が線形かどうかを可視化する
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'MS Gothic'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

OUTPUT_DIR = Path('analysis_results')
OUTPUT_DIR.mkdir(exist_ok=True)


def load_csv(filepath):
    for enc in ['cp932', 'shift-jis', 'utf-8', 'utf-8-sig']:
        try:
            df = pd.read_csv(filepath, encoding=enc, header=0)
            if len(df.columns) >= 4:
                df = df.iloc[:, :4]
                df.columns = ['trial', 'time_sec', 'displacement_mm', 'force_N']
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df.dropna(inplace=True)
                df['trial'] = df['trial'].astype(int)
                return df
        except Exception:
            continue
    return None


def load_all_trials():
    file_map = {
        '2 mol/L': {'file.csv': '2mol_file1', 'file2.csv': '2mol_file2', 'file3.csv': '2mol_file3'},
        '3 mol/L': {'3_1.csv': '3mol_1', '3_2-6.csv': '3mol_2-6'},
        '4 mol/L': {'4_1-5.csv': '4mol_1-5'},
    }
    trials = []
    for conc, files in file_map.items():
        for fname, label in files.items():
            fpath = Path(fname)
            if not fpath.exists():
                continue
            df = load_csv(fpath)
            if df is None:
                continue
            for tid in sorted(df['trial'].unique()):
                tdf = df[df['trial'] == tid].copy().sort_values('time_sec').reset_index(drop=True)
                trials.append({
                    'concentration': conc,
                    'label': f"{label}_T{tid}",
                    'df': tdf,
                })
    return trials


def main():
    trials = load_all_trials()
    print(f"読み込み完了: {len(trials)} 試行\n")

    n = len(trials)
    cols = 4
    rows = (n + cols - 1) // cols

    # --- グラフ1: 各試行の時間-変位プロット + 回帰直線 ---
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 3.5))
    axes = np.array(axes).flatten()

    palette = {'2 mol/L': 'tab:blue', '3 mol/L': 'tab:green', '4 mol/L': 'tab:red'}
    summary_lines = []

    for i, t in enumerate(trials):
        ax = axes[i]
        tdf = t['df']
        time = tdf['time_sec'].values
        disp = tdf['displacement_mm'].values
        color = palette.get(t['concentration'], 'black')

        # プロット
        ax.plot(time, disp, '.', color=color, markersize=2, alpha=0.7)

        # 線形回帰
        coeffs = np.polyfit(time, disp, 1)
        poly = np.poly1d(coeffs)
        y_pred = poly(time)

        # R²
        ss_res = np.sum((disp - y_pred) ** 2)
        ss_tot = np.sum((disp - np.mean(disp)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # 残差の最大値
        residuals = disp - y_pred
        max_resid = np.max(np.abs(residuals))

        # 回帰直線
        t_fit = np.array([time.min(), time.max()])
        ax.plot(t_fit, poly(t_fit), '--', color='red', linewidth=1.5, alpha=0.8)

        ax.set_title(f"{t['label']}\nR²={r2:.6f}  速度={coeffs[0]:.4f} mm/s", fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.2)

        summary_lines.append({
            'trial': t['label'],
            'conc': t['concentration'],
            'slope_mm_per_s': coeffs[0],
            'intercept_mm': coeffs[1],
            'R2': r2,
            'max_residual_mm': max_resid,
            'n_points': len(time),
        })

        print(f"  {t['label']:20s}  R²={r2:.8f}  速度={coeffs[0]:.4f} mm/s  最大残差={max_resid:.4f} mm")

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle('時間-変位の線形性確認（各試行）\n赤破線=線形回帰', fontsize=13, fontweight='bold')
    fig.supxlabel('時間 [sec]', fontsize=11)
    fig.supylabel('変位 [mm]', fontsize=11)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / 'linearity_check_individual.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  保存: linearity_check_individual.png")

    # --- グラフ2: 残差プロット（線形からのずれ） ---
    fig2, axes2 = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 3.5))
    axes2 = np.array(axes2).flatten()

    for i, t in enumerate(trials):
        ax = axes2[i]
        tdf = t['df']
        time = tdf['time_sec'].values
        disp = tdf['displacement_mm'].values
        color = palette.get(t['concentration'], 'black')

        coeffs = np.polyfit(time, disp, 1)
        poly = np.poly1d(coeffs)
        residuals = disp - poly(time)

        ax.plot(time, residuals, '-', color=color, linewidth=0.6, alpha=0.8)
        ax.axhline(0, color='red', linewidth=0.5, linestyle='--')
        ax.set_title(f"{t['label']}\n残差 max={np.max(np.abs(residuals)):.4f} mm", fontsize=7)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.2)

    for j in range(i + 1, len(axes2)):
        axes2[j].set_visible(False)

    fig2.suptitle('線形回帰からの残差（時間-変位）\n残差≈0なら線形性が保たれている',
                  fontsize=13, fontweight='bold')
    fig2.supxlabel('時間 [sec]', fontsize=11)
    fig2.supylabel('残差 [mm]', fontsize=11)
    plt.tight_layout()
    fig2.savefig(OUTPUT_DIR / 'linearity_check_residuals.png', dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"  保存: linearity_check_residuals.png")

    # --- グラフ3: R²のサマリーバー ---
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    sdf = pd.DataFrame(summary_lines)
    colors = [palette.get(c, 'gray') for c in sdf['conc']]
    bars = ax3.barh(range(len(sdf)), sdf['R2'], color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)

    ax3.set_yticks(range(len(sdf)))
    ax3.set_yticklabels(sdf['trial'], fontsize=8)
    ax3.set_xlabel('決定係数 R²', fontsize=12)
    ax3.set_title('各試行の時間-変位 線形性（R²）', fontsize=14, fontweight='bold')
    ax3.set_xlim(min(sdf['R2'].min() - 0.001, 0.999), 1.0001)
    ax3.axvline(1.0, color='red', linewidth=0.5, linestyle='--', label='完全線形 (R²=1)')
    ax3.grid(True, alpha=0.3, axis='x')
    ax3.legend(fontsize=9)

    # R²の値をバーの横に表示
    for idx, (r2, trial) in enumerate(zip(sdf['R2'], sdf['trial'])):
        ax3.text(r2 + 0.00005, idx, f'{r2:.6f}', va='center', fontsize=7)

    plt.tight_layout()
    fig3.savefig(OUTPUT_DIR / 'linearity_R2_summary.png', dpi=300, bbox_inches='tight')
    plt.close(fig3)
    print(f"  保存: linearity_R2_summary.png")

    print("\n完了！")


if __name__ == '__main__':
    main()
