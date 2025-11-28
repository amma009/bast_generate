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

# Try to use stdlib zoneinfo; fallback to pytz if unavailable
try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Asia/Jakarta")
except Exception:
    try:
        import pytz
        tz = pytz.timezone("Asia/Jakarta")
    except Exception:
        tz = None  # last resort: naive datetimes

st.set_page_config(page_title="BAST Generator", layout="wide")
st.title("📦 Berita Acara Serah Terima (BAST) Generator")

# -----------------------
# Input header
# -----------------------
st.header("Input Data Header")
col1, col2 = st.columns(2)

# get a timezone-aware "now" time for default if tz available, else naive now
if tz:
    now_local = datetime.now(tz)
    default_time = now_local.timetz()  # time with tzinfo (may include tz)
else:
    default_time = datetime.now().time()

with col1:
    tanggal_only = st.date_input("Tanggal", datetime.now().date())
    warehouse = st.text_input("Warehouse")
    courier = st.text_input("Courier Name")

with col2:
    # set default value for time_input using local time (UTC+7) if possible
    try:
        # Streamlit expects a time object; timetz() returns time with tzinfo which may be accepted,
        # but to be safe we convert to naive time (hour/min/sec) while keeping tz for later combine.
        default_time_naive = default_time.replace(tzinfo=None) if hasattr(default_time, "tzinfo") else default_time
    except Exception:
        default_time_naive = datetime.now().time()

    waktu_only = st.time_input("Waktu", default_time_naive)
    driver = st.text_input("Driver Name")
    police = st.text_input("Police Number")

# Helper to make a timezone-aware datetime (Asia/Jakarta) from date + time
def make_aware_datetime(date_obj, time_obj):
    """
    Returns a timezone-aware datetime in Asia/Jakarta if tz available,
    otherwise returns a naive datetime.
    """
    naive_dt = datetime(date_obj.year, date_obj.month, date_obj.day,
                        time_obj.hour, time_obj.minute, time_obj.second)
    if tz is None:
        return naive_dt
    # If tz is pytz (has localize), use localize; if zoneinfo, use replace(tzinfo=tz)
    if hasattr(tz, "localize"):
        # pytz timezone
        return tz.localize(naive_dt)
    else:
        # zoneinfo
        return naive_dt.replace(tzinfo=tz)

# create timezone-aware or naive datetime for header / filename
tanggal = make_aware_datetime(tanggal_only, waktu_only)

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
# Generate PDF function (hides TIMESTAMP column from PDF, small font, wide table)
# -----------------------
def generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli):
    buffer = io.BytesIO()

    # Margins (use same values when computing available width)
    left_margin = right_margin = top_margin = bottom_margin = 0.5 * inch

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        leftMargin=left_margin,
        rightMargin=right_margin
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("<b>BERITA ACARA SERAH TERIMA</b>", styles["Title"]))
    elements.append(Spacer(1, 10))

    # Header left (info)
    # show datetime including timezone offset if available
    try:
        # if tanggal is timezone-aware, strftime %z shows offset like +0700
        tanggal_str = tanggal.strftime('%d/%m/%Y %H:%M:%S %z')
    except Exception:
        tanggal_str = tanggal.strftime('%d/%m/%Y %H:%M:%S')

    header_left = f"""
    <b>Tanggal:</b> {tanggal_str}<br/>
    <b>Warehouse:</b> {warehouse}<br/>
    <b>Courier Name:</b> {courier}<br/>
    <b>Driver Name:</b> {driver}<br/>
    <b>Police Number:</b> {police}<br/>
    """

    # TOTAL KOLI style (36px)
    koli_style = ParagraphStyle("KoliStyle", parent=styles["Normal"], alignment=1, fontSize=36, leading=40)
    label_style = ParagraphStyle("LabelStyle", parent=styles["Normal"], alignment=1, fontSize=16)

    # Compute available width for content (page width minus margins)
    available_width = A4[0] - left_margin - right_margin

    total_koli_box_width = 150  # width for box (points)
    # ensure total_koli_box_width not exceed available width
    if total_koli_box_width > available_width * 0.4:
        total_koli_box_width = available_width * 0.3

    total_koli_box = Table(
        [
            [Paragraph("<b>TOTAL KOLI</b>", label_style)],
            [Paragraph(f"<b>{total_koli}</b>", koli_style)]
        ],
        colWidths=[total_koli_box_width]
    )
    total_koli_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 2, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    # Header table widths: left column gets remaining width
    header_left_width = available_width - total_koli_box_width
    header_table = Table([[Paragraph(header_left, styles["Normal"]), total_koli_box]],
                         colWidths=[header_left_width, total_koli_box_width])
    elements.append(header_table)
    elements.append(Spacer(1, 15))

    # Table data
    # Convert any NaN to empty string for clean PDF
    df_clean = df.fillna("")

    # --- HIDE TIMESTAMP column from PDF: create a copy and drop TIMESTAMP if present
    df_pdf = df_clean.copy()
    if "TIMESTAMP" in df_pdf.columns:
        df_pdf = df_pdf.drop(columns=["TIMESTAMP"])

    # Build table data from df_pdf (so TIMESTAMP won't appear)
    table_data = [list(df_pdf.columns)] + df_pdf.values.tolist()

    # Calculate column widths to fill available_width
    num_cols = len(df_pdf.columns) if len(df_pdf.columns) > 0 else 1
    col_width = available_width / num_cols
    col_widths = [col_width] * num_cols

    table = Table(table_data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 6),        # <<< smaller font for table
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
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
        colWidths=[available_width / 3, available_width / 3, available_width / 3]
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

    # If the file has a timestamp-like column but with different name, you can normalize it here.
    # For example, if file has "TIME STAMP" column and you want to keep it as "TIMESTAMP" for preview:
    if "TIME STAMP" in df.columns and "TIMESTAMP" not in df.columns:
        df["TIMESTAMP"] = df["TIME STAMP"]

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
        # show preview including TIMESTAMP (if present)
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.header("📄 Hasil BAST")

        if st.button("Generate PDF"):
            try:
                pdf_buffer = generate_pdf(df, tanggal, warehouse, courier, driver, police, total_koli)
                # filename with timezone offset if available
                try:
                    tz_suffix = tanggal.strftime("%z") if hasattr(tanggal, "tzinfo") and tanggal.tzinfo else ""
                except Exception:
                    tz_suffix = ""
                filename = f"{warehouse}_{courier}_{police}_{tanggal.strftime('%Y%m%d_%H%M%S')}{('_' + tz_suffix) if tz_suffix else ''}.pdf"
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
