from docx import Document
import io

async def parse_docx(file) -> str:
    """
    Parses a DOCX file and converts it to basic HTML.
    Handles headings, paragraphs, bold, and italic formatting.
    """
    content = await file.read()
    doc = Document(io.BytesIO(content))
    
    html_output = []
    
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    # helper to find footnotes
    footnotes_map = {}
    try:
        # Access the footnotes part if it exists
        part = doc.part
        if hasattr(part, 'footnotes_part') and part.footnotes_part:
            footnotes_xml = part.footnotes_part.element
            for fn in footnotes_xml.findall('.//w:footnote', ns):
                id_val = fn.get(f'{{{ns["w"]}}}id')
                # Extract text from footnote
                fn_text = ""
                for p in fn.findall('.//w:p', ns):
                    for r in p.findall('.//w:r', ns):
                        t = r.find('.//w:t', ns)
                        if t is not None and t.text:
                            fn_text += t.text
                if fn_text:
                    footnotes_map[id_val] = fn_text
    except Exception as e:
        print(f"Error parsing footnotes: {e}")

    html_output = []
    
    # Keep track of used footnotes to append them in order
    used_footnotes = []

    for para in doc.paragraphs:
        if not para.text.strip():
            continue
            
        style_name = para.style.name.lower()
        tag = 'p'
        
        if 'heading 1' in style_name:
            tag = 'h1'
        elif 'heading 2' in style_name:
            tag = 'h2'
        elif 'heading 3' in style_name:
            tag = 'h3'
        elif 'title' in style_name:
            tag = 'h1'
            
        # Build paragraph inner HTML handling runs for bold/italic and footnote refs
        inner_html = ""
        
        # We need to iterate over the XML children to capture footnote references correctly 
        # because para.runs might not include them strictly in order with xml elements if we just use runs.
        # But for simplicity in this MVP, let's try to detect footnote refs in runs or just use the xml.
        # Iterating XML is Safer for mixed content.
        
        p_element = para._element
        for child in p_element.getchildren():
            if child.tag.endswith('r'): # Run
                run_text = ""
                is_bold = False
                is_italic = False
                
                # Check properties
                rPr = child.find('.//w:rPr', ns)
                if rPr is not None:
                    if rPr.find('.//w:b', ns) is not None:
                        is_bold = True
                    if rPr.find('.//w:i', ns) is not None:
                        is_italic = True
                
                # Get text
                t_elements = child.findall('.//w:t', ns)
                for t in t_elements:
                    if t.text:
                        run_text += t.text
                
                if not run_text:
                    continue
                    
                if is_bold:
                    run_text = f"<strong>{run_text}</strong>"
                if is_italic:
                    run_text = f"<em>{run_text}</em>"
                
                inner_html += run_text
                
            elif child.tag.endswith('rPr'): 
                pass # Property, skip
            elif 'footnoteReference' in child.tag:
                # Found a footnote reference
                fn_id = child.get(f'{{{ns["w"]}}}id')
                if fn_id in footnotes_map:
                    # We create a visual reference
                    note_index = len(used_footnotes) + 1
                    used_footnotes.append(footnotes_map[fn_id])
                    inner_html += f'<sup>[{note_index}]</sup>'

        html_output.append(f"<{tag}>{inner_html}</{tag}>")
    
    # Append styling for footnotes if any
    if used_footnotes:
        html_output.append("<hr class='my-8 border-slate-300' />")
        html_output.append("<div class='footnotes text-sm text-slate-500'>")
        for idx, text in enumerate(used_footnotes):
             html_output.append(f"<p id='fn-{idx+1}'><sup>[{idx+1}]</sup> {text}</p>")
        html_output.append("</div>")
        
    return "".join(html_output)
