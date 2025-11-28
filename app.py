import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import io

st.set_page_config(page_title="BAST Generator", layout="wide")
st.title("📦 Berita Acara Serah Terima (BAST) Generator")

# -----------------------
# Input header
# -----------------------
st.header("Input Data Header")
col1, col2 = st.columns(2)

with col1:
    tanggal_only = st.date_input("Tanggal", datetime.now().date())
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")

with col2:
    waktu_only = st.time_input("Waktu", datetime.now().time())
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

# gabungkan tanggal + waktu
tanggal = datetime.combine(tanggal_only, waktu_only)

# -----------------------
# Validasi header sebelum upload
# -----------------------
st.header("Upload Excel / CSV Data")

header_fields = {
    "Warehouse": warehouse,
    "Courier Name": courier,
    "Driver Name": driver,
    "Police Number": police
}

missing_fields = [field for field, value in header_fields.items() if not str(value).strip()]

if missing_fields:
    st.warning(f"⚠️ Silakan isi semua data header terlebih dahulu: {', '.join(missing_fields)}")
    uploaded_file = None
else:
    uploaded_file = st.file_uploader("Pilih file (Excel / CSV)", type=["xlsx", "xls", "csv"])

# -----------------------
# Validasi isi file
# -----------------------
def validate_excel_file(df):
    required_columns = ["KOLI QTY"]
    errors = []

    if df is None or df.empty:
        errors.append("File kosong. Silakan upload file dengan data.")
        return False, errors

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Kolom wajib tidak ditemukan: {', '.join(missing_columns)}")

    if "KOLI QTY" in df.columns:
        if not all(df["KOLI QTY"].apply(lambda x: isinstance(x, (int, float)) or str(x).replace(".", "", 1).isdigit())):
            errors.append("Kolom 'KOLI QTY' harus berisi angka")

    return len(errors) == 0, errors

# -----------------------
# NumberedCanvas (stable, saves page states then writes page numbers)
# -----------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # store page state dicts
        self._saved_page_states = []

    def showPage(self):
        # Save a copy of the canvas state for each page, then start a fresh page
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page numbers to each saved page state and write them out."""
        num_pages = len(self._saved_page_states)
        if num_pages == 0:
            # no pages created
            return super().save()

        for state in self._saved_page_states:
            self.__dict__.update(state)  # restore page state
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, total_pages):
        page_num = self.getPageNumber()
        text = f"{page_num}/{total_pages}"
        self.setFont("Helvetica", 9)
        # draw on the bottom-right (40 pts from right, 0.5 inch from bottom)
        self.drawRightString(A4[0] - 40, 0.5 * inch, text)

# -----------------------
# Generate PDF function
# -----------------------
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    # Header left (info)
    header_left = f"""
    <b>Tanggal:</b> {tanggal.strftime('%d/%m/%Y %H:%M')}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier Name:</b> {courier}<br/>
    <b>Driver Name:</b> {driver}<br/>
    <b>Police Number:</b> {police}<br/>
    """

    # TOTAL KOLI style (36px)
    koli_style = ParagraphStyle("KoliStyle", parent=styles["Normal"], alignment=1, fontSize=36, leading=40)
    label_style = ParagraphStyle("LabelStyle", parent=styles["Normal"], alignment=1, fontSize=16)

    total_koli_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", koli_style)]
        ],
        colWidths=[140]
    )
    total_koli_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    header_table = Table([[Paragraph(header_left, styles["Normal"]), total_koli_box]], colWidths=[350, 150])
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Table data
    # Convert any NaN to empty string for clean PDF
    df_clean = df.fillna("")
    table_data = [list(df_clean.columns)] + df_clean.values.tolist()
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Signature block
    signature_table = Table(
        [
            ["Diperiksa oleh", "Diserahkan oleh", "Diterima oleh"],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
            ["__________________", "__________________", "__________________"],
            ["(Security WH)", "( Dispatcher WH )", "( Driver Courier )"],
        ],
        colWidths=[180, 180, 180]
    )
    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(signature_table)

    # Build PDF with canvasmaker NumberedCanvas (it will collect pages and write page numbers)
    doc.build(elements, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer

# -----------------------
# Handle uploaded file
# -----------------------
if uploaded_file:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            # read excel (first sheet)
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ Gagal membaca file: {e}")
        st.stop()

    is_valid, errors = validate_excel_file(df)
    if not is_valid:
        st.error("❌ Validasi gagal:")
        for err in errors:
            st.error("• " + err)
    else:
        # compute total koli from column
        try:
            total_koli = int(pd.to_numeric(df["KOLI QTY"], errors="coerce").fillna(0).sum())
        except Exception:
            total_koli = "N/A"

        st.success("✅ File valid!")
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.header("📄 Hasil BAST")

        if st.button("Generate PDF"):
            try:
                pdf_buffer = generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli)
                filename = f"{warehouse}_{courier}_{police}_{tanggal.strftime('%Y%m%d_%H%M%S')}.pdf"
                st.download_button(
                    label="📥 Download PDF BAST",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"❌ Gagal generate PDF: {e}")
else:
    st.info("💡 Silakan upload file setelah mengisi header.")
