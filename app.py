import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

st.set_page_config(page_title="BAST Generator", layout="wide")

st.title("📦 Berita Acara Serah Terima (BAST) Generator")

# ========================
# INPUT HEADER
# ========================
st.header("Input Data Header")

col1, col2 = st.columns(2)

with col1:
    date_input = st.date_input("Tanggal", datetime.now().date())
    time_input = st.time_input("Waktu", datetime.now().time())
    tanggal = datetime.combine(date_input, time_input)
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")

with col2:
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

# ========================
# VALIDASI HEADER SEBELUM UPLOAD
# ========================
st.header("Upload Excel Data")

header_fields = {
    "Warehouse": warehouse,
    "Courier Name": courier,
    "Driver Name": driver,
    "Police Number": police
}

missing_fields = [field for field, value in header_fields.items() if not value.strip()]

if missing_fields:
    st.warning(f"⚠️ Silakan isi semua data header terlebih dahulu: {', '.join(missing_fields)}")
    uploaded_file = None
else:
    uploaded_file = st.file_uploader("Pilih file Excel", type=["xlsx", "xls", "csv"])


# ========================
# VALIDASI FILE EXCEL
# ========================
def validate_excel_file(df):
    required_columns = ["KOLI QTY"]
    errors = []

    if df.empty:
        errors.append("File Excel kosong. Silakan upload file dengan data.")
        return False, errors

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Kolom yang diperlukan tidak ditemukan: {', '.join(missing_columns)}")

    if not all(
        df["KOLI QTY"].apply(lambda x: isinstance(x, (int, float)) or str(x).replace(".", "", 1).isdigit())
    ):
        errors.append("Kolom 'KOLI QTY' harus berisi nilai numerik")

    return len(errors) == 0, errors


# ========================
# GENERATE PDF
# ========================
class NumberedCanvas:
    def __init__(self, total_pages=1):
        self.page_num = 0
        self.total_pages = total_pages
        
    def add_page_number(self, canvas, doc):
        self.page_num += 1
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        page_text = f"{self.page_num}/{self.total_pages}"
        canvas.drawString(A4[0] - 80, 0.5 * inch, page_text)
        canvas.restoreState()


def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # PERKIRAAN JUMLAH HALAMAN
    estimated_pages = max(1, (len(df) // 20) + 1)

    # JUDUL
    elements.append(Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    # HEADER KIRI
    header_left = f"""
        <b>Tanggal:</b> {tanggal.strftime("%d/%m/%Y %H:%M")}<br/>
        <b>Warehouse:</b> {warehouse}<br/>
        <b>Courier Name:</b> {courier}<br/>
        <b>Driver Name:</b> {driver}<br/>
        <b>Police Number:</b> {police}<br/>
    """

    # STYLE TOTAL KOLI
    koli_style = ParagraphStyle(
        "KoliStyle", parent=styles["Normal"],
        alignment=1, fontSize=36, leading=40
    )
    label_style = ParagraphStyle(
        "LabelStyle", parent=styles["Normal"],
        alignment=1, fontSize=20
    )

    total_koli_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", koli_style)]
        ],
        colWidths=[120]
    )

    total_koli_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ]))

    header_table = Table(
        [[Paragraph(header_left, styles["Normal"]), total_koli_box]],
        colWidths=[350, 150]
    )

    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # TABEL DATA
    table_data = [list(df.columns)] + df.values.tolist()
    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # TANDA TANGAN
    signature_table = Table(
        [
            ["Diperiksa oleh", "Diserahkan oleh", "Diterima oleh"],
            ["", "", ""], ["", "", ""], ["", "", ""],
            ["__________________", "__________________", "__________________"],
        ],
        colWidths=[180, 180, 180],
    )

    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("TOPPADDING", (0, 1), (-1, 1), 20),
    ]))

    elements.append(signature_table)

    canvas = NumberedCanvas(total_pages=estimated_pages)
    pdf.build(elements, onFirstPage=canvas.add_page_number, onLaterPages=canvas.add_page_number)

    buffer.seek(0)
    return buffer


# ========================
# PROSES FILE UPLOADED
# ========================
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    is_valid, validation_errors = validate_excel_file(df)

    if not is_valid:
        st.error("❌ Validasi File Gagal:")
        for error in validation_errors:
            st.error(f"  • {error}")
    else:
        total_koli = int(df["KOLI QTY"].sum()) if "KOLI QTY" in df.columns else "N/A"

        st.success("✅ File berhasil dibaca dan valid!")
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.header("📄 Hasil BAST")

        pdf_buffer = generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli)

        filename = f"{warehouse}_{courier}_{police}_{tanggal.strftime('%Y%m%d_%H%M%S')}.pdf"

        st.download_button(
            label="📥 Download PDF BAST",
            data=pdf_buffer,
            file_name=filename,
            mime="application/pdf"
        )

else:
    st.info("💡 Silakan upload file Excel terlebih dahulu (setelah mengisi header).")
