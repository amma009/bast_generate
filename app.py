import streamlit as st
import pandas as pd
from datetime import datetime, time
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import io

# Try timezone
try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Jakarta")
except:
    tz = None

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
    waktu_only = st.time_input("Waktu (pilih manual)", value=None)   # FLEXIBLE
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

def combine_datetime(d, t):
    if t is None:  # jika waktu tidak diisi
        return None
    dt = datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)
    if tz:
        return dt.replace(tzinfo=tz)
    return dt

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

missing_fields = [k for k, v in header_fields.items() if not str(v).strip()]

if waktu_only is None:
    missing_fields.append("Waktu")

if missing_fields:
    st.warning(f"⚠️ Isi semua data header: {', '.join(missing_fields)}")
    uploaded_file = None
else:
    uploaded_file = st.file_uploader("Pilih file (Excel / CSV)", type=["xlsx", "xls", "csv"])

# -----------------------
# Validasi isi file
# -----------------------
def validate_excel_file(df):
    if df is None or df.empty:
        return False, ["File kosong"]

    if "KOLI QTY" not in df.columns:
        return False, ["Kolom 'KOLI QTY' tidak ditemukan"]

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
        text = f"{page}/{total}"
        self.setFont("Helvetica", 9)
        self.drawRightString(A4[0] - 40, 30, text)

# -----------------------
# Split table per 50 rows
# -----------------------
def paginate_table(df, rows_per_page=50):
    tables = []
    for i in range(0, len(df), rows_per_page):
        chunk = df.iloc[i:i + rows_per_page]
        tables.append(chunk)
    return tables

# -----------------------
# Generate PDF
# -----------------------
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40, leftMargin=30, rightMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Header info left
    tanggal_str = tanggal.strftime("%d/%m/%Y %H:%M:%S")

    header_left = f"""
    <b>Tanggal:</b> {tanggal_str}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier:</b> {courier}<br/>
    <b>Driver:</b> {driver}<br/>
    <b>Police Number:</b> {police}<br/>
    """

    # TOTAL KOLI (besar)
    koli_style = ParagraphStyle("big", fontSize=32, alignment=1)

    total_koli_box = Table(
        [
            ["TOTAL KOLI"],
            [total_koli],
        ],
        colWidths=[140]
    )
    total_koli_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))

    header_table = Table([[Paragraph(header_left, styles["Normal"]), total_koli_box]],
                         colWidths=[350, 140])
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Hide TIMESTAMP for PDF
    df_pdf = df.copy()
    if "TIMESTAMP" in df_pdf.columns:
        df_pdf = df_pdf.drop(columns=["TIMESTAMP"])

    pages = paginate_table(df_pdf, rows_per_page=50)

    for idx, chunk in enumerate(pages):
        table_data = [list(chunk.columns)] + chunk.values.tolist()

        table = Table(table_data, colWidths=[(A4[0]-60)/len(chunk.columns)] * len(chunk.columns))
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.grey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
            ("GRID", (0,0), (-1,-1), 0.4, colors.black),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("FONTSIZE", (0,0), (-1,-1), 6),
        ]))

        elements.append(table)

        if idx < len(pages) - 1:
            elements.append(PageBreak())

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

    st.success("✔ File OK — Preview di bawah")
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
