"""Generate sample FNOL PDFs from the txt files in sample-documents/."""

from pathlib import Path

try:
    from fpdf import FPDF
except ImportError:
    print("Install fpdf2: pip install fpdf2")
    raise

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "sample-documents"


def txt_to_pdf(txt_path: Path) -> None:
    text = txt_path.read_text(encoding="utf-8")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    for line in text.splitlines():
        safe = line.encode("latin-1", errors="replace").decode("latin-1")
        if not safe.strip():
            pdf.ln(3)
            continue
        pdf.cell(0, 5, safe, new_x="LMARGIN", new_y="NEXT")
    pdf_path = txt_path.with_suffix(".pdf")
    pdf.output(str(pdf_path))
    print(f"Created {pdf_path.name}")


if __name__ == "__main__":
    for txt in SAMPLES_DIR.glob("*.txt"):
        txt_to_pdf(txt)
