import streamlit as st
import pandas as pd
from datetime import datetime, time
from io import StringIO
import io
import re

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# ==================================================
# CONFIG
# ==================================================
st.set_page_config(page_title="BAST Generator", layout="wide")
st.title("📦 BAST Generator (Copy Paste Mode)")
st.caption("Tanpa upload file. Tinggal copy dari Excel lalu paste.")

# ==================================================
# HEADER INPUT
# ==================================================
st.header("Input Header")

col1, col2 = st.columns(2)

with col1:
    tanggal_only = st.date_input("Tanggal", datetime.now().date())
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")

with col2:
    waktu_only = st.time_input("Waktu", value=datetime.now().time())
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")


def make_datetime(date_obj, time_obj):
    return datetime(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        time_obj.hour,
        time_obj.minute,
        time_obj.second
    )


tanggal = make_datetime(tanggal_only, waktu_only)

# ==================================================
# PASTE DATA
# ==================================================
st.header("Paste Data")

raw_text = st.text_area(
    "Copy dari Excel lalu paste di sini",
    height=300,
    placeholder="""NO\tDELIVERY ORDER\tAIRWAYBILL\tSTATE\tPROVIDER\tKOLI QTY
1\tDO001\tAWB001\tJKT\tJNE\t2
2\tDO002\tAWB002\tBDG\tSICEPAT\t1"""
)

# ==================================================
# FUNCTIONS
# ==================================================
def safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(text))


def parse_paste_data(text):
    if not text.strip():
        return None

    try:
        # Detect tab (Excel copy paste)
        if "\t" in text:
            df = pd.read_csv(StringIO(text), sep="\t")
        else:
            df = pd.read_csv(StringIO(text))
        return df
    except:
        return None


def validate_file(df):
    errors = []

    if df is None or df.empty:
        errors.append("Data kosong.")

    required = [
        "NO",
        "DELIVERY ORDER",
        "AIRWAYBILL",
        "STATE",
        "PROVIDER",
        "KOLI QTY"
    ]

    for col in required:
        if col not in df.columns:
            errors.append(f"Kolom wajib tidak ada: {col}")

    return len(errors) == 0, errors


# ==================================================
# PAGE NUMBER
# ==================================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self.pages)

        for page in self.pages:
            self.__dict__.update(page)
            self.draw_page_number(total)
            super().showPage()

        super().save()

    def draw_page_number(self, total):
        page = self.getPageNumber()
        self.setFont("Helvetica", 9)
        self.drawRightString(A4[0] - 40, 20, f"{page}/{total}")


# ==================================================
# PDF GENERATOR
# ==================================================
def generate_pdf(df, tanggal, warehouse, courier, driver, police):
    buffer = io.BytesIO()

    margin = 0.5 * inch
    page_width = A4[0] - (margin * 2)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---------------- TITLE ----------------
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        alignment=1,
        fontSize=18,
        spaceAfter=12
    )

    elements.append(
        Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", title_style)
    )

    # ---------------- HEADER ----------------
    total_koli = int(
        pd.to_numeric(df["KOLI QTY"], errors="coerce")
        .fillna(0)
        .sum()
    )

    tanggal_str = tanggal.strftime("%d/%m/%Y %H:%M:%S")

    header_text = f"""
    <b>Tanggal:</b> {tanggal_str}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier Name:</b> {courier}<br/>
    <b>Driver Name:</b> {driver}<br/>
    <b>Police Number:</b> {police}<br/>
    """

    label_style = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        alignment=1,
        fontSize=11
    )

    big_style = ParagraphStyle(
        "big",
        parent=styles["Normal"],
        alignment=1,
        fontSize=22
    )

    total_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", big_style)]
        ],
        colWidths=[140]
    )

    total_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER")
    ]))

    header_table = Table(
        [[Paragraph(header_text, styles["Normal"]), total_box]],
        colWidths=[page_width - 140, 140]
    )

    elements.append(header_table)
    elements.append(Spacer(1, 12))

    # ---------------- DATA TABLE ----------------
    expected = [
        "NO",
        "DELIVERY ORDER",
        "AIRWAYBILL",
        "STATE",
        "PROVIDER",
        "KOLI QTY"
    ]

    df = df[expected].fillna("")

    data = [list(df.columns)] + df.values.tolist()

    widths = [
        page_width * 0.06,
        page_width * 0.22,
        page_width * 0.28,
        page_width * 0.12,
        page_width * 0.20,
        page_width * 0.12
    ]

    table = Table(data, repeatRows=1, colWidths=widths)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2)
    ]))

    elements.append(table)

    # ---------------- SIGNATURE ----------------
    elements.append(Spacer(1, 20))

    note_style = ParagraphStyle(
        "note",
        parent=styles["Normal"],
        alignment=1,
        fontSize=8
    )

    sign = Table(
        [
            ["Diperiksa oleh", "Diserahkan oleh", "Diterima oleh"],
            ["", "", ""],
            ["", "", ""],
            ["", "", ""],
            ["__________________", "__________________", "__________________"],
            ["(Security WH)", "(Dispatcher WH)", "(Driver Courier)"],
            [
                Paragraph(
                    "* BAST ini sebagai bukti bahwa paket sudah diserahkan "
                    "dengan kondisi baik dan jumlah koli sesuai.",
                    note_style
                ),
                "",
                ""
            ]
        ],
        colWidths=[page_width / 3] * 3
    )

    sign.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("SPAN", (0, 6), (2, 6)),
        ("TOPPADDING", (0, 0), (-1, -1), 4)
    ]))

    elements.append(sign)

    doc.build(elements, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return buffer


# ==================================================
# PROCESS
# ==================================================
if raw_text.strip():

    df = parse_paste_data(raw_text)

    valid, errors = validate_file(df)

    if not valid:
        for e in errors:
            st.error(e)

    else:
        st.success("Data berhasil dibaca.")
        st.dataframe(df, use_container_width=True)

        total_koli = int(
            pd.to_numeric(df["KOLI QTY"], errors="coerce")
            .fillna(0)
            .sum()
        )

        st.info(f"TOTAL KOLI: {total_koli}")

        if st.button("Generate PDF"):

            pdf = generate_pdf(
                df,
                tanggal,
                warehouse,
                courier,
                driver,
                police
            )

            fname = (
                f"BAST_"
                f"{safe_filename(warehouse)}_"
                f"{safe_filename(courier)}_"
                f"{safe_filename(police)}_"
                f"{tanggal.strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            st.download_button(
                "📥 Download PDF",
                data=pdf,
                file_name=fname,
                mime="application/pdf"
            )
