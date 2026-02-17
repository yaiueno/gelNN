"""元のプレゼンテーションの内容をすべて抽出するスクリプト"""
from pptx import Presentation
from pptx.util import Emu

prs = Presentation("original_presentation.pptx")
print(f"Slide size: {prs.slide_width/914400:.2f}\" x {prs.slide_height/914400:.2f}\"")
print(f"Slide count: {len(prs.slides)}")

for i, slide in enumerate(prs.slides, 1):
    print(f"\n{'='*80}")
    print(f"  SLIDE {i}")
    print(f"{'='*80}")
    
    for j, shape in enumerate(slide.shapes):
        print(f"\n  Shape {j+1}: type={shape.shape_type}, name={shape.name}")
        print(f"    pos=({shape.left/914400:.3f}\", {shape.top/914400:.3f}\"), size=({shape.width/914400:.3f}\" x {shape.height/914400:.3f}\")")
        
        # Fill info
        if hasattr(shape, "fill"):
            try:
                f = shape.fill
                if f.type is not None:
                    print(f"    fill.type: {f.type}")
                    try:
                        print(f"    fill.fore_color.rgb: {f.fore_color.rgb}")
                    except:
                        pass
            except:
                pass
        
        if shape.has_text_frame:
            tf = shape.text_frame
            for k, p in enumerate(tf.paragraphs):
                txt = p.text.strip()
                if txt:
                    print(f"    Paragraph {k+1}: alignment={p.alignment}, text=\"{txt}\"")
                    for m, run in enumerate(p.runs):
                        f = run.font
                        try:
                            c = str(f.color.rgb)
                        except:
                            c = "N/A"
                        sz = f"{f.size/12700:.1f}pt" if f.size else "None"
                        print(f"      Run {m+1}: \"{run.text}\" font={f.name} size={sz} bold={f.bold} italic={f.italic} color={c}")
        
        # Check for images
        if shape.shape_type == 13:  # Picture
            try:
                img = shape.image
                print(f"    Image: content_type={img.content_type}, size={len(img.blob)} bytes")
            except Exception as e:
                print(f"    Image error: {e}")
        
        # Check for tables
        if shape.has_table:
            table = shape.table
            print(f"    Table: {len(table.rows)} rows x {len(table.columns)} cols")
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    if cell.text.strip():
                        print(f"      Cell[{r_idx},{c_idx}]: \"{cell.text.strip()}\"")
