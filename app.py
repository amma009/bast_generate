import streamlit as st
import pandas as pd
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

st.set_page_config(page_title="BAST Generator", layout="wide")

# ------------------------------
# CUSTOM CANVAS (REAL PAGE COUNT)
# ------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        super().showPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(f"{self._pageNumber}/{total_pages}")
            super().showPage()
        super().save()

    def draw_page_number(self, text):
        self.setFont("Helvetica", 9)
        self.drawRightString(A4[0] - 40, 30, text)


# ------------------------------
# GENERATE PDF
# ------------------------------
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):

    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    elements = []

    # TITLE
    elements.append(Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    # HEADER CONTENT
    header_left = f"""
        <b>Tanggal:</b> {tanggal.strftime("%d/%m/%Y %H:%M")}<br/>
        <b>Warehouse:</b> {warehouse}<br/>
        <b>Courier Name:</b> {courier}<br/>
        <b>Driver Name:</b> {driver}<br/>
        <b>Police Number:</b> {police}<br/>
    """

    koli_style = ParagraphStyle(
        "KoliStyle",
        parent=styles["Normal"],
        alignment=1,
        fontSize=36,
        leading=40,
    )

    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        alignment=1,
        fontSize=18,
    )

    total_koli_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", koli_style)],
        ],
        colWidths=[130],
    )

    total_koli_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 2, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ]
        )
    )

    header_table = Table(
        [
            [Paragraph(header_left, styles["Normal"]), total_koli_box],
        ],
        colWidths=[350, 150],
    )

    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # -------------------------
    # GENERATE MAIN TABLE
    # -------------------------
    table_data = [list(df.columns)] + df.values.tolist()

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 20))

    # -------------------------
    # SIGNATURE AREA
    # -------------------------
    signature_table = Table(
        [
            ["Diperiksa oleh", "Diserahkan oleh", "Diterima oleh"],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
            ["__________________", "__________________", "__________________"],
            ["(Security WH)", "(Dispatcher WH)", "(Driver Courier)"],
        ],
        colWidths=[180, 180, 180],
    )

    signature_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
            ]
        )
    )

    elements.append(signature_table)

    pdf.build(elements, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer


# ------------------------------
# STREAMLIT UI
# ------------------------------

st.title("📄 BAST Generator")

col1, col2 = st.columns(2)

with col1:
    tanggal = st.datetime_input("Tanggal")
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")
    driver = st.text_input("Driver Name")

with col2:
    police = st.text_input("Police Number")
    total_koli = st.number_input("Total Koli", min_value=0, step=1)

uploaded_file = st.file_uploader("Upload File Data (Excel/CSV)", type=["xlsx", "xls", "csv"])

# VALIDASI HEADER WAJIB DIISI
if uploaded_file and (warehouse == "" or courier == "" or driver == "" or police == ""):
    st.error("❌ Semua header wajib diisi sebelum upload file.")
    st.stop()

df = None

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("✔ File berhasil dibaca!")
    st.write(df)

    if st.button("Generate PDF"):
        pdf_buffer = generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli)
        st.download_button(
            label="⬇ Download PDF",
            data=pdf_buffer,
            file_name="BAST.pdf",
            mime="application/pdf"
        )
