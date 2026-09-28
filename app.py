import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO
import io
import re

from PIL import Image
from streamlit_drawable_canvas import st_canvas

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


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="BAST Generator",
    page_icon="📦",
    layout="wide"
)

st.title("📦 BAST Generator")
st.caption(
    "Copy data dari Excel, isi data BAST, lalu buat 3 tanda tangan "
    "langsung menggunakan mouse atau jari."
)


# ============================================================
# HEADER INPUT
# ============================================================

st.header("📋 Input Header")

col1, col2 = st.columns(2)

with col1:

    tanggal_only = st.date_input(
        "Tanggal",
        value=datetime.now().date()
    )

    warehouse = st.text_input(
        "Warehouse",
        placeholder="Contoh: WH Jakarta"
    )

    courier = st.text_input(
        "Courier Name",
        placeholder="Nama courier"
    )


with col2:

    waktu_only = st.time_input(
        "Waktu",
        value=datetime.now().time()
    )

    driver = st.text_input(
        "Driver Name",
        placeholder="Nama driver"
    )

    police = st.text_input(
        "Police Number",
        placeholder="Nomor kendaraan"
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


# ============================================================
# PASTE DATA
# ============================================================

st.header("📊 Paste Data")

raw_text = st.text_area(
    "Copy data dari Excel lalu paste di sini",
    height=300,
    placeholder=(
        "NO\tDELIVERY ORDER\tAIRWAYBILL\tSTATE\tPROVIDER\tKOLI QTY\n"
        "1\tDO001\tAWB001\tDELIVERED\tJNE\t2"
    )
)


# ============================================================
# SIGNATURE INPUT
# ============================================================

st.header("✍️ Tanda Tangan")

st.info(
    "Isi nama masing-masing orang, kemudian gambar tanda tangan "
    "menggunakan mouse atau jari."
)


# ============================================================
# NAMA SIGNER
# ============================================================

sig_col1, sig_col2, sig_col3 = st.columns(3)


with sig_col1:

    st.subheader("Diperiksa oleh")
    st.caption("Security WH")

    security_name = st.text_input(
        "Nama Security",
        key="security_name",
        placeholder="Nama Security"
    )


with sig_col2:

    st.subheader("Diserahkan oleh")
    st.caption("Dispatcher WH")

    dispatcher_name = st.text_input(
        "Nama Dispatcher",
        key="dispatcher_name",
        placeholder="Nama Dispatcher"
    )


with sig_col3:

    st.subheader("Diterima oleh")
    st.caption("Driver Courier")

    driver_name = st.text_input(
        "Nama Driver Courier",
        key="driver_courier_name",
        placeholder="Nama Driver"
    )


# ============================================================
# CANVAS SIGNATURE
# ============================================================

st.subheader("🖊️ Gambar Tanda Tangan")

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


# ============================================================
# FUNCTIONS
# ============================================================

def safe_filename(text):

    return re.sub(
        r"[^A-Za-z0-9_-]",
        "_",
        str(text)
    )


# ============================================================
# PARSE DATA
# ============================================================

def parse_paste_data(text):

    if not text or not text.strip():
        return None

    try:

        # Excel copy biasanya menggunakan TAB
        if "\t" in text:

            df = pd.read_csv(
                StringIO(text),
                sep="\t"
            )

        else:

            df = pd.read_csv(
                StringIO(text)
            )

        # Bersihkan nama kolom
        df.columns = [
            str(col).strip()
            for col in df.columns
        ]

        return df

    except Exception:

        return None


# ============================================================
# VALIDATE DATA
# ============================================================

def validate_file(df):

    errors = []

    if df is None:

        errors.append(
            "Data tidak dapat dibaca."
        )

        return False, errors


    if df.empty:

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


    for col in required:

        if col not in df.columns:

            errors.append(
                f"Kolom wajib tidak ada: {col}"
            )


    return len(errors) == 0, errors


# ============================================================
# FIX BROKEN ROWS
# ============================================================

def fix_broken_rows(text):

    lines = (
        text
        .replace("\r", "")
        .split("\n")
    )

    fixed_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # Jika hanya angka dan ada baris sebelumnya,
        # dianggap bagian dari KOLI QTY
        if line.isdigit() and fixed_lines:

            fixed_lines[-1] += "\t" + line

        else:

            fixed_lines.append(line)

    return "\n".join(fixed_lines)


# ============================================================
# CANVAS TO PNG
# ============================================================

def canvas_to_png(canvas_result):

    if canvas_result is None:
        return None

    if canvas_result.image_data is None:
        return None

    try:

        image = Image.fromarray(
            canvas_result.image_data.astype("uint8")
        )

        image = image.convert("RGBA")

        output = io.BytesIO()

        image.save(
            output,
            format="PNG"
        )

        output.seek(0)

        return output

    except Exception:

        return None


# ============================================================
# CHECK SIGNATURE EMPTY
# ============================================================

def signature_exists(canvas_result):

    if canvas_result is None:
        return False

    if canvas_result.image_data is None:
        return False

    try:

        image_data = canvas_result.image_data

        # Background canvas putih.
        # Cek apakah ada pixel yang bukan putih.
        rgb = image_data[:, :, :3]

        non_white = (
            (rgb[:, :, 0] < 245)
            | (rgb[:, :, 1] < 245)
            | (rgb[:, :, 2] < 245)
        )

        return bool(non_white.any())

    except Exception:

        return False


# ============================================================
# PAGE NUMBER CANVAS
# ============================================================

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


# ============================================================
# PDF GENERATOR
# ============================================================

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
        A4[0] - (margin * 2)
    )


    # ========================================================
    # DOCUMENT
    # ========================================================

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


    # ========================================================
    # TITLE
    # ========================================================

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


    elements.append(
        Spacer(1, 5)
    )


    # ========================================================
    # TOTAL KOLI
    # ========================================================

    total_koli = int(
        pd.to_numeric(
            df["KOLI QTY"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )


    # ========================================================
    # HEADER
    # ========================================================

    tanggal_str = tanggal.strftime(
        "%d/%m/%Y %H:%M:%S"
    )


    header_text = f"""
    <b>Tanggal:</b> {tanggal_str}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier Name:</b> {courier}<br/>
    <b>Driver Name:</b> {driver}<br/>
    <b>Police Number:</b> {police}
    """


    label_style = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        alignment=1,
        fontSize=10
    )


    big_style = ParagraphStyle(
        "big",
        parent=styles["Normal"],
        alignment=1,
        fontSize=20
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
        colWidths=[130],
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
            page_width - 130,
            130
        ]
    )


    header_table.setStyle(
        TableStyle([
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )


    elements.append(
        header_table
    )


    elements.append(
        Spacer(1, 12)
    )


    # ========================================================
    # DATA TABLE
    # ========================================================

    expected = [
        "NO",
        "DELIVERY ORDER",
        "AIRWAYBILL",
        "STATE",
        "PROVIDER",
        "KOLI QTY"
    ]


    df_pdf = df[
        expected
    ].fillna("")


    # Convert semua nilai menjadi string
    df_pdf = df_pdf.astype(str)


    data = [
        list(df_pdf.columns)
    ] + df_pdf.values.tolist()


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
                colors.HexColor("#1F4E78")
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
                7
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
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4
            )
        ])
    )


    elements.append(
        table
    )


    # ========================================================
    # SIGNATURE
    # ========================================================

    elements.append(
        Spacer(1, 25)
    )


    note_style = ParagraphStyle(
        "note",
        parent=styles["Normal"],
        alignment=1,
        fontSize=8
    )


    signature_name_style = ParagraphStyle(
        "signature_name",
        parent=styles["Normal"],
        alignment=1,
        fontSize=9
    )


    role_style = ParagraphStyle(
        "role",
        parent=styles["Normal"],
        alignment=1,
        fontSize=8
    )


    # ========================================================
    # SECURITY SIGNATURE
    # ========================================================

    if security_signature is not None:

        security_img = RLImage(
            security_signature,
            width=120,
            height=60
        )

    else:

        security_img = Spacer(
            1,
            60
        )


    security_cell = [
        security_img,

        Paragraph(
            f"<b>{security_name}</b>",
            signature_name_style
        ),

        Paragraph(
            "(Security WH)",
            role_style
        )
    ]


    # ========================================================
    # DISPATCHER SIGNATURE
    # ========================================================

    if dispatcher_signature is not None:

        dispatcher_img = RLImage(
            dispatcher_signature,
            width=120,
            height=60
        )

    else:

        dispatcher_img = Spacer(
            1,
            60
        )


    dispatcher_cell = [
        dispatcher_img,

        Paragraph(
            f"<b>{dispatcher_name}</b>",
            signature_name_style
        ),

        Paragraph(
            "(Dispatcher WH)",
            role_style
        )
    ]


    # ========================================================
    # DRIVER SIGNATURE
    # ========================================================

    if driver_signature is not None:

        driver_img = RLImage(
            driver_signature,
            width=120,
            height=60
        )

    else:

        driver_img = Spacer(
            1,
            60
        )


    driver_cell = [
        driver_img,

        Paragraph(
            f"<b>{driver_name}</b>",
            signature_name_style
        ),

        Paragraph(
            "(Driver Courier)",
            role_style
        )
    ]


    # ========================================================
    # SIGNATURE TABLE
    # ========================================================

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
                "",
                "",
                ""
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
                "LINEBELOW",
                (0, 1),
                (0, 1),
                0.5,
                colors.black
            ),

            (
                "LINEBELOW",
                (1, 1),
                (1, 1),
                0.5,
                colors.black
            ),

            (
                "LINEBELOW",
                (2, 1),
                (2, 1),
                0.5,
                colors.black
            ),

            (
                "SPAN",
                (0, 3),
                (2, 3)
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )


    elements.append(
        sign
    )


    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        elements,
        canvasmaker=NumberedCanvas
    )


    buffer.seek(0)

    return buffer


# ============================================================
# PROCESS DATA
# ============================================================

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

        for error in errors:

            st.error(error)


    else:

        st.success(
            "✅ Data berhasil dibaca."
        )


        # ====================================================
        # DATA PREVIEW
        # ====================================================

        st.subheader("Preview Data")

        st.dataframe(
            df,
            use_container_width=True
        )


        # ====================================================
        # TOTAL KOLI
        # ====================================================

        total_koli = int(
            pd.to_numeric(
                df["KOLI QTY"],
                errors="coerce"
            )
            .fillna(0)
            .sum()
        )


        st.info(
            f"📦 TOTAL KOLI: {total_koli}"
        )


        # ====================================================
        # VALIDASI NAMA
        # ====================================================

        names_ready = (
            bool(security_name.strip())
            and bool(dispatcher_name.strip())
            and bool(driver_name.strip())
        )


        # ====================================================
        # GENERATE BUTTON
        # ====================================================

        if st.button(
            "📄 Generate PDF",
            type="primary",
            use_container_width=True
        ):

            # -----------------------------------------------
            # VALIDASI NAMA
            # -----------------------------------------------

            if not names_ready:

                st.error(
                    "Nama Security, Dispatcher, dan "
                    "Driver Courier wajib diisi."
                )

                st.stop()


            # -----------------------------------------------
            # VALIDASI SIGNATURE
            # -----------------------------------------------

            security_exists = signature_exists(
                security_canvas
            )

            dispatcher_exists = signature_exists(
                dispatcher_canvas
            )

            driver_exists = signature_exists(
                driver_canvas
            )


            if not security_exists:

                st.error(
                    "✍️ Tanda tangan Security WH belum dibuat."
                )

                st.stop()


            if not dispatcher_exists:

                st.error(
                    "✍️ Tanda tangan Dispatcher WH belum dibuat."
                )

                st.stop()


            if not driver_exists:

                st.error(
                    "✍️ Tanda tangan Driver Courier belum dibuat."
                )

                st.stop()


            # -----------------------------------------------
            # CONVERT SIGNATURE
            # -----------------------------------------------

            security_signature = canvas_to_png(
                security_canvas
            )

            dispatcher_signature = canvas_to_png(
                dispatcher_canvas
            )

            driver_signature = canvas_to_png(
                driver_canvas
            )


            # -----------------------------------------------
            # GENERATE PDF
            # -----------------------------------------------

            with st.spinner(
                "Sedang membuat PDF..."
            ):

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


            # -----------------------------------------------
            # FILENAME
            # -----------------------------------------------

            warehouse_safe = safe_filename(
                warehouse
            )


            fname = (
                f"BAST_"
                f"{warehouse_safe}_"
                f"{tanggal.strftime('%Y%m%d_%H%M%S')}.pdf"
            )


            # -----------------------------------------------
            # SUCCESS
            # -----------------------------------------------

            st.success(
                "✅ PDF berhasil dibuat!"
            )


            st.download_button(
                label="📥 Download PDF",
                data=pdf,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True
            )
