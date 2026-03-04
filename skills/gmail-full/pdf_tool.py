#!/usr/bin/env python3
"""PDF generator for OpenClaw — clean formatting."""
import sys, json, os
from fpdf import FPDF
from datetime import datetime
from zoneinfo import ZoneInfo

OUTPUT_DIR = '/home/YOUR_USERNAME/files'

class JarvisPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f'Jarvis Report | {datetime.now(ZoneInfo("America/New_York")).strftime("%B %d, %Y")}', align='R')
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf(title, content, filename=None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not filename:
        filename = title.lower().replace(' ', '_').replace('/', '_') + '.pdf'
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    pdf = JarvisPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    
    # Title
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.ln(4)
    
    # Content
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(50, 50, 50)
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        
        # Section headers (lines starting with ## or ALL CAPS)
        if line.startswith('## ') or line.startswith('### '):
            pdf.ln(4)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 8, line.lstrip('#').strip(), new_x="LMARGIN", new_y="NEXT")
            pdf.set_draw_color(220, 220, 220)
            pdf.line(10, pdf.get_y(), 120, pdf.get_y())
            pdf.ln(3)
            pdf.set_font('Helvetica', '', 11)
            pdf.set_text_color(50, 50, 50)
        
        # Bullet points
        elif line.startswith('- ') or line.startswith('* ') or line.startswith('• '):
            pdf.set_x(15)
            pdf.cell(5, 6, chr(8226))
            pdf.multi_cell(170, 6, line[2:].strip())
            pdf.ln(1)
        
        # Bold lines (wrapped in **)
        elif line.startswith('**') and line.endswith('**'):
            pdf.set_font('Helvetica', 'B', 11)
            pdf.multi_cell(0, 6, line.strip('*').strip())
            pdf.set_font('Helvetica', '', 11)
        
        # Table-like lines (contains |)
        elif '|' in line and line.count('|') >= 2:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if parts:
                col_width = 180 / len(parts)
                for p in parts:
                    pdf.cell(col_width, 7, p, border=1)
                pdf.ln()
        
        # Regular text
        else:
            pdf.multi_cell(0, 6, line)
            pdf.ln(1)
    
    pdf.output(filepath)
    size = os.path.getsize(filepath)
    print(json.dumps({"status": "pdf_created", "path": filepath, "title": title, "size_bytes": size}))

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: pdf_tool.py <title> <content> [filename]")
        sys.exit(1)
    title = sys.argv[1]
    content = sys.argv[2]
    filename = sys.argv[3] if len(sys.argv) > 3 else None
    generate_pdf(title, content, filename)
