"""pptx の全情報を詳細に読み取る検査スクリプト"""
from pptx import Presentation
from pptx.util import Emu, Pt

prs = Presentation("research_presentation.pptx")
print(f"スライドサイズ: {prs.slide_width/914400:.2f}\" x {prs.slide_height/914400:.2f}\"")
print(f"スライド数: {len(prs.slides)}")
print("=" * 80)

for i, slide in enumerate(prs.slides, 1):
    print(f"\n{'='*80}")
    print(f"  SLIDE {i}")
    print(f"{'='*80}")

    # 背景
    bg = slide.background.fill
    print(f"  背景 fill type: {bg.type}")
    try:
        print(f"  背景色: {bg.fore_color.rgb}")
    except Exception:
        pass

    for j, shape in enumerate(slide.shapes):
        print(f"\n  --- Shape {j+1} ---")
        print(f"    shape_type: {shape.shape_type}")
        print(f"    name: {shape.name}")
        print(f"    position: left={shape.left/914400:.3f}\", top={shape.top/914400:.3f}\"")
        print(f"    size: width={shape.width/914400:.3f}\", height={shape.height/914400:.3f}\"")
        print(f"    rotation: {shape.rotation}")

        # Fill
        if hasattr(shape, "fill"):
            try:
                f = shape.fill
                print(f"    fill.type: {f.type}")
                if f.type is not None:
                    try:
                        print(f"    fill.fore_color.rgb: {f.fore_color.rgb}")
                    except Exception:
                        pass
            except Exception:
                pass

        # Line
        if hasattr(shape, "line"):
            try:
                ln = shape.line
                print(f"    line.width: {ln.width}")
                try:
                    print(f"    line.color.rgb: {ln.color.rgb}")
                except Exception:
                    print(f"    line.fill.type: {ln.fill.type}")
            except Exception:
                pass

        # Auto shape type
        try:
            print(f"    auto_shape_type: {shape.auto_shape_type}")
        except Exception:
            pass

        # Text frame
        if shape.has_text_frame:
            tf = shape.text_frame
            print(f"    text_frame.word_wrap: {tf.word_wrap}")
            try:
                print(f"    text_frame.vertical_anchor: {tf.vertical_anchor}")
            except Exception:
                pass
            try:
                print(f"    text_frame.margin_left: {tf.margin_left}")
                print(f"    text_frame.margin_right: {tf.margin_right}")
                print(f"    text_frame.margin_top: {tf.margin_top}")
                print(f"    text_frame.margin_bottom: {tf.margin_bottom}")
            except Exception:
                pass

            for k, p in enumerate(tf.paragraphs):
                print(f"    --- Paragraph {k+1} ---")
                print(f"      alignment: {p.alignment}")
                print(f"      level: {p.level}")
                if p.space_before is not None:
                    print(f"      space_before: {p.space_before} EMU = {p.space_before/12700:.1f}pt")
                else:
                    print(f"      space_before: None")
                if p.space_after is not None:
                    print(f"      space_after: {p.space_after} EMU = {p.space_after/12700:.1f}pt")
                else:
                    print(f"      space_after: None")
                if p.line_spacing is not None:
                    print(f"      line_spacing: {p.line_spacing} EMU = {p.line_spacing/12700:.1f}pt")
                else:
                    print(f"      line_spacing: None")

                # Bullet / numbering
                pf = p._pPr
                if pf is not None:
                    buNone = pf.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}buNone")
                    buChar = pf.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}buChar")
                    buAutoNum = pf.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}buAutoNum")
                    if buChar:
                        print(f"      bullet: buChar = {buChar[0].attrib}")
                    if buAutoNum:
                        print(f"      bullet: buAutoNum = {buAutoNum[0].attrib}")
                    if buNone:
                        print(f"      bullet: buNone")

                for m, run in enumerate(p.runs):
                    print(f"      --- Run {m+1} ---")
                    print(f"        text: \"{run.text}\"")
                    f = run.font
                    print(f"        font.name: {f.name}")
                    print(f"        font.size: {f.size} EMU = {f.size/12700:.1f}pt" if f.size else f"        font.size: None")
                    print(f"        font.bold: {f.bold}")
                    print(f"        font.italic: {f.italic}")
                    print(f"        font.underline: {f.underline}")
                    try:
                        print(f"        font.color.rgb: {f.color.rgb}")
                    except Exception:
                        print(f"        font.color.type: {f.color.type}")
                    try:
                        print(f"        font.color.theme_color: {f.color.theme_color}")
                    except Exception:
                        pass

    print()
