from pptx import Presentation

prs = Presentation("research_presentation.pptx")
print(f"スライドサイズ: {prs.slide_width/914400:.2f}\" x {prs.slide_height/914400:.2f}\"")
print(f"スライド数: {len(prs.slides)}\n")

for i, slide in enumerate(prs.slides, 1):
    print(f"=== Slide {i} ===")
    bg = slide.background.fill
    print(f"  背景: type={bg.type}")
    for shape in slide.shapes:
        print(f"  Shape: {shape.shape_type}, pos=({shape.left/914400:.2f}\", {shape.top/914400:.2f}\"), size=({shape.width/914400:.2f}\" x {shape.height/914400:.2f}\")")
        if shape.has_text_frame:
            for p in shape.text_frame.paragraphs:
                txt = p.text.strip()
                if txt:
                    for r in p.runs:
                        f = r.font
                        print(f"    Text: \"{r.text.strip()}\"  font={f.name}, size={f.size}, bold={f.bold}, color={f.color.rgb}")
        if hasattr(shape, "fill") and shape.fill.type is not None:
            try:
                print(f"    Fill: {shape.fill.fore_color.rgb}")
            except Exception:
                pass
    print()
