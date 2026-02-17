"""
元のプレゼンテーションをプロフェッショナルなデザインで再生成するスクリプト
- モダンな配色・タイポグラフィ
- 統一されたヘッダー帯＋セクションカラー
- 画像・テーブルをすべて保持
- 適切な余白・行間
"""

import io
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ──────────────────────────────────────────────
# 定数
# ──────────────────────────────────────────────
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# 色パレット (モダンブルー系)
C_PRIMARY     = RGBColor(25, 55, 109)    # ダークブルー (ヘッダー帯)
C_ACCENT      = RGBColor(0, 120, 212)    # アクセントブルー
C_ACCENT2     = RGBColor(0, 164, 239)    # ライトアクセント
C_TEXT_DARK   = RGBColor(45, 45, 48)     # 本文テキスト
C_TEXT_LIGHT  = RGBColor(255, 255, 255)  # 白テキスト
C_TEXT_SUB    = RGBColor(100, 100, 105)  # サブテキスト
C_BG_WHITE    = RGBColor(255, 255, 255)  # スライド背景
C_BG_LIGHT    = RGBColor(245, 247, 250)  # 薄いグレー背景
C_BORDER      = RGBColor(220, 225, 230)  # 罫線
C_TABLE_HDR   = RGBColor(25, 55, 109)    # テーブルヘッダー
C_TABLE_ALT   = RGBColor(235, 240, 248)  # テーブル交互行

# セクション別アクセントカラー
SECTION_COLORS = {
    "title":   RGBColor(25, 55, 109),
    "背景":    RGBColor(25, 55, 109),
    "経緯":    RGBColor(50, 90, 140),
    "方法":    RGBColor(0, 120, 160),
    "材料":    RGBColor(0, 120, 160),
    "結果":    RGBColor(0, 145, 100),
    "考察":    RGBColor(180, 95, 20),
    "展望":    RGBColor(130, 60, 160),
    "参考":    RGBColor(80, 80, 85),
}

# フォント
FONT_JP = "Meiryo UI"
FONT_EN = "Segoe UI"

# レイアウト寸法
MARGIN_L  = Inches(0.6)
MARGIN_R  = Inches(0.6)
MARGIN_T  = Inches(0.15)
HDR_H     = Inches(0.85)
CONTENT_T = HDR_H + Inches(0.25)
CONTENT_W = SLIDE_W - MARGIN_L - MARGIN_R
CONTENT_H = SLIDE_H - CONTENT_T - Inches(0.5)
FOOTER_Y  = SLIDE_H - Inches(0.4)

TOTAL_SLIDES = 20


# ──────────────────────────────────────────────
# ヘルパー
# ──────────────────────────────────────────────

def set_font(run, size_pt, bold=False, italic=False, color=C_TEXT_DARK, font_name=FONT_JP):
    run.font.size  = Pt(size_pt)
    run.font.bold  = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name  = font_name


def add_background(slide, color=C_BG_WHITE):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def add_header_bar(slide, section_label, section_key="背景"):
    """上部にモダンなヘッダー帯を追加"""
    bar_color = SECTION_COLORS.get(section_key, C_PRIMARY)

    # メイン帯
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, HDR_H)
    bar.fill.solid()
    bar.fill.fore_color.rgb = bar_color
    bar.line.fill.background()

    # アクセントライン (帯の下に細い水色ライン)
    accent_line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, HDR_H, SLIDE_W, Inches(0.04)
    )
    accent_line.fill.solid()
    accent_line.fill.fore_color.rgb = C_ACCENT2
    accent_line.line.fill.background()

    # セクションラベル
    tf = bar.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.7)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = section_label
    set_font(run, 26, bold=True, color=C_TEXT_LIGHT, font_name=FONT_JP)


def add_slide_number(slide, num):
    """右下にスライド番号"""
    box = slide.shapes.add_textbox(
        SLIDE_W - Inches(1.2), FOOTER_Y, Inches(1.0), Inches(0.3)
    )
    tf = box.text_frame
    tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
    run = tf.paragraphs[0].add_run()
    run.text = f"{num} / {TOTAL_SLIDES}"
    set_font(run, 10, color=C_TEXT_SUB, font_name=FONT_EN)


def add_title_on_slide(slide, title_text, top=None, left=None, width=None, size_pt=30):
    """スライドタイトル (ヘッダー帯の下)"""
    _top   = top or CONTENT_T
    _left  = left or MARGIN_L
    _width = width or CONTENT_W
    box = slide.shapes.add_textbox(_left, _top, _width, Inches(0.6))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title_text
    set_font(run, size_pt, bold=True, color=C_TEXT_DARK)

    # タイトル下アクセントライン
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        _left, _top + Inches(0.55),
        Inches(2.5), Inches(0.035)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = C_ACCENT
    line.line.fill.background()
    return _top + Inches(0.7)


def add_body_text(slide, text, top, left=None, width=None, height=None, size_pt=14, bold=False, color=None):
    """本文テキストを追加"""
    _left  = left or MARGIN_L
    _width = width or CONTENT_W
    _height = height or Inches(0.5)
    _color = color or C_TEXT_DARK
    box = slide.shapes.add_textbox(_left, top, _width, _height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    p.space_after = Pt(6)
    p.line_spacing = Pt(size_pt * 1.7)
    run = p.add_run()
    run.text = text
    set_font(run, size_pt, bold=bold, color=_color)
    return tf


def add_multiline_text(slide, lines, top, left=None, width=None, height=None, size_pt=14, heading_size=16):
    """複数行テキスト (見出しと本文を含む)"""
    _left  = left or MARGIN_L
    _width = width or CONTENT_W
    _height = height or CONTENT_H
    box = slide.shapes.add_textbox(_left, top, _width, _height)
    tf = box.text_frame
    tf.word_wrap = True

    for i, line_data in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        text = line_data["text"]
        is_heading = line_data.get("heading", False)
        is_bullet = line_data.get("bullet", False)
        indent = line_data.get("indent", 0)

        if is_heading:
            p.space_before = Pt(14) if i > 0 else Pt(0)
            p.space_after = Pt(6)
            p.line_spacing = Pt(heading_size * 1.5)
            run = p.add_run()
            run.text = text
            set_font(run, heading_size, bold=True, color=C_PRIMARY)
        elif is_bullet:
            p.space_before = Pt(4)
            p.space_after = Pt(4)
            p.line_spacing = Pt(size_pt * 1.7)
            p.level = indent
            run = p.add_run()
            run.text = f"  •  {text}" if indent == 0 else f"      •  {text}"
            set_font(run, size_pt, color=C_TEXT_DARK)
        else:
            p.space_before = Pt(3)
            p.space_after = Pt(3)
            p.line_spacing = Pt(size_pt * 1.7)
            run = p.add_run()
            prefix = "　" * indent
            run.text = f"{prefix}{text}"
            set_font(run, size_pt, color=C_TEXT_DARK)

    return tf


def add_card(slide, left, top, width, height, fill_color=C_BG_LIGHT, border_color=C_BORDER):
    """背景カード（角丸四角形）を追加"""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = fill_color
    card.line.color.rgb = border_color
    card.line.width = Pt(0.75)
    # 角丸の調整
    try:
        card.adjustments[0] = 0.02
    except:
        pass
    return card


def add_table(slide, table_data, left, top, width, row_height=Inches(0.4)):
    """プロフェッショナルなテーブルを追加"""
    rows = len(table_data)
    cols = len(table_data[0]) if rows > 0 else 1
    height = row_height * rows

    table_shape = slide.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table

    col_width = width // cols
    for c in range(cols):
        table.columns[c].width = col_width

    for r_idx, row_data in enumerate(table_data):
        for c_idx, cell_text in enumerate(row_data):
            cell = table.cell(r_idx, c_idx)
            cell.text = ""
            tf = cell.text_frame
            tf.word_wrap = True
            tf.margin_left = Inches(0.08)
            tf.margin_right = Inches(0.08)
            tf.margin_top = Inches(0.04)
            tf.margin_bottom = Inches(0.04)

            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER if c_idx > 0 or r_idx == 0 else PP_ALIGN.LEFT
            run = p.add_run()
            run.text = cell_text

            if r_idx == 0:
                # ヘッダー行
                set_font(run, 11, bold=True, color=C_TEXT_LIGHT, font_name=FONT_JP)
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_TABLE_HDR
            else:
                set_font(run, 11, color=C_TEXT_DARK, font_name=FONT_JP)
                cell.fill.solid()
                if r_idx % 2 == 0:
                    cell.fill.fore_color.rgb = C_TABLE_ALT
                else:
                    cell.fill.fore_color.rgb = C_BG_WHITE

    return table_shape


def extract_images(src_prs):
    """元のプレゼンテーションから全画像を抽出"""
    images = {}
    for i, slide in enumerate(src_prs.slides, 1):
        slide_images = []
        for shape in slide.shapes:
            if shape.shape_type == 13:  # PICTURE
                img = shape.image
                slide_images.append({
                    "blob": img.blob,
                    "content_type": img.content_type,
                    "left": shape.left,
                    "top": shape.top,
                    "width": shape.width,
                    "height": shape.height,
                    "name": shape.name,
                })
        images[i] = slide_images
    return images


# ──────────────────────────────────────────────
# メイン生成
# ──────────────────────────────────────────────

def generate_redesigned(src_path="original_presentation.pptx", out_path="redesigned_presentation.pptx"):
    # 元のプレゼンテーションから画像を抽出
    src_prs = Presentation(src_path)
    images = extract_images(src_prs)

    # 新しいプレゼンテーション
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    slide_num = 0

    # ============================================================
    # Slide 1: タイトルスライド
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl, C_PRIMARY)

    # 装飾: 右下に大きなアクセント円
    circle = sl.shapes.add_shape(
        MSO_SHAPE.OVAL, SLIDE_W - Inches(4), SLIDE_H - Inches(4),
        Inches(6), Inches(6)
    )
    circle.fill.solid()
    circle.fill.fore_color.rgb = RGBColor(30, 65, 125)
    circle.line.fill.background()
    circle.rotation = 0

    # 装飾: 左上に小さなアクセント
    circle2 = sl.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(-1.5), Inches(-1.5),
        Inches(4), Inches(4)
    )
    circle2.fill.solid()
    circle2.fill.fore_color.rgb = RGBColor(20, 50, 100)
    circle2.line.fill.background()

    # アクセントライン
    aline = sl.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(3.1),
        Inches(3), Inches(0.05)
    )
    aline.fill.solid()
    aline.fill.fore_color.rgb = C_ACCENT2
    aline.line.fill.background()

    # メインタイトル
    title_box = sl.shapes.add_textbox(Inches(1.2), Inches(1.5), Inches(10), Inches(1.5))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = "イオン液体で作成した"
    set_font(run, 44, bold=True, color=C_TEXT_LIGHT)
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.LEFT
    run2 = p2.add_run()
    run2.text = "DMAAmゲル"
    set_font(run2, 52, bold=True, color=C_ACCENT2)

    # サブタイトル
    sub_box = sl.shapes.add_textbox(Inches(1.2), Inches(3.4), Inches(8), Inches(1.2))
    tf2 = sub_box.text_frame
    tf2.word_wrap = True
    p3 = tf2.paragraphs[0]
    p3.alignment = PP_ALIGN.LEFT
    p3.line_spacing = Pt(28)
    run3 = p3.add_run()
    run3.text = "ソフトマターセンサー材料としての機械特性・電気特性の評価"
    set_font(run3, 18, color=RGBColor(180, 200, 230))

    # スライド番号
    add_slide_number(sl, slide_num)

    # ============================================================
    # Slide 2: 実験の背景
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験の背景", "背景")
    add_slide_number(sl, slide_num)

    body_top = CONTENT_T + Inches(0.1)
    lines = [
        {"text": "1. 背景", "heading": True},
        {"text": "ソフトマターセンサーは、ウェアラブルデバイスや生体計測などの医療分野に加え、ロボット分野への応用においても高い需要がある。これらの用途では、柔軟性と変形追従性を兼ね備えた材料が求められる。その候補材料としてゲルに着目した。"},
        {"text": "イオン液体そのものをセンサー材料とする手法も報告[0]されているが、液体であるため取り扱いや形状保持に課題がある。一方、イオン液体をゲル化することで、固体として扱うことが可能となり、柔軟性と安定性の両立が期待される。"},
        {"text": "2. 目的", "heading": True},
        {"text": "ソフトマターセンサー材料には、使用時の変形に耐える十分な機械的強度、変形を検出可能な電気的応答性が求められる。本研究では、イオン液体を含有させたN,N-ジメチルアクリルアミド（DMAAm）ゲルについて、機械特性（引張特性）、電気特性（インピーダンス特性）を評価し、ソフトマターセンサー材料としての適性を検討することを目的とする。"},
    ]
    add_multiline_text(sl, lines, body_top, height=CONTENT_H)

    # ============================================================
    # Slide 3: 実験の経緯1
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験の経緯", "経緯")
    add_slide_number(sl, slide_num)

    lines = [
        {"text": "1. 当初の計画概要", "heading": True},
        {"text": "今回扱う材料の候補として、DNゲル（ダブルネットワークゲル）、ひも状ミセルなどが他にあった。作業人数やテーマに関する観点から、DNゲルとN,N-ジメチルアクリルアミド（DMAAm）ゲルを選択した。二つのグループに分かれて作業し、本グループはN,N-ジメチルアクリルアミド（DMAAm）ゲルを担当した。"},
        {"text": "2. 当初の実験計画", "heading": True},
        {"text": "以下の２点を想定していた。"},
        {"text": "(i) フォーステスターを使用した引張試験", "bullet": True},
        {"text": "(ii) チューブ状に整形したゲルのインピーダンス測定", "bullet": True},
    ]
    add_multiline_text(sl, lines, body_top, height=CONTENT_H)

    # ============================================================
    # Slide 4: 実験の経緯2
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験の経緯", "経緯")
    add_slide_number(sl, slide_num)

    lines = [
        {"text": "3. 実験中に生じた課題", "heading": True},
        {"text": "(ii)について、チューブ状に液体を詰めた状態で紫外線を当てゲルを固めることには成功したが、有意な電気的応答性が得られなかった。チューブ内の気泡が原因だと思われる。"},
        {"text": "4. 変更・改善した点", "heading": True},
        {"text": "(ii)について、チューブの口径をより大きいものに変更する案もあったが、実験の手法自体を変更することにした。チューブではなく、シャーレの上でゲルを固めることにした。"},
    ]
    add_multiline_text(sl, lines, body_top, height=CONTENT_H)

    # ============================================================
    # Slide 5: 実験方法
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験方法", "方法")
    add_slide_number(sl, slide_num)

    # 左側: テキスト
    text_w = Inches(7.5)
    lines = [
        {"text": "1. DMAAmゲルの作成", "heading": True},
        {"text": "イオン液体[L]に対してDMAAm(モノマー)2[mol/L], α-keto(開始剤)0.001[mol/L], MBAA(架橋剤)0.02[mol/L]を混ぜたものを作成する。DMAAmを0.03[mol/L], 0.04[mol/L]にしたものも作成する。これらを8×8×2[mm]のスペーサーに流し込み紫外線で固めゲルにする。また、同様にシャーレに流し込み固める。"},
        {"text": "2. DMAAmゲルの引張試験", "heading": True},
        {"text": "作成したDMAAmゲルをダンベル状7号型(図1)で型を取り、フォーステスターを使用して引張試験を行う。"},
        {"text": "3. DMAAmゲルのインピーダンスの測定", "heading": True},
        {"text": "ANALOG DISCOVERY 3を使用してDMAAmゲルのインピーダンスを測定する。作成したDMAAmゲルをダンベル状7号型(図1)で型を取ったものとシャーレに作成したDMAAmゲルにアルミホイル(電極)を付けたもの(図2)のインピーダンスを測定する。"},
    ]
    add_multiline_text(sl, lines, body_top, width=text_w, height=CONTENT_H, size_pt=13)

    # 右側: 画像 (図1, 図2)
    img_left = MARGIN_L + text_w + Inches(0.3)
    img_w = SLIDE_W - img_left - MARGIN_R
    if len(images.get(5, [])) >= 2:
        # 図1: ダンベル状7号
        blob1 = images[5][0]["blob"]
        stream1 = io.BytesIO(blob1)
        sl.shapes.add_picture(stream1, img_left, CONTENT_T + Inches(0.5), img_w, Inches(1.8))
        # キャプション
        cap1 = sl.shapes.add_textbox(img_left, CONTENT_T + Inches(2.4), img_w, Inches(0.3))
        tf_c1 = cap1.text_frame
        tf_c1.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_c1 = tf_c1.paragraphs[0].add_run()
        r_c1.text = "図1. ダンベル状7号"
        set_font(r_c1, 10, color=C_TEXT_SUB)

        # 図2: シャーレのゲル
        blob2 = images[5][1]["blob"]
        stream2 = io.BytesIO(blob2)
        sl.shapes.add_picture(stream2, img_left, CONTENT_T + Inches(3.0), img_w, Inches(1.8))
        cap2 = sl.shapes.add_textbox(img_left, CONTENT_T + Inches(4.9), img_w, Inches(0.3))
        tf_c2 = cap2.text_frame
        tf_c2.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_c2 = tf_c2.paragraphs[0].add_run()
        r_c2.text = "図2. シャーレに作成したDMAAmゲル"
        set_font(r_c2, 10, color=C_TEXT_SUB)

    # ============================================================
    # Slide 6: 使用器具
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "使用器具", "方法")
    add_slide_number(sl, slide_num)

    equipment = [
        "ANALOG DISCOVERY 3",
        "シャーレ（直径69 mm）",
        "アルミホイル（電極）",
        "フォーステスター（MCT-1150/2150/2150W）",
        "電極クリップ",
        "SD型レバー式試料裁断機（型式SDL-100）",
        "スーパーダンベルカッター（型式SDMP-1000-D, 規格JIS K6251-7号）",
        "紫外線照射装置（※手作りのため製品情報なし）",
    ]
    lines = [{"text": item, "bullet": True} for item in equipment]
    add_multiline_text(sl, lines, body_top + Inches(0.2), height=CONTENT_H, size_pt=16)

    # ============================================================
    # Slide 7: 実験材料
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験材料", "材料")
    add_slide_number(sl, slide_num)

    materials = [
        ["No.", "材料名", "化学式", "役割"],
        ["1", "1-ブチル-3-メチルイミダゾリウム\nビス(フルオロスルホニル)イミド", "C₈H₁₅F₂N₃O₄S₂", "イオン液体"],
        ["2", "N,N-ジメチルアクリルアミド", "C₅H₉NO", "モノマー"],
        ["3", "α-ケトグルタル酸", "C₅H₆O₅", "開始剤"],
        ["4", "N,N'-メチレンビスアクリルアミド", "C₇H₁₀N₂O₂", "架橋剤"],
    ]
    add_table(sl, materials, Inches(0.8), body_top + Inches(0.3), Inches(11.7), Inches(0.55))

    # 右側に画像 (材料の構造式)
    img_top = body_top + Inches(3.5)
    if images.get(7):
        for idx, img_data in enumerate(images[7][:4]):
            x = MARGIN_L + Inches(idx * 3)
            blob = img_data["blob"]
            stream = io.BytesIO(blob)
            sl.shapes.add_picture(stream, x, img_top, Inches(2.6), Inches(1.2))
            # 参考文献番号
            ref_box = sl.shapes.add_textbox(x + Inches(2.0), img_top + Inches(1.0), Inches(0.5), Inches(0.3))
            rf = ref_box.text_frame
            rf.paragraphs[0].alignment = PP_ALIGN.RIGHT
            rr = rf.paragraphs[0].add_run()
            rr.text = f"[{idx+1}]"
            set_font(rr, 9, color=C_TEXT_SUB, font_name=FONT_EN)

    # ============================================================
    # Slide 8: 実験1 引張試験 - 分量テーブル
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験1：引張試験", "方法")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "DMAAmゲルの作成条件")

    tensile_data = [
        ["", "DMAAm 2 [mol/L]", "DMAAm 3 [mol/L]", "DMAAm 4 [mol/L]"],
        ["イオン液体 [g]", "13.597", "13.607", "13.620"],
        ["架橋剤 [g]", "0.061", "0.061", "0.061"],
        ["モノマー [g]", "1.983", "2.974", "3.965"],
        ["開始剤 [mg]", "3.0", "3.1", "3.1"],
    ]
    add_table(sl, tensile_data, Inches(2.5), next_y + Inches(0.3), Inches(8.5), Inches(0.55))

    caption = sl.shapes.add_textbox(Inches(2.5), next_y + Inches(3.3), Inches(8.5), Inches(0.4))
    tf_cap = caption.text_frame
    tf_cap.paragraphs[0].alignment = PP_ALIGN.CENTER
    r_cap = tf_cap.paragraphs[0].add_run()
    r_cap.text = "表1. DMAAmゲルを作る際に実際に使用した材料の分量"
    set_font(r_cap, 12, color=C_TEXT_SUB)

    # ============================================================
    # Slide 9-12: グラフスライド (力-変位曲線)
    # ============================================================
    graph_slides = [
        (9,  "図3. DMAAm 2[mol/L] の力-変位曲線"),
        (10, "図4. DMAAm 3[mol/L] の力-変位曲線"),
        (11, "図5. DMAAm 4[mol/L] の力-変位曲線"),
        (12, "図6. DMAAm 各濃度の重ね合わせ力-変位曲線"),
    ]
    for orig_slide_num, caption_text in graph_slides:
        slide_num += 1
        sl = prs.slides.add_slide(blank)
        add_background(sl)
        add_header_bar(sl, "実験1：引張試験結果", "結果")
        add_slide_number(sl, slide_num)

        if images.get(orig_slide_num) and len(images[orig_slide_num]) > 0:
            blob = images[orig_slide_num][0]["blob"]
            stream = io.BytesIO(blob)
            # 画像を中央に大きく配置
            img_w = Inches(10)
            img_h = Inches(5.2)
            img_left = (SLIDE_W - img_w) // 2
            img_top = CONTENT_T + Inches(0.1)
            sl.shapes.add_picture(stream, img_left, img_top, img_w, img_h)

        # キャプション
        cap = sl.shapes.add_textbox(Inches(2), SLIDE_H - Inches(0.85), Inches(9), Inches(0.4))
        tf_cap = cap.text_frame
        tf_cap.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_cap = tf_cap.paragraphs[0].add_run()
        r_cap.text = caption_text
        set_font(r_cap, 14, bold=True, color=C_TEXT_SUB)

    # ============================================================
    # Slide 13: 箱ひげ図
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験1：引張試験結果", "結果")
    add_slide_number(sl, slide_num)

    if images.get(13) and len(images[13]) > 0:
        blob = images[13][0]["blob"]
        stream = io.BytesIO(blob)
        img_w = Inches(7.5)
        img_h = Inches(5.5)
        img_left = (SLIDE_W - img_w) // 2
        sl.shapes.add_picture(stream, img_left, CONTENT_T + Inches(0.05), img_w, img_h)

    cap = sl.shapes.add_textbox(Inches(2), SLIDE_H - Inches(0.85), Inches(9), Inches(0.4))
    tf_cap = cap.text_frame
    tf_cap.paragraphs[0].alignment = PP_ALIGN.CENTER
    r_cap = tf_cap.paragraphs[0].add_run()
    r_cap.text = "図7. DMAAm 濃度別ピーク荷重の箱ひげ図"
    set_font(r_cap, 14, bold=True, color=C_TEXT_SUB)

    # ============================================================
    # Slide 14: 考察1
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "考察1：引張試験", "考察")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "引張試験に関する考察")

    # 背景カード
    card_top = next_y + Inches(0.1)
    add_card(sl, MARGIN_L, card_top, CONTENT_W, Inches(3.5))

    lines = [
        {"text": "図3～図6より、モノマーが2[mol/L]から4[mol/L]の濃度範囲では、モノマーの濃度を大きくするほど強度が高くなることがわかった。"},
        {"text": "モノマーが2[mol/L]の場合、試験片を作成する際や実際に引張試験をする際にも、その脆さから操作が難しく、センサーへの応用はかなり限定的な場面に限られると考えられる。"},
        {"text": "モノマー濃度が4[mol/L]のものが最も強度が高かったので、今回の実験ではこの濃度のDMAAmゲルを使用して実験2を行った。"},
    ]
    add_multiline_text(sl, lines, card_top + Inches(0.2),
                       left=MARGIN_L + Inches(0.3), width=CONTENT_W - Inches(0.6),
                       height=Inches(3.2), size_pt=15)

    # ============================================================
    # Slide 15: 実験2 インピーダンス測定 条件
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験2：インピーダンス測定", "方法")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "測定条件")

    # 説明文
    desc_box = sl.shapes.add_textbox(MARGIN_L, next_y, CONTENT_W, Inches(0.5))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    p_desc = tf_desc.paragraphs[0]
    r_desc = p_desc.add_run()
    r_desc.text = "シャーレに作成したDMAAmゲル 4[mol/L]について、Analog Discovery 3を用いて加圧によるインピーダンスの変化を測定した。"
    set_font(r_desc, 14, color=C_TEXT_DARK)

    impedance_data = [
        ["項目", "条件・設定値", "備考"],
        ["試料", "DMAAmゲル (4 mol/L)", "初期厚さ: 6 mm"],
        ["電極", "アルミニウム箔", "ゲル対角線上に密着貼付"],
        ["測定機器", "Analog Discovery 3", "インピーダンスアナライザ機能"],
        ["周波数範囲", "1 kHz ～ 100 kHz", ""],
        ["印加電圧", "振幅 1 V (バイアス 0 V)", ""],
        ["掃引点数", "50 点 (対数スイープ)", ""],
        ["加圧条件", "手押し (Manual Press)", "定性的なインピーダンス変化を観測"],
    ]
    add_table(sl, impedance_data, Inches(1.5), next_y + Inches(0.7), Inches(10.3), Inches(0.5))

    # ============================================================
    # Slide 16: インピーダンス測定結果
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験2：測定結果", "結果")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "インピーダンス測定結果")

    if images.get(16) and len(images[16]) >= 2:
        half_w = Inches(5.8)
        gap = Inches(0.3)
        left1 = MARGIN_L
        left2 = MARGIN_L + half_w + gap

        blob1 = images[16][0]["blob"]
        stream1 = io.BytesIO(blob1)
        sl.shapes.add_picture(stream1, left1, next_y + Inches(0.2), half_w, Inches(3.7))

        blob2 = images[16][1]["blob"]
        stream2 = io.BytesIO(blob2)
        sl.shapes.add_picture(stream2, left2, next_y + Inches(0.2), half_w, Inches(3.7))

    # ============================================================
    # Slide 17: インピーダンス測定結果分析
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "実験2：結果分析", "結果")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "インピーダンス測定結果の分析")

    if images.get(17) and len(images[17]) >= 2:
        half_w = Inches(5.8)
        gap = Inches(0.3)
        left1 = MARGIN_L
        left2 = MARGIN_L + half_w + gap

        blob1 = images[17][0]["blob"]
        stream1 = io.BytesIO(blob1)
        sl.shapes.add_picture(stream1, left1, next_y + Inches(0.2), half_w, Inches(3.7))

        blob2 = images[17][1]["blob"]
        stream2 = io.BytesIO(blob2)
        sl.shapes.add_picture(stream2, left2, next_y + Inches(0.2), half_w, Inches(3.7))

    # ============================================================
    # Slide 18: 考察2
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "考察2：インピーダンス測定", "考察")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "インピーダンス測定に関する考察")

    # カード1: 観測結果
    card_top1 = next_y + Inches(0.1)
    add_card(sl, MARGIN_L, card_top1, CONTENT_W, Inches(1.5), fill_color=RGBColor(240, 248, 255))
    
    obs_label = sl.shapes.add_textbox(MARGIN_L + Inches(0.3), card_top1 + Inches(0.15), Inches(2), Inches(0.35))
    tf_ol = obs_label.text_frame
    r_ol = tf_ol.paragraphs[0].add_run()
    r_ol.text = "◆ 観測結果"
    set_font(r_ol, 14, bold=True, color=C_ACCENT)
    
    obs_txt = sl.shapes.add_textbox(MARGIN_L + Inches(0.3), card_top1 + Inches(0.5), CONTENT_W - Inches(0.6), Inches(0.8))
    tf_ot = obs_txt.text_frame
    tf_ot.word_wrap = True
    r_ot = tf_ot.paragraphs[0].add_run()
    r_ot.text = "インピーダンスの周波数特性には手で押したときと離したときに変化が見られた。"
    set_font(r_ot, 15, color=C_TEXT_DARK)

    # 矢印 (下向き)
    arrow = sl.shapes.add_shape(
        MSO_SHAPE.DOWN_ARROW, (SLIDE_W - Inches(1)) // 2,
        card_top1 + Inches(1.7), Inches(1), Inches(0.6)
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = C_ACCENT
    arrow.line.fill.background()

    # カード2: 結論
    card_top2 = card_top1 + Inches(2.5)
    add_card(sl, MARGIN_L, card_top2, CONTENT_W, Inches(1.8), fill_color=RGBColor(255, 248, 240))
    
    conc_label = sl.shapes.add_textbox(MARGIN_L + Inches(0.3), card_top2 + Inches(0.15), Inches(2), Inches(0.35))
    tf_cl = conc_label.text_frame
    r_cl = tf_cl.paragraphs[0].add_run()
    r_cl.text = "◆ 応用可能性"
    set_font(r_cl, 14, bold=True, color=RGBColor(180, 95, 20))
    
    conc_txt = sl.shapes.add_textbox(MARGIN_L + Inches(0.3), card_top2 + Inches(0.55), CONTENT_W - Inches(0.6), Inches(1.0))
    tf_ct = conc_txt.text_frame
    tf_ct.word_wrap = True
    r_ct = tf_ct.paragraphs[0].add_run()
    r_ct.text = "インピーダンスの周波数特性の差分を測定し、分析・機械学習させることによって圧力センサーやタッチセンサーとして活用可能"
    set_font(r_ct, 15, color=C_TEXT_DARK)

    # ============================================================
    # Slide 19: 今後の展望
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "今後の展望", "展望")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "今後の研究展望")

    prospects = [
        "今回実験した範囲内では、モノマーの濃度が大きくなるほどゲルの強度（引張試験）が上昇したが、より大きなスケールでモノマーの濃度を変化させ、どの範囲までこの傾向が続くかを調査してみたい。",
        "実験2と同じ形式で、ゲルの濃度を変化させた際、結果がどのように変化するか調査することも、今後の課題として挙げられる。",
        "今回の実験だけでは、ソフトマターセンサーの応用に関するゲルの特性について十分には調べきれていないので、より多角的に、形状、特殊な形状にしたときの電気的応答性、ゲル、接点間距離などについて調査が必要。",
    ]
    
    for i, prospect in enumerate(prospects):
        card_y = next_y + Inches(i * 1.6)
        # 番号アイコン
        num_circle = sl.shapes.add_shape(
            MSO_SHAPE.OVAL, MARGIN_L, card_y + Inches(0.15),
            Inches(0.45), Inches(0.45)
        )
        num_circle.fill.solid()
        num_circle.fill.fore_color.rgb = SECTION_COLORS["展望"]
        num_circle.line.fill.background()
        tf_num = num_circle.text_frame
        tf_num.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf_num.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_num = tf_num.paragraphs[0].add_run()
        r_num.text = str(i + 1)
        set_font(r_num, 14, bold=True, color=C_TEXT_LIGHT, font_name=FONT_EN)

        # テキスト
        txt_box = sl.shapes.add_textbox(
            MARGIN_L + Inches(0.65), card_y + Inches(0.05),
            CONTENT_W - Inches(0.65), Inches(1.3)
        )
        tf_txt = txt_box.text_frame
        tf_txt.word_wrap = True
        p_txt = tf_txt.paragraphs[0]
        p_txt.line_spacing = Pt(22)
        r_txt = p_txt.add_run()
        r_txt.text = prospect
        set_font(r_txt, 14, color=C_TEXT_DARK)

    # ============================================================
    # Slide 20: 参考文献
    # ============================================================
    slide_num += 1
    sl = prs.slides.add_slide(blank)
    add_background(sl)
    add_header_bar(sl, "参考文献", "参考")
    add_slide_number(sl, slide_num)

    next_y = add_title_on_slide(sl, "参考文献")

    references = [
        ("[0]", "CHEMFISH「イオン液体ゲルの高感度圧力センサー」\nhttps://www.chemfish.co.jp/index.php?id=3890"),
        ("[1]", "Cica-Web「1-ブチル-3-メチルイミダゾリウムビス(フルオロスルホニル)イミド」\nhttps://cica-web.kanto.co.jp/CicaWeb/servlet/wsj.front.LogonSvlt?ReqItem=05816-35"),
        ("[2]", "FUJIFILM「N,N-ジメチルアクリルアミド」\nhttps://labchem-wako.fujifilm.com/jp/product/detail/W01W0104-1918.html"),
        ("[3]", "MilliporeSigma「α-ケトグルタル酸」\nhttps://www.sigmaaldrich.com/JP/ja/product/sigma/k1750"),
        ("[4]", "TCI「N,N'-Methylenebisacrylamide」\nhttps://www.tcichemicals.com/JP/ja/p/M0506"),
    ]

    for i, (ref_num, ref_text) in enumerate(references):
        ref_y = next_y + Inches(i * 0.9)
        # 番号
        num_box = sl.shapes.add_textbox(MARGIN_L, ref_y, Inches(0.5), Inches(0.3))
        tf_n = num_box.text_frame
        r_n = tf_n.paragraphs[0].add_run()
        r_n.text = ref_num
        set_font(r_n, 12, bold=True, color=C_PRIMARY, font_name=FONT_EN)

        # テキスト
        ref_box = sl.shapes.add_textbox(MARGIN_L + Inches(0.5), ref_y, CONTENT_W - Inches(0.5), Inches(0.8))
        tf_r = ref_box.text_frame
        tf_r.word_wrap = True
        p_r = tf_r.paragraphs[0]
        p_r.line_spacing = Pt(18)
        r_r = p_r.add_run()
        r_r.text = ref_text
        set_font(r_r, 11, color=C_TEXT_DARK)

    # ============================================================
    # 保存
    # ============================================================
    prs.save(out_path)
    print(f"\n生成完了: {out_path}")
    print(f"合計 {slide_num} スライド")


if __name__ == "__main__":
    generate_redesigned()
