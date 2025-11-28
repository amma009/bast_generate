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
    waktu_only = st.time_input("Waktu (pilih manual)", value=None)
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

# Combine datetime
def combine_datetime(d, t):
    if t is None:
        return None
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)

tanggal = combine_datetime(tanggal_only, waktu_only)

# -----------------------
# Validasi header sebelum upload
# -----------------------
st.header("Upload Excel / CSV Data")

header_fields = {
    "Warehouse": warehouse,
    "Courier Name": courier,
    "Driver Name": driver,
    "Police Number": police,
}

missing_fields = [x for x, v in header_fields.items() if not str(v).strip()]
if waktu_only is None:
    missing_fields.append("Waktu")

if missing_fields:
    st.warning(f"⚠️ Lengkapi dulu: {', '.join(missing_fields)}")
    uploaded_file = None
else:
    uploaded_file = st.file_uploader("Upload file (Excel / CSV)", type=["xlsx", "xls", "csv"])

# -----------------------
# Validasi file
# -----------------------
def validate_excel_file(df):
    if df is None or df.empty:
        return False, ["File kosong"]

    if "KOLI QTY" not in df.columns:
        return False, ["Kolom 'KOLI QTY' wajib ada"]

    try:
        pd.to_numeric(df["KOLI QTY"], errors="raise")
    except:
        return False, ["Kolom KOLI QTY harus angka"]

    return True, []

# -----------------------
# Canvas page numbering
# -----------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for p in self._pages:
            self.__dict__.update(p)
            self.draw_page_number(total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, total):
        page = self.getPageNumber()
        txt = f"{page}/{total}"
        self.setFont("Helvetica", 9)
        self.drawRightString(A4[0] - 40, 30, txt)

# -----------------------
# Auto-fit column width
# -----------------------
def auto_column_widths(df):
    col_widths = []
    for col in df.columns:
        max_len = max(df[col].astype(str).map(len).max(), len(col))
        col_widths.append(max(40, min(120, max_len * 4)))  # dynamic width
    return col_widths

# -----------------------
# Generate PDF
# -----------------------
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=30, rightMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    tanggal_str = tanggal.strftime("%d/%m/%Y %H:%M")

    header_left = f"""
    <b>Tanggal:</b> {tanggal_str}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier Name:</b> {courier}<br/>
    <b>Driver Name:</b> {driver}<br/>
    <b>Police Number:</b> {police}<br/>
    """

    total_koli_box = Table(
        [["TOTAL KOLI"], [total_koli]],
        colWidths=[130]
    )
    total_koli_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ("FONTSIZE", (0, 0), (-1, 0), 14),
        ("FONTSIZE", (0, 1), (-1, 1), 32)
    ]))

    header_table = Table(
        [[Paragraph(header_left, styles["Normal"]), total_koli_box]],
        colWidths=[360, 150]
    )

    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Hide TIMESTAMP in PDF
    df_pdf = df.copy()
    if "TIMESTAMP" in df_pdf.columns:
        df_pdf = df_pdf.drop(columns=["TIMESTAMP"])

    col_widths = auto_column_widths(df_pdf)

    table_data = [list(df_pdf.columns)] + df_pdf.astype(str).values.tolist()

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTSIZE", (0, 0), (-1, 0), 8),  # header
        ("FONTSIZE", (0, 1), (-1, -1), 7),  # body
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    elements.append(table)
    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer

# -----------------------
# Upload handling
# -----------------------
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    if "TIME STAMP" in df.columns and "TIMESTAMP" not in df.columns:
        df["TIMESTAMP"] = df["TIME STAMP"]

    ok, err = validate_excel_file(df)
    if not ok:
        for e in err:
            st.error("❌ " + e)
        st.stop()

    total_koli = int(pd.to_numeric(df["KOLI QTY"], errors="coerce").fillna(0).sum())

    st.success("✔ File valid — data ditampilkan di bawah")
    st.dataframe(df, use_container_width=True)

    if st.button("Generate PDF"):
        pdf = generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli)
        st.download_button(
            "📄 Download PDF",
            data=pdf,
            file_name=f"BAST_{warehouse}_{courier}_{police}_{tanggal.strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
        )
else:
    st.info("📥 Upload file setelah header terisi lengkap.")
