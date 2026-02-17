"""
研究発表スライド生成スクリプト
python-pptx を使用し、「読みやすさ」を最優先したレイアウトで生成する。
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
SLIDE_WIDTH  = Inches(13.333)   # 16:9 ワイドスライド
SLIDE_HEIGHT = Inches(7.5)

# 色定義
COLOR_WHITE      = RGBColor(255, 255, 255)
COLOR_TEXT        = RGBColor(50, 50, 50)
COLOR_HEADER_BG  = RGBColor(44, 62, 80)      # 濃紺の帯
COLOR_HEADER_TXT = RGBColor(255, 255, 255)
COLOR_PLACEHOLDER = RGBColor(230, 230, 230)   # 図表エリアの薄いグレー
COLOR_ACCENT     = RGBColor(52, 152, 219)     # アクセント（青）
COLOR_SLIDE_NUM  = RGBColor(150, 150, 150)

# フォント
FONT_MAIN = "MS PGothic"
FONT_SUB  = "Arial"

# レイアウト寸法
MARGIN          = Inches(0.5)
HEADER_HEIGHT   = Inches(0.7)
CONTENT_TOP     = HEADER_HEIGHT + Inches(0.25)
CONTENT_HEIGHT  = SLIDE_HEIGHT - CONTENT_TOP - MARGIN
CONTENT_WIDTH   = SLIDE_WIDTH - MARGIN * 2

# 黄金比 6:4 分割
LEFT_RATIO  = 0.58          # テキスト側（少し余白を確保）
RIGHT_RATIO = 0.38          # 図表側
GAP         = Inches(0.3)   # 左右間のギャップ

LEFT_WIDTH  = int(CONTENT_WIDTH * LEFT_RATIO)
RIGHT_WIDTH = int(CONTENT_WIDTH * RIGHT_RATIO)
RIGHT_LEFT  = MARGIN + LEFT_WIDTH + GAP

# セクション色マップ（帯の色を変えて視覚的に区別）
SECTION_COLORS = {
    "背景": RGBColor(44, 62, 80),
    "手法": RGBColor(39, 174, 96),
    "結果": RGBColor(192, 57, 43),
}

# ──────────────────────────────────────────────
# スライド構成データ（ここを書き換えて使用）
# ──────────────────────────────────────────────
slides_data = [
    {
        "section": "背景",
        "title": "研究の背景と課題",
        "points": [
            "複雑な物理現象のシミュレーション",
            "既存手法における計算負荷の増大",
        ],
    },
    {
        "section": "手法",
        "title": "提案手法の概要",
        "points": [
            "アルゴリズムの並列化による高速化",
            "C++およびOpenGLを用いた可視化",
        ],
    },
    {
        "section": "結果",
        "title": "評価実験の結果",
        "points": [
            "従来手法と比較して20%の高速化",
            "計算精度の維持を確認",
        ],
    },
]


# ──────────────────────────────────────────────
# ヘルパー関数
# ──────────────────────────────────────────────
def set_font(run, size_pt, bold=False, color=COLOR_TEXT, font_name=FONT_MAIN):
    """Run のフォントを一括設定する。"""
    run.font.size = Pt(size_pt)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name


def add_header_band(slide, section_name, slide_index, total):
    """スライド上部にセクション名の帯を配置する。"""
    band_color = SECTION_COLORS.get(section_name, COLOR_HEADER_BG)

    # 帯シェイプ
    band = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_WIDTH, HEADER_HEIGHT
    )
    band.fill.solid()
    band.fill.fore_color.rgb = band_color
    band.line.fill.background()  # 枠線なし

    # セクションラベル（左寄せ）
    tf = band.text_frame
    tf.word_wrap = True
    tf.paragraphs[0].alignment = PP_ALIGN.LEFT
    run = tf.paragraphs[0].add_run()
    run.text = f"  {section_name}"
    set_font(run, 20, bold=True, color=COLOR_HEADER_TXT, font_name=FONT_MAIN)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    # スライド番号（右下）
    num_box = slide.shapes.add_textbox(
        SLIDE_WIDTH - Inches(1.0),
        SLIDE_HEIGHT - Inches(0.45),
        Inches(0.8),
        Inches(0.35),
    )
    ntf = num_box.text_frame
    ntf.paragraphs[0].alignment = PP_ALIGN.RIGHT
    nrun = ntf.paragraphs[0].add_run()
    nrun.text = f"{slide_index} / {total}"
    set_font(nrun, 12, color=COLOR_SLIDE_NUM, font_name=FONT_SUB)


def add_title_text(slide, title_text):
    """タイトルテキスト（36pt 太字）を左領域上部に配置する。"""
    title_box = slide.shapes.add_textbox(
        MARGIN, CONTENT_TOP, LEFT_WIDTH, Inches(0.7)
    )
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title_text
    set_font(run, 36, bold=True, color=COLOR_TEXT)

    # タイトル下にアクセントライン
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        MARGIN,
        CONTENT_TOP + Inches(0.75),
        Inches(2.0),
        Inches(0.04),
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_ACCENT
    line.line.fill.background()


def add_bullet_points(slide, points):
    """箇条書き（24pt、広めの行間）を左領域に配置する。"""
    bullets_top = CONTENT_TOP + Inches(1.1)
    bullets_height = CONTENT_HEIGHT - Inches(1.1)
    bullet_box = slide.shapes.add_textbox(
        MARGIN + Inches(0.15), bullets_top, LEFT_WIDTH - Inches(0.15), bullets_height
    )
    tf = bullet_box.text_frame
    tf.word_wrap = True

    for i, point in enumerate(points):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        # 行間: 1.8 行（詰まりを防ぐ）
        p.space_before = Pt(18)
        p.space_after  = Pt(12)
        p.line_spacing = Pt(36)       # 行間を広めに確保
        p.alignment = PP_ALIGN.LEFT

        # ● 記号 + テキスト
        run = p.add_run()
        run.text = f"●  {point}"
        set_font(run, 24, color=COLOR_TEXT)


def add_figure_placeholder(slide, slide_index):
    """
    右側（40%）に図表配置エリア（薄いグレー）を設置する。
    座標を返すので、後で画像を差し替えやすい。
    """
    fig_top    = CONTENT_TOP + Inches(0.3)
    fig_height = CONTENT_HEIGHT - Inches(0.6)

    placeholder = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        RIGHT_LEFT,
        fig_top,
        RIGHT_WIDTH,
        fig_height,
    )
    placeholder.fill.solid()
    placeholder.fill.fore_color.rgb = COLOR_PLACEHOLDER
    placeholder.line.color.rgb = RGBColor(200, 200, 200)
    placeholder.line.width = Pt(1)

    # 中央に案内テキスト
    tf = placeholder.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = "図表配置エリア"
    set_font(run, 18, color=RGBColor(160, 160, 160), font_name=FONT_MAIN)

    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = f"(Slide {slide_index})"
    set_font(run2, 12, color=RGBColor(180, 180, 180), font_name=FONT_SUB)

    # 座標情報を返す（後でグラフ画像を挿入する際に利用）
    coords = {
        "left":   RIGHT_LEFT,
        "top":    fig_top,
        "width":  RIGHT_WIDTH,
        "height": fig_height,
    }
    return coords


# ──────────────────────────────────────────────
# メイン: スライド生成
# ──────────────────────────────────────────────
def generate_presentation(data, output_path="research_presentation.pptx"):
    prs = Presentation()
    prs.slide_width  = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT

    total_slides = len(data)
    figure_coords = {}  # {slide_index: coords} を後で利用可能

    for idx, slide_info in enumerate(data, start=1):
        # 空白レイアウトを使用（自前で全要素を配置）
        blank_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_layout)

        # 背景を白に設定
        bg = slide.background
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_WHITE

        # 各要素を配置
        add_header_band(slide, slide_info["section"], idx, total_slides)
        add_title_text(slide, slide_info["title"])
        add_bullet_points(slide, slide_info["points"])
        coords = add_figure_placeholder(slide, idx)
        figure_coords[idx] = coords

    prs.save(output_path)

    # 座標情報を表示（後で画像を差し替える際のリファレンス）
    print(f"\n=== 生成完了: {output_path} ===\n")
    print("図表配置エリアの座標 (Inches):")
    print("-" * 50)
    for si, c in figure_coords.items():
        print(
            f"  Slide {si}: "
            f"left={c['left'] / 914400:.2f}\", "
            f"top={c['top'] / 914400:.2f}\", "
            f"width={c['width'] / 914400:.2f}\", "
            f"height={c['height'] / 914400:.2f}\""
        )
    print("-" * 50)
    print(
        "\n画像挿入例:\n"
        "  slide.shapes.add_picture('fig.png',\n"
        "      left=coords['left'], top=coords['top'],\n"
        "      width=coords['width'], height=coords['height'])\n"
    )


if __name__ == "__main__":
    generate_presentation(slides_data)
