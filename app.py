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
    tanggal_only = st.date_input("Tanggal", datetime.now().date())
    waktu_only = st.time_input("Waktu", datetime.now().time())
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")

with col2:
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

# gabungkan menjadi datetime
tanggal = datetime.combine(tanggal_only, waktu_only)

# ========================
# VALIDASI HEADER SEBELUM UPLOAD
# ========================
st.header("Upload Excel / CSV Data")

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
    uploaded_file = st.file_uploader("Pilih file (Excel / CSV)", type=["xlsx", "xls", "csv"])


# ========================
# VALIDASI FILE
# ========================
def validate_excel_file(df):
    required_columns = ["KOLI QTY"]
    errors = []

    if df.empty:
        errors.append("File kosong. Silakan upload file dengan data.")
        return False, errors

    # cek kolom wajib
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        errors.append(f"Kolom yang diperlukan tidak ditemukan: {', '.join(missing_columns)}")

    # cek nilai numerik
    if "KOLI QTY" in df.columns:
        if not all(df["KOLI QTY"].apply(lambda x: isinstance(x, (int, float)) or str(x).replace(".", "", 1).isdigit())):
            errors.append("Kolom 'KOLI QTY' harus berisi angka")

    return len(errors) == 0, errors


# ========================
# CANVAS PAGINATION FIX
# ========================
from reportlab.pdfgen.canvas import Canvas

class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        self._total_pages = 0
        super().__init__(*args, **kwargs)

    def showPage(self):
        self._total_pages += 1
        super().showPage()

    def save(self):
        """Hitung total halaman lalu render ulang"""
        total_pages = self._total_pages
        self._pageNumber = 0

        super().saveState()
        self._startPage()

        for page in range(1, total_pages + 1):
            self.setPageSize(A4)
            self.draw_page_number(page, total_pages)
            super().showPage()

        super().restoreState()
        super().save()

    def draw_page_number(self, page, total):
        page_text = f"{page}/{total}"
        self.setFont("Helvetica", 9)
        self.drawString(A4[0] - 80, 0.5 * inch, page_text)


# ========================
# GENERATE PDF
# ========================
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # ========================
    # JUDUL
    # ========================
    elements.append(Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    # ========================
    # HEADER KIRI
    # ========================
    header_left = f"""
    <b>Tanggal:</b> {tanggal.strftime('%d/%m/%Y %H:%M')}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier Name:</b> {courier}<br/>
    <b>Driver Name:</b> {driver}<br/>
    <b>Police Number:</b> {police}<br/>
    """

    # ========================
    # TOTAL KOLI BOX (36px)
    # ========================
    koli_style = ParagraphStyle(
        "KoliStyle",
        parent=styles["Normal"],
        alignment=1,
        fontSize=36,
        leading=40
    )
    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        alignment=1,
        fontSize=16
    )

    total_koli_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", koli_style)]
        ],
        colWidths=[140]
    )

    total_koli_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ]))

    header_table = Table([[Paragraph(header_left, styles["Normal"]), total_koli_box]],
                         colWidths=[350, 150])
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # ========================
    # TABEL DATA
    # ========================
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

    # ========================
    # TANDA TANGAN
    # ========================
    signature_table = Table(
        [
            ["Diperiksa oleh", "Diserahkan oleh", "Diterima oleh"],
            ["", "", ""], ["", "", ""], ["", "", ""],
            ["__________________", "__________________", "__________________"],
            ["(Security WH)", "( Dispatcher WH )", "( Driver Courier )"],
        ],
        colWidths=[180, 180, 180],
    )

    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
    ]))

    elements.append(signature_table)

    pdf.build(elements, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer


# ========================
# PROSES FILE
# ========================
if uploaded_file:

    # baca file → bisa Excel atau CSV
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    is_valid, errors = validate_excel_file(df)

    if not is_valid:
        st.error("❌ Validasi gagal:")
        for err in errors:
            st.error("• " + err)
    else:
        total_koli = int(df["KOLI QTY"].sum())

        st.success("✅ File valid!")
        st.dataframe(df, use_container_width=True)

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
    st.info("💡 Upload file setelah mengisi header.")
