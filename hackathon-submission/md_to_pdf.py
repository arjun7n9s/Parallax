"""Convert SOLUTION_APPROACH.md to a properly formatted PDF.

Produces a styled PDF that mirrors the docx layout. Uses fpdf2 (pure Python, no Word/GTK needed).

Output: SOLUTION_APPROACH.pdf
"""
import re
from pathlib import Path
from fpdf import FPDF


class HackathonPDF(FPDF):
    def __init__(self):
        super().__init__()
        # Register Unicode TrueType fonts (Windows system fonts).
        # Cannot use 'Helvetica' or 'Courier' as family names — those are
        # built-in core fonts in fpdf2 and cannot be overridden.
        self.add_font('Body', '', r'C:\Windows\Fonts\arial.ttf', uni=True)
        self.add_font('Body', 'B', r'C:\Windows\Fonts\arialbd.ttf', uni=True)
        self.add_font('Body', 'I', r'C:\Windows\Fonts\ariali.ttf', uni=True)
        self.add_font('Body', 'BI', r'C:\Windows\Fonts\arialbi.ttf', uni=True)
        self.add_font('Mono', '', r'C:\Windows\Fonts\consola.ttf', uni=True)
        self.add_font('Mono', 'B', r'C:\Windows\Fonts\consolab.ttf', uni=True)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(left=20, top=20, right=20)
        self.add_page()
        self.cover_done = False

    def header(self):
        # Top-right small marker
        self.set_y(8)
        self.set_font('Body', 'I', 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 5, 'PARALLAX  -  Solution Approach', align='R')
        self.ln(8)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font('Body', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def write_inline(self, text, size=11, style=''):
        """Parse **bold**, *italic*, `code` and add as styled runs."""
        pattern = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')
        parts = pattern.split(text)
        for part in parts:
            if not part:
                continue
            if part.startswith('**') and part.endswith('**'):
                self.set_font('Body', 'B', size)
                self.write(6, part[2:-2])
            elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                self.set_font('Body', 'I', size)
                self.write(6, part[1:-1])
            elif part.startswith('`') and part.endswith('`'):
                self.set_font('Mono', '', size - 1)
                self.write(6, part[1:-1])
            else:
                self.set_font('Body', style, size)
                self.write(6, part)
        self.set_font('Body', '', size)

    def h1(self, text):
        self.ln(6)
        self.set_font('Body', 'B', 22)
        self.set_text_color(15, 23, 42)
        self.write(10, text)
        self.ln(10)
        # Underline rule
        y = self.get_y()
        self.set_draw_color(15, 23, 42)
        self.set_line_width(0.6)
        self.line(20, y, self.w - 20, y)
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def h2(self, text):
        self.ln(6)
        self.set_font('Body', 'B', 15)
        self.set_text_color(15, 23, 42)
        self.write(8, text)
        self.ln(8)
        self.set_text_color(0, 0, 0)
        self.set_font('Body', '', 11)

    def h3(self, text):
        self.ln(4)
        self.set_font('Body', 'B', 12)
        self.set_text_color(51, 65, 85)
        self.write(6, text)
        self.ln(6)
        self.set_text_color(0, 0, 0)
        self.set_font('Body', '', 11)

    def h4(self, text):
        self.ln(3)
        self.set_font('Body', 'BI', 11)
        self.set_text_color(51, 65, 85)
        self.write(5, text)
        self.ln(5)
        self.set_text_color(0, 0, 0)
        self.set_font('Body', '', 11)

    def para(self, text):
        self.set_font('Body', '', 11)
        self.write_inline(text, size=11)
        self.ln(7)

    def bullet(self, text, level=0):
        indent = '    ' * level + chr(0x2022) + '  '
        self.set_font('Body', '', 11)
        self.write(6, indent)
        self.write_inline(text, size=11)
        self.ln(6)

    def numbered(self, text, n, level=0):
        indent = '    ' * level + f'{n}. '
        self.set_font('Body', '', 11)
        self.write(6, indent)
        self.write_inline(text, size=11)
        self.ln(6)

    def code_block(self, code):
        self.set_font('Mono', '', 9)
        self.set_text_color(30, 41, 59)
        self.set_fill_color(241, 245, 249)
        x, y, w = self.get_x(), self.get_y(), self.w - 40
        # Approximate height: 4.5pt per line + padding
        n_lines = code.count('\n') + 1
        h = n_lines * 4.5 + 6
        if y + h > self.h - 18:
            self.add_page()
            y = self.get_y()
        self.rect(x, y, w, h, style='F')
        self.set_xy(x + 3, y + 3)
        for line in code.split('\n'):
            self.cell(0, 4.5, line if line else ' ', new_x='LMARGIN', new_y='NEXT')
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def add_image(self, path, caption):
        """Embed a PNG image with a centered caption below.

        The image is scaled to fit within the page margins while preserving
        aspect ratio. The caption is rendered in small italic gray below the
        image, centered on the page.
        """
        import os
        if not os.path.exists(path):
            # Fallback: just show the caption
            self.set_font('Body', 'I', 9)
            self.set_text_color(100, 116, 139)
            self.ln(2)
            self.cell(0, 5, f'[image missing: {path}] {caption}', new_x='LMARGIN', new_y='NEXT', align='C')
            self.ln(2)
            return

        # Read PNG header to get dimensions without external deps
        # PNG: 8-byte signature, then IHDR chunk
        # IHDR is at offset 8, then 4 bytes length, 4 bytes "IHDR", then width(4) height(4)
        with open(path, 'rb') as f:
            f.read(16)  # skip signature + IHDR length + "IHDR"
            import struct
            w_px, h_px = struct.unpack('>II', f.read(8))

        # Available area: page width minus margins, with some padding
        max_w = self.w - 40  # 20 left + 20 right margin
        max_h = 145  # cap image height — leaves room for caption + footer

        # Scale to fit
        aspect = h_px / w_px
        if max_w * aspect <= max_h:
            img_w = max_w
            img_h = max_w * aspect
        else:
            img_h = max_h
            img_w = max_h / aspect

        # Center horizontally
        x = (self.w - img_w) / 2
        y = self.get_y()

        # Page break check — be conservative to avoid bleeding into footer
        needed = img_h + 18  # image + caption + breathing room
        if y + needed > self.h - 22:
            self.add_page()
            y = self.get_y()

        # Draw a thin border around the image
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        # Insert the actual image
        try:
            self.image(path, x, y, img_w, img_h)
        except Exception as e:
            # If image() fails (some fpdf2 + Pillow version issues), show caption
            self.set_font('Body', 'I', 9)
            self.set_text_color(100, 116, 139)
            self.cell(0, 5, f'[image render failed: {path}] {caption}', new_x='LMARGIN', new_y='NEXT', align='C')
            self.ln(2)
            return
        # Border
        self.rect(x, y, img_w, img_h)

        # Move cursor below image
        self.set_xy(self.l_margin, y + img_h + 2)

        # Caption: small italic gray
        self.set_font('Body', 'I', 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, caption, new_x='LMARGIN', new_y='NEXT', align='C')
        self.ln(4)

        # Reset for next element
        self.set_text_color(30, 41, 59)

    def rule(self):
        y = self.get_y() + 2
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.3)
        self.line(20, y, self.w - 20, y)
        self.ln(8)

    def add_table(self, rows):
        """Render a markdown table as a proper bordered Word-style table.

        Strategy: compute column widths and row heights up-front, then
        render each row with explicit cursor positioning, draw the cell
        borders as full rect() calls so borders connect cleanly.
        """
        if not rows:
            return
        n_cols = max(len(r) for r in rows)
        usable_w = self.w - 40  # 20mm margins on each side
        col_w = usable_w / n_cols

        # Phase 1: compute wrapped text for every cell, and per-row height
        def wrap_cell(text, width, font_size):
            self.set_font('Body', '', font_size)
            words = text.split()
            lines = []
            cur = ''
            for w in words:
                test = (cur + ' ' + w).strip()
                if self.get_string_width(test) < width - 3:
                    cur = test
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            if not lines:
                lines = ['']
            return lines

        # Wrap all cells; row height = max lines in row * line_h + padding
        all_wrapped = []
        for i, row in enumerate(rows):
            font_size = 9
            row_cells = []
            for j in range(n_cols):
                cell = row[j] if j < len(row) else ''
                row_cells.append(wrap_cell(cell, col_w, font_size))
            all_wrapped.append(row_cells)

        line_h = 4.5
        pad = 2.0
        row_heights = []
        for i, row_cells in enumerate(all_wrapped):
            n_lines = max(len(c) for c in row_cells)
            row_heights.append(n_lines * line_h + 2 * pad)

        # Phase 2: render rows. Always start at the LEFT margin.
        # If a page break happens mid-table, repeat the header row.
        x_left = 20  # left margin
        for i, row_cells in enumerate(all_wrapped):
            is_header = (i == 0)

            # Page-break check: if header won't fit OR a tall body row won't
            # fit, break to a new page. Always re-emit the header on the new
            # page so the reader can see the column names.
            y = self.get_y()
            if y + row_heights[i] > self.h - 18:
                self.add_page()
                if not is_header:
                    # Re-emit the header row on the new page
                    y = self.get_y()
                    self.set_fill_color(226, 232, 240)
                    self.set_draw_color(180, 180, 180)
                    self.set_line_width(0.2)
                    for j in range(n_cols):
                        x = x_left + j * col_w
                        self.rect(x, y, col_w, row_heights[0], style='F')
                        self.rect(x, y, col_w, row_heights[0])
                        self.set_font('Body', 'B', 9)
                        self.set_text_color(15, 23, 42)
                        cell_lines = all_wrapped[0][j]
                        for k, ln in enumerate(cell_lines):
                            line_y = y + pad + k * line_h
                            self.set_xy(x + 2, line_y - 1)
                            self.cell(col_w - 4, line_h, ln, border=0, align='L')
                    # Move cursor below the re-emitted header
                    self.set_xy(x_left, y + row_heights[0])
                    y = self.get_y()

            y = self.get_y()

            # Fill + border style
            if is_header:
                self.set_fill_color(226, 232, 240)  # slate-200
            else:
                self.set_fill_color(255, 255, 255)
            self.set_draw_color(180, 180, 180)
            self.set_line_width(0.2)

            for j in range(n_cols):
                x = x_left + j * col_w
                # Draw filled rectangle
                self.rect(x, y, col_w, row_heights[i], style='F')
                # Draw cell border
                self.rect(x, y, col_w, row_heights[i])

                # Render text
                if is_header:
                    self.set_font('Body', 'B', 9)
                    self.set_text_color(15, 23, 42)
                else:
                    self.set_font('Body', '', 9)
                    self.set_text_color(0, 0, 0)

                cell_lines = row_cells[j]
                for k, ln in enumerate(cell_lines):
                    line_y = y + pad + k * line_h
                    self.set_xy(x + 2, line_y - 1)
                    self.cell(col_w - 4, line_h, ln, border=0, align='L')

            # Move cursor to start of next row
            self.set_xy(x_left, y + row_heights[i])
        self.ln(2)
        self.set_text_color(0, 0, 0)


def parse_md_table(lines, idx):
    table_lines = []
    i = idx
    while i < len(lines) and lines[i].strip().startswith('|'):
        table_lines.append(lines[i])
        i += 1
    if len(table_lines) < 2:
        return None, idx
    header_cells = [c.strip() for c in table_lines[0].strip('|').split('|')]
    body_lines = table_lines[2:]
    rows = [header_cells]
    for bl in body_lines:
        cells = [c.strip() for c in bl.strip('|').split('|')]
        rows.append(cells)
    return rows, i


def main():
    md_path = Path(r"C:/Users/arjun/Desktop/PSBs/GenAI-Cybersec-hackathon/hackathon-submission/SOLUTION_APPROACH.md")
    pdf_path = Path(r"C:/Users/arjun/Desktop/PSBs/GenAI-Cybersec-hackathon/hackathon-submission/SOLUTION_APPROACH.pdf")

    md_text = md_path.read_text(encoding='utf-8')
    lines = md_text.split('\n')

    pdf = HackathonPDF()
    pdf.set_title('PARALLAX - Solution Approach')
    pdf.set_author('PARALLAX Team')

    i = 0
    in_code = False
    code_buf = []
    numbered_counters = {}  # track numbering per indent level

    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if s.startswith('```'):
            if in_code:
                pdf.code_block('\n'.join(code_buf))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Image embed: ![alt](relative/path.png)
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', s)
        if img_match:
            alt_text = img_match.group(1)
            rel_path = img_match.group(2)
            # Resolve relative to the markdown file's directory
            img_path = (md_path.parent / rel_path).resolve()
            pdf.add_image(str(img_path), alt_text)
            i += 1
            continue

        if s.startswith('# '):
            pdf.h1(s[2:])
        elif s.startswith('## '):
            pdf.h2(s[3:])
            numbered_counters = {0: 0}
        elif s.startswith('### '):
            pdf.h3(s[4:])
            numbered_counters[1] = 0
        elif s.startswith('#### '):
            pdf.h4(s[5:])
        elif s == '---':
            pdf.rule()
        elif s.startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s\-:|]+\|\s*$', lines[i + 1]):
            rows, end_idx = parse_md_table(lines, i)
            if rows:
                pdf.add_table(rows)
                i = end_idx
                continue
        elif re.match(r'^\s*\d+\.\s+', line):
            indent = (len(line) - len(line.lstrip())) // 2
            numbered_counters.setdefault(indent, 0)
            numbered_counters[indent] += 1
            text = re.sub(r'^\s*\d+\.\s+', '', line)
            pdf.numbered(text, numbered_counters[indent], level=indent // 2)
        elif re.match(r'^\s*[-*]\s+', line):
            indent = (len(line) - len(line.lstrip())) // 2
            text = re.sub(r'^\s*[-*]\s+', '', line)
            pdf.bullet(text, level=indent)
        elif not s:
            pdf.ln(2)
        else:
            pdf.para(line)

        i += 1

    pdf.output(str(pdf_path))
    print(f"Wrote: {pdf_path}")
    print(f"Size: {pdf_path.stat().st_size:,} bytes")
    print(f"Pages: {pdf.page_no()}")


if __name__ == '__main__':
    main()
