"""
更新済みプレゼンテーションをプロフェッショナルなデザインで再生成するスクリプト
- モダンな配色・タイポグラフィ
- 画像のアスペクト比を保持
- 考察2は矢印で論理展開
"""

import io
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

# 色パレット
C_PRIMARY     = RGBColor(25, 55, 109)
C_ACCENT      = RGBColor(0, 120, 212)
C_ACCENT2     = RGBColor(0, 164, 239)
C_TEXT_DARK   = RGBColor(45, 45, 48)
C_TEXT_LIGHT  = RGBColor(255, 255, 255)
C_TEXT_SUB    = RGBColor(100, 100, 105)
C_BG_WHITE    = RGBColor(255, 255, 255)
C_BG_LIGHT    = RGBColor(245, 247, 250)
C_BORDER      = RGBColor(220, 225, 230)
C_TABLE_HDR   = RGBColor(25, 55, 109)
C_TABLE_ALT   = RGBColor(235, 240, 248)

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

FONT_JP = "Meiryo UI"
FONT_EN = "Segoe UI"

MARGIN_L  = Inches(0.6)
MARGIN_R  = Inches(0.6)
HDR_H     = Inches(0.85)
CONTENT_T = HDR_H + Inches(0.25)
CONTENT_W = SLIDE_W - MARGIN_L - MARGIN_R
CONTENT_H = SLIDE_H - CONTENT_T - Inches(0.5)
FOOTER_Y  = SLIDE_H - Inches(0.4)


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
    bar_color = SECTION_COLORS.get(section_key, C_PRIMARY)
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, HDR_H)
    bar.fill.solid()
    bar.fill.fore_color.rgb = bar_color
    bar.line.fill.background()

    accent_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, HDR_H, SLIDE_W, Inches(0.04))
    accent_line.fill.solid()
    accent_line.fill.fore_color.rgb = C_ACCENT2
    accent_line.line.fill.background()

    tf = bar.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.7)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = section_label
    set_font(run, 26, bold=True, color=C_TEXT_LIGHT)


def add_slide_number(slide, num, total):
    box = slide.shapes.add_textbox(SLIDE_W - Inches(1.2), FOOTER_Y, Inches(1.0), Inches(0.3))
    tf = box.text_frame
    tf.paragraphs[0].alignment = PP_ALIGN.RIGHT
    run = tf.paragraphs[0].add_run()
    run.text = f"{num} / {total}"
    set_font(run, 10, color=C_TEXT_SUB, font_name=FONT_EN)


def add_title_on_slide(slide, title_text, top=None, left=None, width=None, size_pt=30):
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

    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, _left, _top + Inches(0.55),
        Inches(2.5), Inches(0.035)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = C_ACCENT
    line.line.fill.background()
    return _top + Inches(0.7)


def add_multiline_text(slide, lines, top, left=None, width=None, height=None, size_pt=14, heading_size=16):
    _left  = left or MARGIN_L
    _width = width or CONTENT_W
    _height = height or CONTENT_H
    box = slide.shapes.add_textbox(_left, top, _width, _height)
    tf = box.text_frame
    tf.word_wrap = True

    for i, line_data in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        text = line_data["text"]
        is_heading = line_data.get("heading", False)
        is_bullet = line_data.get("bullet", False)

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
            run = p.add_run()
            run.text = f"  •  {text}"
            set_font(run, size_pt, color=C_TEXT_DARK)
        else:
            p.space_before = Pt(3)
            p.space_after = Pt(3)
            p.line_spacing = Pt(size_pt * 1.7)
            run = p.add_run()
            run.text = text
            set_font(run, size_pt, color=C_TEXT_DARK)
    return tf


def add_card(slide, left, top, width, height, fill_color=C_BG_LIGHT, border_color=C_BORDER):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = fill_color
    card.line.color.rgb = border_color
    card.line.width = Pt(0.75)
    try:
        card.adjustments[0] = 0.02
    except:
        pass
    return card


def add_table(slide, table_data, left, top, width, row_height=Inches(0.4)):
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
                set_font(run, 11, bold=True, color=C_TEXT_LIGHT)
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_TABLE_HDR
            else:
                set_font(run, 11, color=C_TEXT_DARK)
                cell.fill.solid()
                cell.fill.fore_color.rgb = C_TABLE_ALT if r_idx % 2 == 0 else C_BG_WHITE
    return table_shape


def add_picture_preserve_aspect(slide, blob, left, top, max_width=None, max_height=None, orig_aspect=None):
    """画像をアスペクト比を保持して配置。max_width/max_heightの範囲内に収める。"""
    stream = io.BytesIO(blob)
    # まずmax_widthベースで計算
    if max_width and max_height and orig_aspect:
        # max_width基準の高さ
        h_from_w = int(max_width / orig_aspect)
        # max_height基準の幅
        w_from_h = int(max_height * orig_aspect)
        
        if h_from_w <= max_height:
            w, h = max_width, h_from_w
        else:
            w, h = w_from_h, max_height
    elif max_width and orig_aspect:
        w = max_width
        h = int(max_width / orig_aspect)
    elif max_height and orig_aspect:
        h = max_height
        w = int(max_height * orig_aspect)
    else:
        w = max_width or Inches(5)
        h = max_height or Inches(3)
    
    pic = slide.shapes.add_picture(stream, left, top, w, h)
    return pic, w, h


def add_arrow_down(slide, cx, top, width=Inches(0.8), height=Inches(0.5), color=None):
    """下向き矢印を追加"""
    _color = color or C_ACCENT
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.DOWN_ARROW,
        cx - width // 2, top, width, height
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = _color
    arrow.line.fill.background()
    return arrow


def add_flow_card(slide, left, top, width, height, label, text, label_color=C_ACCENT, bg_color=None):
    """ラベル付きカード（論理フロー用）"""
    _bg = bg_color or RGBColor(240, 248, 255)
    card = add_card(slide, left, top, width, height, fill_color=_bg, border_color=label_color)

    # ラベル
    lbl = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.1), width - Inches(0.5), Inches(0.35))
    tf_l = lbl.text_frame
    r_l = tf_l.paragraphs[0].add_run()
    r_l.text = label
    set_font(r_l, 13, bold=True, color=label_color)

    # テキスト
    txt = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.42), width - Inches(0.5), height - Inches(0.55))
    tf_t = txt.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.line_spacing = Pt(20)
    r_t = p_t.add_run()
    r_t.text = text
    set_font(r_t, 13, color=C_TEXT_DARK)
    return card


def add_right_arrow(slide, left, top, width=Inches(0.7), height=Inches(0.5), color=None):
    """右向き矢印"""
    _color = color or C_ACCENT
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW,
        left, top, width, height
    )
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = _color
    arrow.line.fill.background()
    return arrow


def extract_images(src_prs):
    """元のプレゼンテーションから全画像を抽出（アスペクト比情報含む）"""
    images = {}
    for i, slide in enumerate(src_prs.slides, 1):
        slide_images = []
        for shape in slide.shapes:
            if shape.shape_type == 13:
                img = shape.image
                slide_images.append({
                    "blob": img.blob,
                    "content_type": img.content_type,
                    "orig_width": shape.width,
                    "orig_height": shape.height,
                    "aspect": shape.width / shape.height,
                    "name": shape.name,
                })
        images[i] = slide_images
    return images


# ──────────────────────────────────────────────
# メイン生成
# ──────────────────────────────────────────────

def generate_redesigned(src_path="updated_original.pptx", out_path="redesigned_updated.pptx"):
    src_prs = Presentation(src_path)
    images = extract_images(src_prs)

    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    all_slides = []  # 後でスライド番号を振るために追跡

    def new_slide():
        sl = prs.slides.add_slide(blank)
        add_background(sl)
        all_slides.append(sl)
        return sl

    # ============================================================
    # Slide 1: タイトルスライド
    # ============================================================
    sl = new_slide()
    add_background(sl, C_PRIMARY)

    # 装飾
    circle = sl.shapes.add_shape(MSO_SHAPE.OVAL, SLIDE_W - Inches(4), SLIDE_H - Inches(4), Inches(6), Inches(6))
    circle.fill.solid()
    circle.fill.fore_color.rgb = RGBColor(30, 65, 125)
    circle.line.fill.background()

    circle2 = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(-1.5), Inches(-1.5), Inches(4), Inches(4))
    circle2.fill.solid()
    circle2.fill.fore_color.rgb = RGBColor(20, 50, 100)
    circle2.line.fill.background()

    aline = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(3.1), Inches(3), Inches(0.05))
    aline.fill.solid()
    aline.fill.fore_color.rgb = C_ACCENT2
    aline.line.fill.background()

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

    sub_box = sl.shapes.add_textbox(Inches(1.2), Inches(3.4), Inches(8), Inches(1.2))
    tf2 = sub_box.text_frame
    tf2.word_wrap = True
    p3 = tf2.paragraphs[0]
    p3.alignment = PP_ALIGN.LEFT
    p3.line_spacing = Pt(28)
    run3 = p3.add_run()
    run3.text = "ソフトマターセンサー材料としての機械特性・電気特性の評価"
    set_font(run3, 18, color=RGBColor(180, 200, 230))

    # ============================================================
    # Slide 2: 実験の背景
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "実験の背景", "背景")
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
    sl = new_slide()
    add_header_bar(sl, "実験の経緯", "経緯")
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
    sl = new_slide()
    add_header_bar(sl, "実験の経緯", "経緯")
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
    sl = new_slide()
    add_header_bar(sl, "実験方法", "方法")
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

    # 右側: 画像 (図1, 図2) - アスペクト比保持
    img_left = MARGIN_L + text_w + Inches(0.3)
    img_area_w = SLIDE_W - img_left - MARGIN_R
    if len(images.get(5, [])) >= 2:
        img1 = images[5][0]
        max_h1 = Inches(1.8)
        pic1, w1, h1 = add_picture_preserve_aspect(sl, img1["blob"], img_left, CONTENT_T + Inches(0.5),
                                                     max_width=img_area_w, max_height=max_h1, orig_aspect=img1["aspect"])
        cap1 = sl.shapes.add_textbox(img_left, CONTENT_T + Inches(0.5) + h1 + Inches(0.05), img_area_w, Inches(0.3))
        tf_c1 = cap1.text_frame
        tf_c1.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_c1 = tf_c1.paragraphs[0].add_run()
        r_c1.text = "図1. ダンベル状7号"
        set_font(r_c1, 10, color=C_TEXT_SUB)

        img2 = images[5][1]
        img2_top = CONTENT_T + Inches(0.5) + h1 + Inches(0.5)
        max_h2 = Inches(2.0)
        pic2, w2, h2 = add_picture_preserve_aspect(sl, img2["blob"], img_left, img2_top,
                                                     max_width=img_area_w, max_height=max_h2, orig_aspect=img2["aspect"])
        cap2 = sl.shapes.add_textbox(img_left, img2_top + h2 + Inches(0.05), img_area_w, Inches(0.3))
        tf_c2 = cap2.text_frame
        tf_c2.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_c2 = tf_c2.paragraphs[0].add_run()
        r_c2.text = "図2. シャーレに作成したDMAAmゲル"
        set_font(r_c2, 10, color=C_TEXT_SUB)

    # ============================================================
    # Slide 6: 使用器具
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "使用器具", "方法")
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
    sl = new_slide()
    add_header_bar(sl, "実験材料", "材料")

    materials = [
        ["No.", "材料名", "化学式", "役割"],
        ["1", "1-ブチル-3-メチルイミダゾリウム\nビス(フルオロスルホニル)イミド", "C₈H₁₅F₂N₃O₄S₂", "イオン液体"],
        ["2", "N,N-ジメチルアクリルアミド", "C₅H₉NO", "モノマー"],
        ["3", "α-ケトグルタル酸", "C₅H₆O₅", "開始剤"],
        ["4", "N,N'-メチレンビスアクリルアミド", "C₇H₁₀N₂O₂", "架橋剤"],
    ]
    add_table(sl, materials, Inches(0.8), body_top + Inches(0.3), Inches(11.7), Inches(0.55))

    # 構造式画像（アスペクト比保持）
    img_top = body_top + Inches(3.5)
    if images.get(7):
        x_offset = MARGIN_L
        for idx, img_data in enumerate(images[7][:4]):
            max_w = Inches(2.6)
            max_h = Inches(1.2)
            pic, pw, ph = add_picture_preserve_aspect(sl, img_data["blob"], x_offset, img_top,
                                                       max_width=max_w, max_height=max_h, orig_aspect=img_data["aspect"])
            ref_box = sl.shapes.add_textbox(x_offset + pw - Inches(0.4), img_top + ph - Inches(0.2), Inches(0.5), Inches(0.3))
            rf = ref_box.text_frame
            rf.paragraphs[0].alignment = PP_ALIGN.RIGHT
            rr = rf.paragraphs[0].add_run()
            rr.text = f"[{idx+1}]"
            set_font(rr, 9, color=C_TEXT_SUB, font_name=FONT_EN)
            x_offset += Inches(3.0)

    # ============================================================
    # Slide 8: 実験1 引張試験 - 分量テーブル
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "実験1：引張試験", "方法")
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
    # Slide 9-12: グラフスライド (力-変位曲線) - アスペクト比保持
    # ============================================================
    graph_slides = [
        (9,  "図3. DMAAm 2[mol/L] の力-変位曲線"),
        (10, "図4. DMAAm 3[mol/L] の力-変位曲線"),
        (11, "図5. DMAAm 4[mol/L] の力-変位曲線"),
        (12, "図6. DMAAm 各濃度の重ね合わせ力-変位曲線"),
    ]
    for orig_slide_num, caption_text in graph_slides:
        sl = new_slide()
        add_header_bar(sl, "実験1：引張試験結果", "結果")

        if images.get(orig_slide_num) and len(images[orig_slide_num]) > 0:
            img_data = images[orig_slide_num][0]
            max_w = Inches(10)
            max_h = Inches(5.2)
            pic, pw, ph = add_picture_preserve_aspect(sl, img_data["blob"],
                                                       0, 0,  # placeholder pos
                                                       max_width=max_w, max_height=max_h,
                                                       orig_aspect=img_data["aspect"])
            # 中央配置
            pic.left = (SLIDE_W - pw) // 2
            pic.top = CONTENT_T + Inches(0.1)

        cap = sl.shapes.add_textbox(Inches(2), SLIDE_H - Inches(0.85), Inches(9), Inches(0.4))
        tf_cap = cap.text_frame
        tf_cap.paragraphs[0].alignment = PP_ALIGN.CENTER
        r_cap = tf_cap.paragraphs[0].add_run()
        r_cap.text = caption_text
        set_font(r_cap, 14, bold=True, color=C_TEXT_SUB)

    # ============================================================
    # Slide 13: 箱ひげ図
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "実験1：引張試験結果", "結果")

    if images.get(13) and len(images[13]) > 0:
        img_data = images[13][0]
        max_w = Inches(7.5)
        max_h = Inches(5.5)
        pic, pw, ph = add_picture_preserve_aspect(sl, img_data["blob"], 0, 0,
                                                   max_width=max_w, max_height=max_h,
                                                   orig_aspect=img_data["aspect"])
        pic.left = (SLIDE_W - pw) // 2
        pic.top = CONTENT_T + Inches(0.05)

    cap = sl.shapes.add_textbox(Inches(2), SLIDE_H - Inches(0.85), Inches(9), Inches(0.4))
    tf_cap = cap.text_frame
    tf_cap.paragraphs[0].alignment = PP_ALIGN.CENTER
    r_cap = tf_cap.paragraphs[0].add_run()
    r_cap.text = "図7. DMAAm 濃度別ピーク荷重の箱ひげ図"
    set_font(r_cap, 14, bold=True, color=C_TEXT_SUB)

    # ============================================================
    # Slide 14: 考察1
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "考察1：引張試験", "考察")
    next_y = add_title_on_slide(sl, "引張試験に関する考察")

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
    sl = new_slide()
    add_header_bar(sl, "実験2：インピーダンス測定", "方法")
    next_y = add_title_on_slide(sl, "測定条件")

    desc_box = sl.shapes.add_textbox(MARGIN_L, next_y, CONTENT_W, Inches(0.5))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    r_desc = tf_desc.paragraphs[0].add_run()
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
    sl = new_slide()
    add_header_bar(sl, "実験2：測定結果", "結果")
    next_y = add_title_on_slide(sl, "インピーダンス測定結果")

    if images.get(16) and len(images[16]) >= 2:
        gap = Inches(0.4)
        avail_w = (CONTENT_W - gap) // 2
        max_h = Inches(3.7)

        img1 = images[16][0]
        pic1, pw1, ph1 = add_picture_preserve_aspect(sl, img1["blob"], MARGIN_L, next_y + Inches(0.2),
                                                       max_width=avail_w, max_height=max_h, orig_aspect=img1["aspect"])

        img2 = images[16][1]
        pic2, pw2, ph2 = add_picture_preserve_aspect(sl, img2["blob"], MARGIN_L + avail_w + gap, next_y + Inches(0.2),
                                                       max_width=avail_w, max_height=max_h, orig_aspect=img2["aspect"])

    # ============================================================
    # Slide 17: インピーダンス測定結果分析
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "実験2：結果分析", "結果")
    next_y = add_title_on_slide(sl, "インピーダンス測定結果の分析")

    if images.get(17) and len(images[17]) >= 2:
        gap = Inches(0.4)
        avail_w = (CONTENT_W - gap) // 2
        max_h = Inches(3.7)

        img1 = images[17][0]
        pic1, pw1, ph1 = add_picture_preserve_aspect(sl, img1["blob"], MARGIN_L, next_y + Inches(0.2),
                                                       max_width=avail_w, max_height=max_h, orig_aspect=img1["aspect"])

        img2 = images[17][1]
        pic2, pw2, ph2 = add_picture_preserve_aspect(sl, img2["blob"], MARGIN_L + avail_w + gap, next_y + Inches(0.2),
                                                       max_width=avail_w, max_height=max_h, orig_aspect=img2["aspect"])

    # ============================================================
    # Slide 18-19: 考察2 - 矢印で論理展開（2スライド構成）
    # ============================================================
    # --- 考察2 スライド1: 観測→分析→応用可能性 ---
    sl = new_slide()
    add_header_bar(sl, "考察2：インピーダンス測定", "考察")
    next_y = add_title_on_slide(sl, "インピーダンス測定に関する考察")

    # 横方向フローレイアウト
    card_w = Inches(3.5)
    card_h = Inches(3.6)
    arrow_w = Inches(0.6)
    arrow_h = Inches(0.4)
    total_flow_w = card_w * 3 + arrow_w * 2
    flow_left = (SLIDE_W - total_flow_w) // 2
    flow_top = next_y + Inches(0.2)

    # カード1: 観測事実
    add_flow_card(sl, flow_left, flow_top, card_w, card_h,
                  "◆ Step 1：観測事実",
                  "インピーダンスの周波数特性には手で押したときと離したときに変化が見られた。",
                  label_color=RGBColor(0, 120, 212),
                  bg_color=RGBColor(235, 245, 255))

    # 矢印1
    add_right_arrow(sl,
                    flow_left + card_w + Inches(0.05),
                    flow_top + card_h // 2 - arrow_h // 2,
                    arrow_w - Inches(0.1), arrow_h,
                    color=RGBColor(0, 120, 212))

    # カード2: 定量分析
    card2_left = flow_left + card_w + arrow_w
    add_flow_card(sl, card2_left, flow_top, card_w, card_h,
                  "◆ Step 2：応用可能性",
                  "インピーダンスの周波数特性の差分を測定し、分析・機械学習させることによって圧力センサーやタッチセンサーとして活用可能。",
                  label_color=RGBColor(180, 95, 20),
                  bg_color=RGBColor(255, 245, 235))

    # 矢印2
    add_right_arrow(sl,
                    card2_left + card_w + Inches(0.05),
                    flow_top + card_h // 2 - arrow_h // 2,
                    arrow_w - Inches(0.1), arrow_h,
                    color=RGBColor(180, 95, 20))

    # カード3: 実証
    card3_left = card2_left + card_w + arrow_w
    add_flow_card(sl, card3_left, flow_top, card_w, card_h,
                  "◆ Step 3：プロトタイプ実証",
                  "サーキットラーンを用いた機械学習で判定ソフトプロトタイプを作成し、実演による検証を行った。",
                  label_color=RGBColor(0, 145, 100),
                  bg_color=RGBColor(235, 255, 245))

    # --- 考察2 スライド2: 損失正接の定量的分析 ---
    sl = new_slide()
    add_header_bar(sl, "考察2：定量分析", "考察")
    next_y = add_title_on_slide(sl, "損失正接による粘弾性評価")

    # 上段: 2つのカードを左右に配置（周波数ごとの分析）
    half_w = Inches(5.8)
    gap = Inches(0.5)
    c_top = next_y + Inches(0.15)
    c_h = Inches(1.8)

    # カード左: 10^5 Hz
    add_flow_card(sl, MARGIN_L, c_top, half_w, c_h,
                  "周波数 1×10⁵ Hz での分析",
                  "位相差が約1°であるため、損失正接は\ntan1° ≒ 0.0175 = 損失弾性率 / 貯蔵弾性率\n→ 貯蔵弾性率は損失弾性率の約57倍",
                  label_color=C_ACCENT, bg_color=RGBColor(240, 248, 255))

    # カード右: 10^6 Hz
    add_flow_card(sl, MARGIN_L + half_w + gap, c_top, half_w, c_h,
                  "周波数 1×10⁶ Hz での分析",
                  "位相差が約6°であるため、損失正接は\ntan6° ≒ 0.105\n→ 貯蔵弾性率は損失弾性率の約10倍",
                  label_color=RGBColor(180, 95, 20), bg_color=RGBColor(255, 248, 240))

    # 下向き矢印
    add_arrow_down(sl, SLIDE_W // 2, c_top + c_h + Inches(0.1),
                   width=Inches(0.7), height=Inches(0.45), color=C_PRIMARY)

    # 下段カード: 結論
    conc_top = c_top + c_h + Inches(0.65)
    conc_h = Inches(2.3)
    add_card(sl, MARGIN_L, conc_top, CONTENT_W, conc_h, fill_color=RGBColor(248, 250, 255), border_color=C_PRIMARY)

    conc_lines = [
        {"text": "▶ 総合考察", "heading": True},
        {"text": "実験で使用したゲルは 1×10⁵ Hz までは形を保とうとするが、1×10⁶ Hz くらいからは内部で摩擦やズレが生じエネルギーをロスしやすくなることがわかる。"},
        {"text": "周波数が 1×10⁵ Hz から 1×10⁶ Hz の間では位相差が小さいことから、超音波がゲルを通過する際に熱に変わらず信号が減衰しにくい。1 MHz 付近は医療用超音波や非破壊検査で多く使われるため、これらへの応用が期待できる。"},
    ]
    add_multiline_text(sl, conc_lines, conc_top + Inches(0.15),
                       left=MARGIN_L + Inches(0.3), width=CONTENT_W - Inches(0.6),
                       height=conc_h - Inches(0.3), size_pt=14)

    # ============================================================
    # Slide 20: 今後の展望
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "今後の展望", "展望")
    next_y = add_title_on_slide(sl, "今後の研究展望")

    prospects = [
        "今回実験した範囲内では、モノマーの濃度が大きくなるほどゲルの強度（引張試験）が上昇したが、より大きなスケールでモノマーの濃度を変化させ、どの範囲までこの傾向が続くかを調査する。",
        "実験2と同じ形式で、ゲルの濃度を変化させた際、結果がどのように変化するか調査することも、今後の課題として挙げられる。",
        "今回の実験では、ゲルを押下したときのインピーダンス変化をあくまで定性的に分析したが、押下した際の強さや位置の関係についても測定、分析、考察したい。",
    ]

    for i, prospect in enumerate(prospects):
        card_y = next_y + Inches(i * 1.6)
        num_circle = sl.shapes.add_shape(
            MSO_SHAPE.OVAL, MARGIN_L, card_y + Inches(0.15), Inches(0.45), Inches(0.45)
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

        txt_box = sl.shapes.add_textbox(MARGIN_L + Inches(0.65), card_y + Inches(0.05),
                                         CONTENT_W - Inches(0.65), Inches(1.3))
        tf_txt = txt_box.text_frame
        tf_txt.word_wrap = True
        p_txt = tf_txt.paragraphs[0]
        p_txt.line_spacing = Pt(22)
        r_txt = p_txt.add_run()
        r_txt.text = prospect
        set_font(r_txt, 14, color=C_TEXT_DARK)

    # ============================================================
    # Slide 21: 今後の展望 - 回路図
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "今後の展望：具体的構想", "展望")
    next_y = add_title_on_slide(sl, "押下位置推定のための装置構想")

    # 説明テキスト
    desc_box = sl.shapes.add_textbox(MARGIN_L, next_y, CONTENT_W, Inches(0.7))
    tf_desc = desc_box.text_frame
    tf_desc.word_wrap = True
    r_desc = tf_desc.paragraphs[0].add_run()
    r_desc.text = "具体的な構想として、以下のような回路を組みマルチプレクサで端子の組み合わせ ₂C₄ = 6通りで装置を作ることで、押下の位置推定を行うことを構想している。"
    set_font(r_desc, 14, color=C_TEXT_DARK)

    # 回路図画像（アスペクト比保持）
    if images.get(21) and len(images[21]) > 0:
        img_data = images[21][0]
        max_w = Inches(8)
        max_h = Inches(4.5)
        pic, pw, ph = add_picture_preserve_aspect(sl, img_data["blob"], 0, 0,
                                                   max_width=max_w, max_height=max_h,
                                                   orig_aspect=img_data["aspect"])
        pic.left = (SLIDE_W - pw) // 2
        pic.top = next_y + Inches(0.85)

    # ============================================================
    # Slide 22: 参考文献
    # ============================================================
    sl = new_slide()
    add_header_bar(sl, "参考文献", "参考")
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
        num_box = sl.shapes.add_textbox(MARGIN_L, ref_y, Inches(0.5), Inches(0.3))
        tf_n = num_box.text_frame
        r_n = tf_n.paragraphs[0].add_run()
        r_n.text = ref_num
        set_font(r_n, 12, bold=True, color=C_PRIMARY, font_name=FONT_EN)

        ref_box = sl.shapes.add_textbox(MARGIN_L + Inches(0.5), ref_y, CONTENT_W - Inches(0.5), Inches(0.8))
        tf_r = ref_box.text_frame
        tf_r.word_wrap = True
        p_r = tf_r.paragraphs[0]
        p_r.line_spacing = Pt(18)
        r_r = p_r.add_run()
        r_r.text = ref_text
        set_font(r_r, 11, color=C_TEXT_DARK)

    # ============================================================
    # スライド番号を全スライドに追加
    # ============================================================
    total = len(all_slides)
    for idx, sl in enumerate(all_slides, 1):
        add_slide_number(sl, idx, total)

    prs.save(out_path)
    print(f"\n生成完了: {out_path}")
    print(f"合計 {total} スライド")


if __name__ == "__main__":
    generate_redesigned()
