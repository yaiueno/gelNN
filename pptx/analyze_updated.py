"""更新済みプレゼンテーションの全情報を詳細に読み取る"""
from pptx import Presentation

prs = Presentation("updated_original.pptx")
print(f"Slide size: {prs.slide_width/914400:.2f}\" x {prs.slide_height/914400:.2f}\"")
print(f"Slide count: {len(prs.slides)}")

for i, slide in enumerate(prs.slides, 1):
    print(f"\n{'='*80}")
    print(f"  SLIDE {i}")
    print(f"{'='*80}")
    
    for j, shape in enumerate(slide.shapes):
        print(f"\n  Shape {j+1}: type={shape.shape_type}, name={shape.name}")
        print(f"    pos=({shape.left/914400:.3f}\", {shape.top/914400:.3f}\"), size=({shape.width/914400:.3f}\" x {shape.height/914400:.3f}\")")
        
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
                    print(f"    P{k+1}: align={p.alignment}, text=\"{txt}\"")
                    for m, run in enumerate(p.runs):
                        f = run.font
                        try:
                            c = str(f.color.rgb)
                        except:
                            c = "N/A"
                        sz = f"{f.size/12700:.1f}pt" if f.size else "None"
                        print(f"      R{m+1}: \"{run.text}\" font={f.name} sz={sz} b={f.bold} i={f.italic} c={c}")
        
        if shape.shape_type == 13:
            try:
                img = shape.image
                print(f"    IMAGE: {img.content_type}, {len(img.blob)} bytes, aspect={shape.width/shape.height:.3f}")
            except Exception as e:
                print(f"    IMAGE ERROR: {e}")
        
        if shape.has_table:
            table = shape.table
            print(f"    TABLE: {len(table.rows)}r x {len(table.columns)}c")
            for r_idx, row in enumerate(table.rows):
                cells = []
                for c_idx, cell in enumerate(row.cells):
                    cells.append(cell.text.strip())
                print(f"      Row {r_idx}: {cells}")
