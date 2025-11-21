# ---------------------------------------------------------
#  ARTWORK REVIEW MODULE - PHARMA AUDIT REPORT STYLE (B3)
# ---------------------------------------------------------

import fitz           # PyMuPDF
import difflib
import html
import numpy as np
import cv2
from PIL import Image


# -------------------------------
#  Utility: Render small thumbnail
# -------------------------------
def _thumbnail(page, size=(250, 250)):
    pix = page.get_pixmap(alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img = img.resize(size)
    return np.array(img)


# -------------------------------
#  TEXT DIFF (Pharma-ready)
# -------------------------------
def compare_text(std_page, ref_page):
    std = std_page.get_text("text")
    ref = ref_page.get_text("text")

    s_lines = std.splitlines()
    r_lines = ref.splitlines()

    diff = difflib.ndiff(s_lines, r_lines)

    html_lines = []
    for line in diff:
        if line.startswith("- "):
            html_lines.append(f'<div class="del">- {html.escape(line[2:])}</div>')
        elif line.startswith("+ "):
            html_lines.append(f'<div class="add">+ {html.escape(line[2:])}</div>')
        else:
            html_lines.append(f'<div class="eq">{html.escape(line[2:].strip())}</div>')

    return f"""
    <div class="section">
        <h3>1. Text Comparison</h3>
        <div class="section-body diff-block">
            {''.join(html_lines)}
        </div>
    </div>
    """


# -------------------------------
#  FONT ANALYSIS
# -------------------------------
def _fonts(page):
    data = page.get_text("dict")
    fonts = set()

    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                name = span.get("font", "")
                size = int(span.get("size", 0))
                fonts.add((name, size))

    return sorted(fonts)


def compare_fonts(std_page, ref_page):
    std = set(_fonts(std_page))
    ref = set(_fonts(ref_page))

    only_std = std - ref
    only_ref = ref - std

    rows = []
    for name, size in sorted(std):
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{size}</td><td>Standard</td></tr>")
    for name, size in sorted(ref):
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{size}</td><td>Reference</td></tr>")

    summary = ""
    if only_std or only_ref:
        summary += '<div class="warning">Font mismatch detected between Standard and Reference.</div>'
    else:
        summary += '<div class="ok">Fonts appear consistent.</div>'

    return f"""
    <div class="section">
        <h3>2. Font & Typography Comparison</h3>
        {summary}
        <table>
            <tr><th>Font Name</th><th>Size</th><th>Source</th></tr>
            {''.join(rows)}
        </table>
    </div>
    """


# -------------------------------
#  COLOR / GRAPHIC DIFFERENCE
# -------------------------------
def compare_color(std_page, ref_page):
    std_img = _thumbnail(std_page)
    ref_img = _thumbnail(ref_page)

    diff = np.mean(np.abs(std_img.astype("float32") - ref_img.astype("float32")))

    if diff < 5:
        flag = '<div class="ok">No major colour/graphic differences detected.</div>'
    elif diff < 20:
        flag = f'<div class="warning">Minor colour differences detected (Δ ≈ {diff:.1f}).</div>'
    else:
        flag = f'<div class="critical">Significant colour/graphic difference (Δ ≈ {diff:.1f}).</div>'

    return f"""
    <div class="section">
        <h3>3. Colour / Graphic Difference</h3>
        {flag}
        <p class="note">Δ = Mean absolute pixel-based difference. Not a calibrated colour proof.</p>
    </div>
    """


# -------------------------------
#  QR CODE DETECTION
# -------------------------------
def detect_qr(page):
    pix = page.get_pixmap(alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    detector = cv2.QRCodeDetector()
    data, pts, _ = detector.detectAndDecode(arr)

    if data:
        return [data]
    return []


def compare_qr(std_page, ref_page):
    q1 = set(detect_qr(std_page))
    q2 = set(detect_qr(ref_page))

    if not q1 and not q2:
        msg = '<div class="note">No QR codes detected.</div>'
    elif q1 == q2:
        msg = f'<div class="ok">QR codes match: {", ".join(q1)}</div>'
    else:
        msg = f'<div class="critical">QR mismatch!<br>Standard: {q1}<br>Reference: {q2}</div>'

    return f"""
    <div class="section">
        <h3>4. QR / Barcode Verification</h3>
        {msg}
    </div>
    """


# -------------------------------
#  MAIN REPORT BUILDER (B3 style)
# -------------------------------
def run_artwork_review(standard_pdf, reference_pdf):
    std = fitz.open(standard_pdf)
    ref = fitz.open(reference_pdf)

    count = min(len(std), len(ref))

    analysis = []

    for i in range(count):
        analysis.append(f"""
        <div class="page-block">
            <h2>PAGE {i+1}</h2>
            {compare_text(std[i], ref[i])}
            {compare_fonts(std[i], ref[i])}
            {compare_color(std[i], ref[i])}
            {compare_qr(std[i], ref[i])}
        </div>
        """)

    std.close()
    ref.close()

    # Final HTML
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Artwork Review Report</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background: #fafafa;
            }}
            h1 {{
                text-align: center;
                color: #004085;
                border-bottom: 3px solid #004085;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #00345c;
                border-left: 5px solid #00345c;
                padding-left: 10px;
                margin-top: 40px;
            }}
            .page-block {{
                background: #fff;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 6px;
                border: 1px solid #ddd;
                box-shadow: 0 0 5px rgba(0,0,0,0.05);
            }}
            .section {{
                margin-bottom: 25px;
            }}
            .section-body {{
                padding: 10px;
            }}
            .diff-block {{
                font-family: monospace;
                font-size: 13px;
                background: #f9f9f9;
                border: 1px solid #ddd;
                padding: 10px;
            }}
            .add {{ background-color: #d4ffd4; }}
            .del {{ background-color: #ffd4d4; text-decoration: line-through; }}
            .eq  {{ color: #444; }}

            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }}
            th {{
                background: #e9ecef;
                padding: 8px;
                border: 1px solid #ccc;
            }}
            td {{
                padding: 6px;
                border: 1px solid #ddd;
            }}

            .ok {{
                color: #155724;
                background: #d4edda;
                padding: 6px;
                border-left: 5px solid #155724;
                margin-bottom: 8px;
            }}
            .warning {{
                color: #856404;
                background: #fff3cd;
                padding: 6px;
                border-left: 5px solid #856404;
                margin-bottom: 8px;
            }}
            .critical {{
                color: #721c24;
                background: #f8d7da;
                padding: 6px;
                border-left: 5px solid #721c24;
                margin-bottom: 8px;
            }}
            .note {{
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>

    <body>
        <h1>PHARMA ARTWORK COMPARISON REPORT</h1>
        <p><b>Standard:</b> {html.escape(standard_pdf.split('/')[-1])}<br>
           <b>Reference:</b> {html.escape(reference_pdf.split('/')[-1])}
        </p>
        {''.join(analysis)}
    </body>
    </html>
    """

    return html_report
