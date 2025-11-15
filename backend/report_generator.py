# backend/report_generator.py
from fpdf import FPDF
import textwrap
import os

def generate_review_pdf(pdf_path: str, repo: str, number: int, ai_review: str, diff_text: str):
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, txt="AI DevSecOps — PR/MR Review", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", size=11)
    pdf.cell(0, 6, txt=f"Repository / Project: {repo}", ln=True)
    pdf.cell(0, 6, txt=f"PR/MR #: {number}", ln=True)
    pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, txt="AI Review Summary:", ln=True)
    pdf.ln(3)

    pdf.set_font("Arial", size=10)
    for line in textwrap.wrap(ai_review, width=95):
        pdf.multi_cell(0, 5, line)
    pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, txt="Diff Snapshot (truncated):", ln=True)
    pdf.ln(3)

    pdf.set_font("Courier", size=8)
    snippet = diff_text[:4000]
    for line in snippet.splitlines():
        safe = line.replace("\x00","")
        pdf.multi_cell(0, 4, safe)

    pdf.output(pdf_path)
    return pdf_path
