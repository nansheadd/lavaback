from docx import Document
import io
import zipfile
from lxml import etree

async def parse_docx(file) -> str:
    """
    Parses a DOCX file and converts it to HTML.
    Handles headings, paragraphs, bold, italic, footnotes, and endnotes.
    """
    content = await file.read()
    doc_bytes = io.BytesIO(content)
    doc = Document(doc_bytes)
    
    # Reset stream for zipfile access
    doc_bytes.seek(0)
    
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    # Extract footnotes and endnotes using zipfile (more reliable)
    notes_map = {}  # id -> text
    
    try:
        with zipfile.ZipFile(doc_bytes, 'r') as zf:
            # Check for footnotes.xml
            if 'word/footnotes.xml' in zf.namelist():
                with zf.open('word/footnotes.xml') as f:
                    footnotes_xml = etree.parse(f)
                    root = footnotes_xml.getroot()
                    for footnote in root.findall('.//w:footnote', ns):
                        id_val = footnote.get(f'{{{ns["w"]}}}id')
                        # Skip separator/continuation (id 0 and -1)
                        if id_val in ['0', '-1']:
                            continue
                        note_text = _extract_text_from_note(footnote, ns)
                        if note_text:
                            notes_map[id_val] = note_text
            
            # Check for endnotes.xml
            if 'word/endnotes.xml' in zf.namelist():
                with zf.open('word/endnotes.xml') as f:
                    endnotes_xml = etree.parse(f)
                    root = endnotes_xml.getroot()
                    for endnote in root.findall('.//w:endnote', ns):
                        id_val = endnote.get(f'{{{ns["w"]}}}id')
                        # Skip separator/continuation (id 0 and -1)
                        if id_val in ['0', '-1']:
                            continue
                        note_text = _extract_text_from_note(endnote, ns)
                        if note_text:
                            notes_map[id_val] = note_text
    except Exception as e:
        print(f"Error parsing notes: {e}")

    html_output = []
    used_notes = []  # List of (id, text) tuples in order of appearance

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
            
        # Build paragraph inner HTML
        inner_html = ""
        
        p_element = para._element
        for child in p_element.iter():
            # Handle text runs
            if child.tag.endswith('}r'):
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
                
                # Get text elements directly under run
                for subchild in child:
                    if subchild.tag.endswith('}t') and subchild.text:
                        run_text += subchild.text
                
                if run_text:
                    if is_bold:
                        run_text = f"<strong>{run_text}</strong>"
                    if is_italic:
                        run_text = f"<em>{run_text}</em>"
                    inner_html += run_text
            
            # Handle footnote/endnote references
            if 'footnoteReference' in child.tag or 'endnoteReference' in child.tag:
                fn_id = child.get(f'{{{ns["w"]}}}id')
                if fn_id and fn_id in notes_map:
                    # Add to used notes in order
                    note_index = len(used_notes) + 1
                    used_notes.append((fn_id, notes_map[fn_id]))
                    inner_html += f'<sup class="footnote-ref"><a href="#fn-{note_index}" id="fnref-{note_index}">[{note_index}]</a></sup>'

        if inner_html:
            html_output.append(f"<{tag}>{inner_html}</{tag}>")
    
    # Append notes section if any
    if used_notes:
        # Use inline styles to ensure it renders even if Tailwind classes are purged or not applied to dynamic content
        html_output.append('<hr class="footnotes-divider" style="margin-top: 2rem; margin-bottom: 2rem; border-top: 2px solid #cbd5e1;" />')
        html_output.append('<section class="footnotes-section" style="margin-top: 1.5rem; padding-top: 1rem;">')
        html_output.append('<h4 style="font-size: 0.875rem; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem;">Notes de bas de page</h4>')
        html_output.append('<ol class="footnotes-list" style="font-size: 0.875rem; color: #475569; list-style-type: decimal; list-style-position: inside; padding-left: 1rem;">')
        for idx, (_, text) in enumerate(used_notes):
            html_output.append(f'<li id="fn-{idx+1}" class="footnote-item" style="margin-bottom: 0.5rem;"><span class="footnote-text">{text}</span> <a href="#fnref-{idx+1}" class="footnote-backref" style="color: #4f46e5; text-decoration: none; margin-left: 0.25rem;">↩</a></li>')
        html_output.append('</ol>')
        html_output.append('</section>')
        
    return "".join(html_output)


def _extract_text_from_note(note_element, ns):
    """Extract plain text from a footnote or endnote element."""
    note_text = ""
    for p in note_element.findall('.//w:p', ns):
        for r in p.findall('.//w:r', ns):
            t = r.find('.//w:t', ns)
            if t is not None and t.text:
                note_text += t.text
    return note_text
