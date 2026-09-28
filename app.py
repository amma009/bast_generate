import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO

from streamlit_drawable_canvas import st_canvas

import io
import re

from PIL import Image

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as RLImage
)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from streamlit_drawable_canvas import st_canvas


# ==================================================
# CONFIG
# ==================================================

st.set_page_config(
    page_title="BAST Generator",
    layout="wide"
)

st.title("📦 BAST Generator")
st.caption(
    "Copy data dari Excel, isi 3 nama, lalu buat tanda tangan langsung."
)


# ==================================================
# HEADER INPUT
# ==================================================

st.header("Input Header")

col1, col2 = st.columns(2)

with col1:

    tanggal_only = st.date_input(
        "Tanggal",
        datetime.now().date()
    )

    warehouse = st.text_input(
        "Warehouse"
    )

    courier = st.text_input(
        "Courier Name"
    )


with col2:

    waktu_only = st.time_input(
        "Waktu",
        value=datetime.now().time()
    )

    driver = st.text_input(
        "Driver Name"
    )

    police = st.text_input(
        "Police Number"
    )


def make_datetime(date_obj, time_obj):

    return datetime(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        time_obj.hour,
        time_obj.minute,
        time_obj.second
    )


tanggal = make_datetime(
    tanggal_only,
    waktu_only
)


# ==================================================
# PASTE DATA
# ==================================================

st.header("Paste Data")

raw_text = st.text_area(
    "Copy dari Excel lalu paste di sini",
    height=300
)


# ==================================================
# SIGNATURE INPUT
# ==================================================

st.header("✍️ Tanda Tangan")

st.info(
    "Isi nama masing-masing orang, kemudian gambar tanda tangan "
    "menggunakan mouse atau jari."
)


# ==================================================
# NAMA SIGNER
# ==================================================

sig_col1, sig_col2, sig_col3 = st.columns(3)


with sig_col1:

    st.subheader("Diperiksa oleh")
    st.caption("Security WH")

    security_name = st.text_input(
        "Nama Security",
        key="security_name"
    )


with sig_col2:

    st.subheader("Diserahkan oleh")
    st.caption("Dispatcher WH")

    dispatcher_name = st.text_input(
        "Nama Dispatcher",
        key="dispatcher_name"
    )


with sig_col3:

    st.subheader("Diterima oleh")
    st.caption("Driver Courier")

    driver_name = st.text_input(
        "Nama Driver Courier",
        key="driver_courier_name"
    )


# ==================================================
# CANVAS SIGNATURE
# ==================================================

st.subheader("Gambar Tanda Tangan")


canvas_col1, canvas_col2, canvas_col3 = st.columns(3)


with canvas_col1:

    st.markdown("**Security WH**")

    security_canvas = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=180,
        width=350,
        drawing_mode="freedraw",
        key="security_canvas",
        display_toolbar=True
    )


with canvas_col2:

    st.markdown("**Dispatcher WH**")

    dispatcher_canvas = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=180,
        width=350,
        drawing_mode="freedraw",
        key="dispatcher_canvas",
        display_toolbar=True
    )


with canvas_col3:

    st.markdown("**Driver Courier**")

    driver_canvas = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=180,
        width=350,
        drawing_mode="freedraw",
        key="driver_canvas",
        display_toolbar=True
    )


# ==================================================
# FUNCTIONS
# ==================================================

def safe_filename(text):

    return re.sub(
        r"[^A-Za-z0-9_-]",
        "_",
        str(text)
    )


def parse_paste_data(text):

    if not text.strip():
        return None

    try:

        if "\t" in text:

            df = pd.read_csv(
                StringIO(text),
                sep="\t"
            )

        else:

            df = pd.read_csv(
                StringIO(text)
            )

        return df

    except:

        return None


def validate_file(df):

    errors = []

    if df is None or df.empty:

        errors.append(
            "Data kosong."
        )

    required = [
        "NO",
        "DELIVERY ORDER",
        "AIRWAYBILL",
        "STATE",
        "PROVIDER",
        "KOLI QTY"
    ]

    if df is not None:

        for col in required:

            if col not in df.columns:

                errors.append(
                    f"Kolom wajib tidak ada: {col}"
                )

    return len(errors) == 0, errors


# ==================================================
# FIX ENTER DALAM CELL
# ==================================================

def fix_broken_rows(text):

    lines = (
        text
        .replace("\r", "")
        .split("\n")
    )

    fixed_lines = []

    for line in lines:

        line = line.strip()

        if line.isdigit() and fixed_lines:

            fixed_lines[-1] += "\t" + line

        else:

            fixed_lines.append(line)

    return "\n".join(fixed_lines)


# ==================================================
# PAGE NUMBER
# ==================================================

class NumberedCanvas(canvas.Canvas):

    def __init__(
        self,
        *args,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.pages = []


    def showPage(self):

        self.pages.append(
            dict(self.__dict__)
        )

        self._startPage()


    def save(self):

        total = len(self.pages)

        for page in self.pages:

            self.__dict__.update(page)

            self.draw_page_number(
                total
            )

            super().showPage()

        super().save()


    def draw_page_number(self, total):

        page = self.getPageNumber()

        self.setFont(
            "Helvetica",
            9
        )

        self.drawRightString(
            A4[0] - 40,
            20,
            f"{page}/{total}"
        )


# ==================================================
# CONVERT CANVAS TO PNG
# ==================================================

def canvas_to_png(canvas_result):

    if canvas_result is None:
        return None

    if canvas_result.image_data is None:
        return None

    image = Image.fromarray(
        canvas_result.image_data.astype("uint8")
    )

    # Pastikan RGBA
    image = image.convert("RGBA")

    output = io.BytesIO()

    image.save(
        output,
        format="PNG"
    )

    output.seek(0)

    return output


# ==================================================
# PDF GENERATOR
# ==================================================

def generate_pdf(
    df,
    tanggal,
    warehouse,
    courier,
    driver,
    police,
    security_name,
    dispatcher_name,
    driver_name,
    security_signature,
    dispatcher_signature,
    driver_signature
):

    buffer = io.BytesIO()

    margin = 0.5 * inch

    page_width = (
        A4[0]
        - (margin * 2)
    )

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


    # ==================================================
    # TITLE
    # ==================================================

    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        alignment=1,
        fontSize=18,
        spaceAfter=12
    )


    elements.append(
        Paragraph(
            "<b>BERITA ACARA SERAH TERIMA</b>",
            title_style
        )
    )


    # ==================================================
    # HEADER
    # ==================================================

    total_koli = int(
        pd.to_numeric(
            df["KOLI QTY"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    tanggal_str = tanggal.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


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
            [
                Paragraph(
                    "<b>TOTAL KOLI</b>",
                    label_style
                )
            ],
            [
                Paragraph(
                    f"<b>{total_koli}</b>",
                    big_style
                )
            ]
        ],
        colWidths=[140],
        rowHeights=[25, 45]
    )


    total_box.setStyle(
        TableStyle([
            (
                "BOX",
                (0, 0),
                (-1, -1),
                1.5,
                colors.black
            ),

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )


    header_table = Table(
        [
            [
                Paragraph(
                    header_text,
                    styles["Normal"]
                ),
                total_box
            ]
        ],
        colWidths=[
            page_width - 140,
            140
        ]
    )


    elements.append(
        header_table
    )

    elements.append(
        Spacer(1, 12)
    )


    # ==================================================
    # TABLE DATA
    # ==================================================

    expected = [
        "NO",
        "DELIVERY ORDER",
        "AIRWAYBILL",
        "STATE",
        "PROVIDER",
        "KOLI QTY"
    ]


    df = df[
        expected
    ].fillna("")


    data = [
        list(df.columns)
    ] + df.values.tolist()


    table = Table(
        data,
        repeatRows=1
    )


    table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#1F4E78"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.4,
                colors.black
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            )

        ])
    )


    elements.append(
        table
    )


    # ==================================================
    # SIGNATURE
    # ==================================================

    elements.append(
        Spacer(1, 25)
    )


    note_style = ParagraphStyle(
        "note",
        parent=styles["Normal"],
        alignment=1,
        fontSize=8
    )


    signature_cells = []


    # --------------------------------------------------
    # SECURITY
    # --------------------------------------------------

    if security_signature is not None:

        security_img = RLImage(
            security_signature,
            width=120,
            height=60
        )

    else:

        security_img = Paragraph(
            "<br/><br/><br/>",
            styles["Normal"]
        )


    security_cell = [
        security_img,
        Paragraph(
            f"<b>{security_name}</b>"
            if security_name
            else " ",
            styles["Normal"]
        ),
        Paragraph(
            "(Security WH)",
            styles["Normal"]
        )
    ]


    # --------------------------------------------------
    # DISPATCHER
    # --------------------------------------------------

    if dispatcher_signature is not None:

        dispatcher_img = RLImage(
            dispatcher_signature,
            width=120,
            height=60
        )

    else:

        dispatcher_img = Paragraph(
            "<br/><br/><br/>",
            styles["Normal"]
        )


    dispatcher_cell = [
        dispatcher_img,
        Paragraph(
            f"<b>{dispatcher_name}</b>"
            if dispatcher_name
            else " ",
            styles["Normal"]
        ),
        Paragraph(
            "(Dispatcher WH)",
            styles["Normal"]
        )
    ]


    # --------------------------------------------------
    # DRIVER
    # --------------------------------------------------

    if driver_signature is not None:

        driver_img = RLImage(
            driver_signature,
            width=120,
            height=60
        )

    else:

        driver_img = Paragraph(
            "<br/><br/><br/>",
            styles["Normal"]
        )


    driver_cell = [
        driver_img,
        Paragraph(
            f"<b>{driver_name}</b>"
            if driver_name
            else " ",
            styles["Normal"]
        ),
        Paragraph(
            "(Driver Courier)",
            styles["Normal"]
        )
    ]


    # ==================================================
    # SIGNATURE TABLE
    # ==================================================

    sign = Table(
        [
            [
                Paragraph(
                    "<b>Diperiksa oleh</b>",
                    styles["Normal"]
                ),

                Paragraph(
                    "<b>Diserahkan oleh</b>",
                    styles["Normal"]
                ),

                Paragraph(
                    "<b>Diterima oleh</b>",
                    styles["Normal"]
                )
            ],

            [
                security_cell,
                dispatcher_cell,
                driver_cell
            ],

            [
                Paragraph(
                    "<br/>",
                    styles["Normal"]
                ),
                Paragraph(
                    "<br/>",
                    styles["Normal"]
                ),
                Paragraph(
                    "<br/>",
                    styles["Normal"]
                )
            ],

            [
                Paragraph(
                    "* BAST ini sebagai bukti bahwa paket "
                    "sudah diserahkan dengan kondisi baik "
                    "dan jumlah koli sesuai.",
                    note_style
                ),
                "",
                ""
            ]
        ],
        colWidths=[
            page_width / 3
        ] * 3
    )


    sign.setStyle(
        TableStyle([

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "SPAN",
                (0, 3),
                (2, 3)
            )

        ])
    )


    elements.append(
        sign
    )


    # ==================================================
    # BUILD
    # ==================================================

    doc.build(
        elements,
        canvasmaker=NumberedCanvas
    )


    buffer.seek(0)

    return buffer


# ==================================================
# PROCESS
# ==================================================

if raw_text.strip():

    cleaned = fix_broken_rows(
        raw_text
    )

    df = parse_paste_data(
        cleaned
    )


    valid, errors = validate_file(
        df
    )


    if not valid:

        for e in errors:

            st.error(e)


    else:

        st.success(
            "Data berhasil dibaca."
        )


        st.dataframe(
            df
        )


        total_koli = int(
            pd.to_numeric(
                df["KOLI QTY"],
                errors="coerce"
            )
            .fillna(0)
            .sum()
        )


        st.info(
            f"TOTAL KOLI: {total_koli}"
        )


        # ==================================================
        # VALIDASI NAMA
        # ==================================================

        names_ready = (
            security_name.strip()
            and dispatcher_name.strip()
            and driver_name.strip()
        )


        # ==================================================
        # GENERATE
        # ==================================================

        if st.button(
            "📄 Generate PDF",
            type="primary"
        ):

            if not names_ready:

                st.error(
                    "Nama Security, Dispatcher, "
                    "dan Driver Courier wajib diisi."
                )

                st.stop()


            # ----------------------------------------------
            # CONVERT SIGNATURE
            # ----------------------------------------------

            security_signature = canvas_to_png(
                security_canvas
            )

            dispatcher_signature = canvas_to_png(
                dispatcher_canvas
            )

            driver_signature = canvas_to_png(
                driver_canvas
            )


            # ----------------------------------------------
            # VALIDATE SIGNATURE
            # ----------------------------------------------

            if (
                security_signature is None
                or dispatcher_signature is None
                or driver_signature is None
            ):

                st.error(
                    "Ketiga tanda tangan wajib dibuat "
                    "sebelum Generate PDF."
                )

                st.stop()


            # ----------------------------------------------
            # GENERATE PDF
            # ----------------------------------------------

            pdf = generate_pdf(
                df=df,
                tanggal=tanggal,
                warehouse=warehouse,
                courier=courier,
                driver=driver,
                police=police,

                security_name=security_name,
                dispatcher_name=dispatcher_name,
                driver_name=driver_name,

                security_signature=security_signature,
                dispatcher_signature=dispatcher_signature,
                driver_signature=driver_signature
            )


            fname = (
                f"BAST_"
                f"{tanggal.strftime('%Y%m%d_%H%M%S')}.pdf"
            )


            st.success(
                "PDF berhasil dibuat!"
            )


            st.download_button(
                "📥 Download PDF",
                data=pdf,
                file_name=fname,
                mime="application/pdf"
            )
