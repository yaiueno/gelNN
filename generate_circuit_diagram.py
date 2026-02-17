"""
回路図生成スクリプト

イオンゲル押圧位置推定システムの回路図をPNG画像として出力します。
構成: Analog Discovery 3 + Arduino + CD4051 MUX ×2 + イオンゲル(4端子)

Usage:
    python generate_circuit_diagram.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc
import matplotlib.font_manager as fm
import numpy as np
import platform

# 日本語フォント設定
_jp_font = None
if platform.system() == "Windows":
    for fname in ["Yu Gothic", "Meiryo", "MS Gothic"]:
        if any(fname == f.name for f in fm.fontManager.ttflist):
            _jp_font = fname
            break
elif platform.system() == "Darwin":
    _jp_font = "Hiragino Sans"
else:
    _jp_font = "IPAGothic"

if _jp_font:
    plt.rcParams["font.family"] = [_jp_font, "sans-serif"]
    plt.rcParams["font.sans-serif"] = [_jp_font] + plt.rcParams["font.sans-serif"]

plt.rcParams["axes.unicode_minus"] = False


def draw_rounded_box(ax, xy, width, height, label, color="#E8F0FE",
                     edgecolor="#333333", fontsize=10, bold=False,
                     sublabel=None, lw=2):
    """角丸ボックスを描画"""
    box = FancyBboxPatch(
        xy, width, height,
        boxstyle="round,pad=0.05",
        facecolor=color,
        edgecolor=edgecolor,
        linewidth=lw,
    )
    ax.add_patch(box)
    cx = xy[0] + width / 2
    cy = xy[1] + height / 2
    weight = "bold" if bold else "normal"
    if sublabel:
        ax.text(cx, cy + 0.15, label, ha="center", va="center",
                fontsize=fontsize, fontweight=weight)
        ax.text(cx, cy - 0.25, sublabel, ha="center", va="center",
                fontsize=fontsize - 2, color="#555555")
    else:
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fontsize, fontweight=weight)


def draw_pin_label(ax, x, y, label, ha="left", fontsize=7, color="#333"):
    """ピンラベルを描画"""
    ax.text(x, y, label, ha=ha, va="center", fontsize=fontsize,
            color=color)


def draw_wire(ax, x1, y1, x2, y2, color="#333333", lw=1.2, ls="-"):
    """配線を描画"""
    ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, linestyle=ls,
            solid_capstyle="round")


def draw_arrow_wire(ax, x1, y1, x2, y2, color="#333333", lw=1.2):
    """矢印付き配線"""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw))


def draw_resistor(ax, x, y, width=0.6, label="10kΩ"):
    """抵抗のシンボルを描画 (水平)"""
    # ジグザグ
    n_teeth = 6
    h = 0.12
    xs = np.linspace(x, x + width, n_teeth * 2 + 1)
    ys_vals = [y]
    for i in range(1, len(xs) - 1):
        ys_vals.append(y + h * (1 if i % 2 == 1 else -1))
    ys_vals.append(y)
    ax.plot(xs, ys_vals, color="#333333", linewidth=1.5, solid_capstyle="round")
    ax.text(x + width / 2, y + 0.22, label, ha="center", va="bottom",
            fontsize=7, color="#333333")


def draw_gel(ax, cx, cy, size=1.8):
    """イオンゲル (4端子) を描画"""
    half = size / 2
    # ゲル本体
    gel = FancyBboxPatch(
        (cx - half, cy - half), size, size,
        boxstyle="round,pad=0.05",
        facecolor="#C8E6C9", edgecolor="#2E7D32", linewidth=2.5,
    )
    ax.add_patch(gel)
    ax.text(cx, cy + 0.1, "Ion Gel", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#1B5E20")
    ax.text(cx, cy - 0.25, "(タッチセンサ)", ha="center", va="center",
            fontsize=7, color="#388E3C")

    # 端子位置: A=左下, B=右下, C=右上, D=左上
    terminals = {
        "A": (cx - half, cy - half),
        "B": (cx + half, cy - half),
        "C": (cx + half, cy + half),
        "D": (cx - half, cy + half),
    }
    for name, (tx, ty) in terminals.items():
        circle = plt.Circle((tx, ty), 0.1, color="#2E7D32", zorder=5)
        ax.add_patch(circle)
        # ラベル位置
        ox = -0.2 if "A" in name or "D" in name else 0.2
        oy = -0.2 if "A" in name or "B" in name else 0.2
        ax.text(tx + ox, ty + oy, name, ha="center", va="center",
                fontsize=9, fontweight="bold", color="#1B5E20")

    return terminals


def generate_circuit_diagram(output_path="circuit_diagram.png"):
    """メインの回路図生成関数"""

    fig, ax = plt.subplots(1, 1, figsize=(18, 11))
    ax.set_xlim(-1, 17)
    ax.set_ylim(-1, 10.5)
    ax.set_aspect("equal")
    ax.axis("off")

    # タイトル
    ax.text(8, 10.2, "イオンゲル押圧位置推定システム 回路図",
            ha="center", va="center", fontsize=16, fontweight="bold")
    ax.text(8, 9.8, "Analog Discovery 3 + Arduino Uno + CD4051 MUX ×2 + Ion Gel (4端子)",
            ha="center", va="center", fontsize=9, color="#666666")

    # ================================================================
    # PC
    # ================================================================
    draw_rounded_box(ax, (-0.5, 3.5), 2.0, 2.5, "PC",
                     color="#FFF9C4", edgecolor="#F9A825",
                     fontsize=13, bold=True,
                     sublabel="Python App\n(WaveForms SDK)")

    # ================================================================
    # Analog Discovery 3
    # ================================================================
    ad3_x, ad3_y = 3.0, 2.5
    ad3_w, ad3_h = 3.5, 5.0
    draw_rounded_box(ax, (ad3_x, ad3_y), ad3_w, ad3_h,
                     "", color="#E3F2FD", edgecolor="#1565C0",
                     fontsize=12, bold=True, lw=2.5)
    ax.text(ad3_x + ad3_w / 2, ad3_y + ad3_h - 0.35,
            "Analog Discovery 3", ha="center", va="center",
            fontsize=11, fontweight="bold", color="#0D47A1")
    ax.text(ad3_x + ad3_w / 2, ad3_y + ad3_h - 0.7,
            "(Impedance Analyzer Mode)", ha="center", va="center",
            fontsize=7, color="#1976D2")

    # AD3内部ブロック
    # W1 (Waveform Generator)
    w1_y = 6.3
    draw_rounded_box(ax, (ad3_x + 0.2, w1_y), 1.4, 0.6, "W1",
                     color="#BBDEFB", edgecolor="#1976D2",
                     fontsize=8, sublabel="WaveGen")
    # → 出力ピン
    draw_pin_label(ax, ad3_x + ad3_w + 0.1, w1_y + 0.3, "W1+", ha="left", fontsize=8, color="#1565C0")

    # 1+/1- (Scope)
    scope_y = 5.2
    draw_rounded_box(ax, (ad3_x + 0.2, scope_y), 1.4, 0.6, "Scope",
                     color="#BBDEFB", edgecolor="#1976D2",
                     fontsize=8, sublabel="CH1")
    draw_pin_label(ax, ad3_x + ad3_w + 0.1, scope_y + 0.45, "1+", ha="left", fontsize=8, color="#1565C0")
    draw_pin_label(ax, ad3_x + ad3_w + 0.1, scope_y + 0.05, "1−", ha="left", fontsize=8, color="#1565C0")

    # Ref R (内部リファレンス抵抗)
    ref_y = 4.0
    draw_rounded_box(ax, (ad3_x + 0.2, ref_y), 1.4, 0.6, "Ref R",
                     color="#BBDEFB", edgecolor="#1976D2",
                     fontsize=8, sublabel="10kΩ")

    # GND
    gnd_y = 3.1
    draw_pin_label(ax, ad3_x + ad3_w + 0.1, gnd_y, "GND", ha="left", fontsize=8, color="#1565C0")

    # AD3 内部配線
    # W1 → 出力端子
    draw_wire(ax, ad3_x + 1.6 + 0.2, w1_y + 0.3, ad3_x + ad3_w, w1_y + 0.3, color="#1976D2", lw=1.5)
    # Scope 1+
    draw_wire(ax, ad3_x + 1.6 + 0.2, scope_y + 0.45, ad3_x + ad3_w, scope_y + 0.45, color="#1976D2", lw=1.5)
    # Scope 1-
    draw_wire(ax, ad3_x + 1.6 + 0.2, scope_y + 0.05, ad3_x + ad3_w, scope_y + 0.05, color="#1976D2", lw=1.5)
    # Ref R → GND方向
    draw_wire(ax, ad3_x + 1.6 + 0.2, ref_y + 0.3, ad3_x + ad3_w, ref_y + 0.3, color="#1976D2", lw=1.0)
    # GND line
    draw_wire(ax, ad3_x + 0.5, gnd_y, ad3_x + ad3_w, gnd_y, color="#1976D2", lw=1.0)

    # AD3 出力端子ドット
    for py in [w1_y + 0.3, scope_y + 0.45, scope_y + 0.05, ref_y + 0.3, gnd_y]:
        ax.plot(ad3_x + ad3_w, py, "o", color="#1565C0", markersize=4, zorder=5)

    # PC → AD3 (USB)
    draw_wire(ax, 1.5, 4.75, 3.0, 4.75, color="#F9A825", lw=2.5)
    ax.text(2.25, 5.0, "USB", ha="center", va="bottom", fontsize=8,
            color="#F9A825", fontweight="bold")

    # ================================================================
    # Arduino Uno
    # ================================================================
    ard_x, ard_y = 3.2, 0.0
    ard_w, ard_h = 3.0, 2.0
    draw_rounded_box(ax, (ard_x, ard_y), ard_w, ard_h,
                     "Arduino Uno", color="#FFF3E0", edgecolor="#E65100",
                     fontsize=11, bold=True,
                     sublabel="MUX Controller\n9600 baud")

    # Arduino ピンラベル (右側)
    ard_pins_y_start = 1.6
    pin_labels = ["D2", "D3", "D4", "D5", "D6", "D7"]
    pin_ys = []
    for i, pl in enumerate(pin_labels):
        py = ard_pins_y_start - i * 0.25
        pin_ys.append(py)
        draw_pin_label(ax, ard_x + ard_w + 0.1, py, pl, fontsize=7, color="#BF360C")
        ax.plot(ard_x + ard_w, py, "o", color="#E65100", markersize=3, zorder=5)

    # PC → Arduino (USB/Serial)
    draw_wire(ax, 1.5, 4.25, 2.0, 4.25, color="#F9A825", lw=2.0)
    draw_wire(ax, 2.0, 4.25, 2.0, 1.0, color="#F9A825", lw=2.0)
    draw_wire(ax, 2.0, 1.0, 3.2, 1.0, color="#F9A825", lw=2.0)
    ax.text(1.3, 2.5, "USB\nSerial", ha="center", va="center", fontsize=7,
            color="#F9A825", fontweight="bold", rotation=90)

    # ================================================================
    # MUX1 (Source側) - CD4051
    # ================================================================
    mux1_x, mux1_y = 8.5, 5.0
    mux1_w, mux1_h = 2.2, 3.5
    draw_rounded_box(ax, (mux1_x, mux1_y), mux1_w, mux1_h,
                     "", color="#F3E5F5", edgecolor="#6A1B9A",
                     fontsize=10, bold=True, lw=2)
    ax.text(mux1_x + mux1_w / 2, mux1_y + mux1_h - 0.3,
            "MUX1 (Source)", ha="center", va="center",
            fontsize=10, fontweight="bold", color="#4A148C")
    ax.text(mux1_x + mux1_w / 2, mux1_y + mux1_h - 0.6,
            "CD4051", ha="center", va="center",
            fontsize=8, color="#7B1FA2")

    # MUX1 制御ピン (左側: S0, S1, S2)
    mux1_ctrl_labels = ["S0", "S1", "S2"]
    mux1_ctrl_ys = []
    for i, cl in enumerate(mux1_ctrl_labels):
        cy = mux1_y + 0.5 + i * 0.4
        mux1_ctrl_ys.append(cy)
        draw_pin_label(ax, mux1_x - 0.35, cy, cl, ha="right", fontsize=7, color="#6A1B9A")
        ax.plot(mux1_x, cy, "o", color="#6A1B9A", markersize=3, zorder=5)

    # MUX1 COM (左側, 上方)
    mux1_com_y = mux1_y + 2.5
    draw_pin_label(ax, mux1_x - 0.35, mux1_com_y, "COM", ha="right", fontsize=7, color="#6A1B9A")
    ax.plot(mux1_x, mux1_com_y, "o", color="#6A1B9A", markersize=4, zorder=5)

    # MUX1 チャンネル出力 (右側: Y0-Y3 のみ表示)
    mux1_ch_labels = ["Y0", "Y1", "Y2", "Y3"]
    mux1_ch_ys = []
    for i, yl in enumerate(mux1_ch_labels):
        cy = mux1_y + mux1_h - 1.0 - i * 0.5
        mux1_ch_ys.append(cy)
        draw_pin_label(ax, mux1_x + mux1_w + 0.1, cy, yl, fontsize=7, color="#6A1B9A")
        ax.plot(mux1_x + mux1_w, cy, "o", color="#6A1B9A", markersize=3, zorder=5)

    # ================================================================
    # MUX2 (Sink側) - CD4051
    # ================================================================
    mux2_x, mux2_y = 8.5, 0.5
    mux2_w, mux2_h = 2.2, 3.5
    draw_rounded_box(ax, (mux2_x, mux2_y), mux2_w, mux2_h,
                     "", color="#E8EAF6", edgecolor="#283593",
                     fontsize=10, bold=True, lw=2)
    ax.text(mux2_x + mux2_w / 2, mux2_y + mux2_h - 0.3,
            "MUX2 (Sink)", ha="center", va="center",
            fontsize=10, fontweight="bold", color="#1A237E")
    ax.text(mux2_x + mux2_w / 2, mux2_y + mux2_h - 0.6,
            "CD4051", ha="center", va="center",
            fontsize=8, color="#283593")

    # MUX2 制御ピン (左側: S0, S1, S2)
    mux2_ctrl_labels = ["S0", "S1", "S2"]
    mux2_ctrl_ys = []
    for i, cl in enumerate(mux2_ctrl_labels):
        cy = mux2_y + 0.5 + i * 0.4
        mux2_ctrl_ys.append(cy)
        draw_pin_label(ax, mux2_x - 0.35, cy, cl, ha="right", fontsize=7, color="#283593")
        ax.plot(mux2_x, cy, "o", color="#283593", markersize=3, zorder=5)

    # MUX2 COM (左側, 上方)
    mux2_com_y = mux2_y + 2.5
    draw_pin_label(ax, mux2_x - 0.35, mux2_com_y, "COM", ha="right", fontsize=7, color="#283593")
    ax.plot(mux2_x, mux2_com_y, "o", color="#283593", markersize=4, zorder=5)

    # MUX2 チャンネル出力 (右側: Y0-Y3)
    mux2_ch_labels = ["Y0", "Y1", "Y2", "Y3"]
    mux2_ch_ys = []
    for i, yl in enumerate(mux2_ch_labels):
        cy = mux2_y + mux2_h - 1.0 - i * 0.5
        mux2_ch_ys.append(cy)
        draw_pin_label(ax, mux2_x + mux2_w + 0.1, cy, yl, fontsize=7, color="#283593")
        ax.plot(mux2_x + mux2_w, cy, "o", color="#283593", markersize=3, zorder=5)

    # ================================================================
    # イオンゲル
    # ================================================================
    gel_cx, gel_cy = 14.5, 4.5
    gel_size = 2.2
    terminals = draw_gel(ax, gel_cx, gel_cy, gel_size)

    # ================================================================
    # 配線: AD3 → MUX1 COM (W1+ と 1+ を結合)
    # ================================================================
    # W1+ → MUX1 COM
    ad3_out_x = ad3_x + ad3_w
    mid_x1 = 7.5

    # W1+ の配線 (上)
    draw_wire(ax, ad3_out_x, w1_y + 0.3, mid_x1, w1_y + 0.3, color="#D32F2F", lw=1.8)
    draw_wire(ax, mid_x1, w1_y + 0.3, mid_x1, mux1_com_y, color="#D32F2F", lw=1.8)
    draw_wire(ax, mid_x1, mux1_com_y, mux1_x, mux1_com_y, color="#D32F2F", lw=1.8)
    ax.text(mid_x1 + 0.15, (w1_y + 0.3 + mux1_com_y) / 2, "W1+",
            ha="left", va="center", fontsize=7, color="#D32F2F", rotation=90)

    # 1+ も同じノードに接続 (DUT高電位側)
    draw_wire(ax, ad3_out_x, scope_y + 0.45, mid_x1 - 0.3, scope_y + 0.45, color="#1976D2", lw=1.2)
    draw_wire(ax, mid_x1 - 0.3, scope_y + 0.45, mid_x1 - 0.3, mux1_com_y, color="#1976D2", lw=1.2)
    # 接合ドット
    ax.plot(mid_x1 - 0.3, mux1_com_y, "o", color="#333", markersize=5, zorder=6)

    draw_wire(ax, mid_x1 - 0.3, mux1_com_y, mid_x1, mux1_com_y, color="#333", lw=1.5)

    # ================================================================
    # 配線: AD3 1- / RefR → MUX2 COM
    # ================================================================
    mid_x2 = 7.8

    # 1- → MUX2 COM
    draw_wire(ax, ad3_out_x, scope_y + 0.05, mid_x2, scope_y + 0.05, color="#1976D2", lw=1.2)
    draw_wire(ax, mid_x2, scope_y + 0.05, mid_x2, mux2_com_y, color="#1976D2", lw=1.2)
    draw_wire(ax, mid_x2, mux2_com_y, mux2_x, mux2_com_y, color="#0D47A1", lw=1.8)
    ax.text(mid_x2 + 0.15, (scope_y + 0.05 + mux2_com_y) / 2 + 0.5, "1−",
            ha="left", va="center", fontsize=7, color="#1976D2", rotation=90)

    # RefR 配線もこのノードへ
    draw_wire(ax, ad3_out_x, ref_y + 0.3, mid_x2 + 0.3, ref_y + 0.3, color="#999", lw=1.0, ls="--")
    draw_wire(ax, mid_x2 + 0.3, ref_y + 0.3, mid_x2 + 0.3, mux2_com_y, color="#999", lw=1.0, ls="--")
    ax.plot(mid_x2, mux2_com_y, "o", color="#333", markersize=5, zorder=6)

    # GND
    draw_wire(ax, ad3_out_x, gnd_y, mid_x2 + 0.6, gnd_y, color="#666", lw=1.0, ls="--")
    # GND シンボル
    gnd_sym_x = mid_x2 + 0.6
    for d in [-0.15, 0, 0.15]:
        w = 0.2 - abs(d) * 0.8
        draw_wire(ax, gnd_sym_x - w, gnd_y + d - 0.2, gnd_sym_x + w, gnd_y + d - 0.2, color="#666", lw=1.5)
    draw_wire(ax, gnd_sym_x, gnd_y, gnd_sym_x, gnd_y - 0.2, color="#666", lw=1.5)

    # ================================================================
    # Arduino → MUX1 制御線 (D2→S0, D3→S1, D4→S2)
    # ================================================================
    mux1_colors = ["#E65100", "#F57C00", "#FF9800"]
    for i in range(3):
        # Arduino pin → intermediate
        ard_pin_x = ard_x + ard_w
        int_x = 7.2 + i * 0.2
        draw_wire(ax, ard_pin_x, pin_ys[i], int_x, pin_ys[i], color=mux1_colors[i], lw=1.0)
        draw_wire(ax, int_x, pin_ys[i], int_x, mux1_ctrl_ys[i], color=mux1_colors[i], lw=1.0)
        draw_wire(ax, int_x, mux1_ctrl_ys[i], mux1_x, mux1_ctrl_ys[i], color=mux1_colors[i], lw=1.0)

    # Arduino → MUX2 制御線 (D5→S0, D6→S1, D7→S2)
    mux2_colors = ["#1A237E", "#283593", "#3949AB"]
    for i in range(3):
        ard_pin_x = ard_x + ard_w
        j = i + 3  # pin_ys index
        int_x = 7.8 + i * 0.15
        draw_wire(ax, ard_pin_x, pin_ys[j], int_x, pin_ys[j], color=mux2_colors[i], lw=1.0)
        draw_wire(ax, int_x, pin_ys[j], int_x, mux2_ctrl_ys[i], color=mux2_colors[i], lw=1.0)
        draw_wire(ax, int_x, mux2_ctrl_ys[i], mux2_x, mux2_ctrl_ys[i], color=mux2_colors[i], lw=1.0)

    # ================================================================
    # MUX → イオンゲル端子 配線
    # ================================================================
    # 端子マッピング: Y0→A, Y1→B, Y2→C, Y3→D
    terminal_order = ["A", "B", "C", "D"]
    mux_out_colors = ["#D32F2F", "#E91E63", "#9C27B0", "#673AB7"]
    sink_colors = ["#0D47A1", "#1565C0", "#1976D2", "#1E88E5"]

    # MUX1 (Source) → ゲル端子
    for i, tname in enumerate(terminal_order):
        tx, ty = terminals[tname]
        mx = mux1_x + mux1_w
        my = mux1_ch_ys[i]
        # 中継点
        relay_x = 12.0 + i * 0.15
        draw_wire(ax, mx, my, relay_x, my, color=mux_out_colors[i], lw=1.2)
        draw_wire(ax, relay_x, my, relay_x, ty, color=mux_out_colors[i], lw=1.2)
        draw_wire(ax, relay_x, ty, tx, ty, color=mux_out_colors[i], lw=1.2)

    # MUX2 (Sink) → ゲル端子
    for i, tname in enumerate(terminal_order):
        tx, ty = terminals[tname]
        mx = mux2_x + mux2_w
        my = mux2_ch_ys[i]
        relay_x = 12.6 + i * 0.15
        draw_wire(ax, mx, my, relay_x, my, color=sink_colors[i], lw=1.2)
        draw_wire(ax, relay_x, my, relay_x, ty, color=sink_colors[i], lw=1.2)
        draw_wire(ax, relay_x, ty, tx, ty, color=sink_colors[i], lw=1.0)

    # ================================================================
    # 信号フロー注釈
    # ================================================================
    # 測定フロー説明
    note_x, note_y = 0.0, -0.5
    notes = [
        "【測定フロー】",
        "1. PC → Arduino: MUXチャンネル選択コマンド (例: S0K1)",
        "2. Arduino → MUX1/MUX2: 制御信号 (D2-D7) でチャンネル切替",
        "3. AD3 W1+: 励起信号 (1kHz, 0.1V) → MUX1 → ゲル端子[Source]",
        "4. ゲル端子[Sink] → MUX2 → AD3 1−: 応答信号をインピーダンス計測",
        "5. 6ペア (AB,AD,BC,BD,CD,AC) を順次測定 → NN で押圧位置推定",
    ]
    for i, note in enumerate(notes):
        weight = "bold" if i == 0 else "normal"
        ax.text(note_x, note_y - i * 0.35, note, ha="left", va="top",
                fontsize=7.5, color="#333", fontweight=weight)

    # Arduino ピンマッピング注釈
    ax.text(8.5, 9.2, "Arduino → MUX 制御ピンマッピング",
            ha="left", fontsize=8, fontweight="bold", color="#555")
    pin_info = [
        "D2→MUX1_S0  D3→MUX1_S1  D4→MUX1_S2  (Source選択)",
        "D5→MUX2_S0  D6→MUX2_S1  D7→MUX2_S2  (Sink選択)",
    ]
    for i, pi in enumerate(pin_info):
        ax.text(8.5, 8.85 - i * 0.3, pi, ha="left", fontsize=7,
                color="#666")

    # AD3 設定情報
    ax.text(3.0, 9.2, "AD3 インピーダンス測定設定",
            ha="left", fontsize=8, fontweight="bold", color="#555")
    ad3_info = [
        "Mode: Impedance (8)  Freq: 1kHz",
        "Amplitude: 0.1V  Ref R: 10kΩ",
    ]
    for i, ai in enumerate(ad3_info):
        ax.text(3.0, 8.85 - i * 0.3, ai, ha="left", fontsize=7,
                color="#666")

    # ================================================================
    # 凡例
    # ================================================================
    legend_x, legend_y = 14.0, 9.2
    ax.text(legend_x, legend_y, "凡例", fontsize=8, fontweight="bold", color="#555")
    legend_items = [
        ("━━", "#D32F2F", "Source (励起)"),
        ("━━", "#0D47A1", "Sink (応答)"),
        ("━━", "#F9A825", "USB通信"),
        ("╌╌", "#999999", "GND / Ref R"),
    ]
    for i, (sym, col, desc) in enumerate(legend_items):
        ly = legend_y - 0.35 * (i + 1)
        ls = "--" if sym == "╌╌" else "-"
        draw_wire(ax, legend_x, ly, legend_x + 0.5, ly, color=col, lw=2, ls=ls)
        ax.text(legend_x + 0.65, ly, desc, ha="left", va="center",
                fontsize=7, color="#333")

    # ================================================================
    # 保存
    # ================================================================
    plt.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"回路図を保存しました: {output_path}")


if __name__ == "__main__":
    import os
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "circuit_diagram.png")
    generate_circuit_diagram(output)
