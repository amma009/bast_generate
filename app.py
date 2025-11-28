import streamlit as st
import pandas as pd
from datetime import datetime, time
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
# Header Inputs
# -----------------------
st.header("Input Data Header")
col1, col2 = st.columns(2)

with col1:
    tanggal_only = st.date_input("Tanggal", datetime.now().date())
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")

with col2:
    # Time input without default now()
    waktu_only = st.time_input("Waktu", value=time(0, 0))
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

# Combine date & time (no timezone)
def make_datetime(date_obj, time_obj):
    return datetime(date_obj.year, date_obj.month, date_obj.day,
                    time_obj.hour, time_obj.minute, time_obj.second)

tanggal = make_datetime(tanggal_only, waktu_only)

# -----------------------
# Upload
# -----------------------
st.header("Upload Excel / CSV Data")

header_fields = {
    "Warehouse": warehouse,
    "Courier Name": courier,
    "Driver Name": driver,
    "Police Number": police
}

missing = [f for f,v in header_fields.items() if not str(v).strip()]
if missing:
    st.warning(f"⚠️ Lengkapi header: {', '.join(missing)}")
    uploaded_file = None
else:
    uploaded_file = st.file_uploader("Pilih file", type=["xlsx", "xls", "csv"])

# -----------------------
# Validation
# -----------------------
def validate_file(df):
    errors = []
    if df is None or df.empty:
        errors.append("File kosong.")
        return False, errors

    if "KOLI QTY" not in df.columns:
        errors.append("Kolom KOLI QTY wajib ada.")

    return len(errors) == 0, errors

# -----------------------
# PDF Canvas + Page Numbers
# -----------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self.draw_page_number(total)
            super().showPage()
        super().save()

    def draw_page_number(self, total):
        page = self.getPageNumber()
        text = f"{page}/{total}"
        self.setFont("Helvetica", 9)
        self.drawRightString(A4[0] - 40, 0.5 * inch, text)

# -----------------------
# PDF Generator
# -----------------------
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()

    margin = 0.5 * inch
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=margin, bottomMargin=margin
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    # Header text
    tanggal_str = tanggal.strftime('%d/%m/%Y %H:%M:%S')
    header_left = f"""
        <b>Tanggal:</b> {tanggal_str}<br/>
        <b>Warehouse:</b> {warehouse}<br/>
        <b>Courier Name:</b> {courier}<br/>
        <b>Driver Name:</b> {driver}<br/>
        <b>Police Number:</b> {police}<br/>
    """

    # Total Koli Box
    koli_style = ParagraphStyle("Koli", parent=styles["Normal"], alignment=1, fontSize=28)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], alignment=1, fontSize=14)

    total_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", koli_style)]
        ],
        colWidths=[130]
    )
    total_box.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 2, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    page_width = A4[0] - (margin*2)
    header_width = page_width - 130

    header_table = Table([[Paragraph(header_left, styles["Normal"]), total_box]],
                         colWidths=[header_width, 130])

    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Clean DF
    df_clean = df.copy().fillna("")
    if "TIMESTAMP" in df_clean.columns:
        df_clean = df_clean.drop(columns=["TIMESTAMP"])

    # TABLE FORMAT — tidy columns
    header = list(df_clean.columns)
    data = df_clean.values.tolist()

    # Adjust column widths — proportional layout
    num_cols = len(header)
    col_width = page_width / num_cols
    col_widths = [col_width] * num_cols

    table = Table([header] + data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("FONTSIZE", (0,0), (-1,-1), 9),     # FONT 9
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 2),
        ("RIGHTPADDING", (0,0), (-1,-1), 2)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Signature
    sign = Table(
        [
            ["Diperiksa oleh", "Diserahkan oleh", "Diterima oleh"],
            ["", "", ""], ["", "", ""], ["", "", ""],
            ["__________________", "__________________", "__________________"],
            ["(Security WH)", "(Dispatcher WH)", "(Driver Courier)"]
        ],
        colWidths=[page_width/3]*3
    )
    sign.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER")]))

    elements.append(sign)

    doc.build(elements, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer

# -----------------------
# Handle Upload
# -----------------------
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.lower().endswith("csv") else pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"❌ Gagal membaca file: {e}")
        st.stop()

    valid, errors = validate_file(df)
    if not valid:
        for err in errors:
            st.error("• " + err)
    else:
        total_koli = int(pd.to_numeric(df["KOLI QTY"], errors="coerce").fillna(0).sum())
        st.dataframe(df, use_container_width=True)

        if st.button("Generate PDF"):
            pdf_buffer = generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli)
            fname = f"BAST_{warehouse}_{courier}_{police}_{tanggal.strftime('%Y%m%d_%H%M%S')}.pdf"
            st.download_button("📥 Download PDF BAST", data=pdf_buffer, file_name=fname, mime="application/pdf")
