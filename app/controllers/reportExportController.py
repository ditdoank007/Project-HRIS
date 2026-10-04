"""
Global report export presentation standard for HRIS Reborn.

Single source of truth for report colors and legend semantics.
PDF and Excel exporters should consume these definitions instead of
declaring their own color palettes.
"""

from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors


REPORT_COLORS = {
    "header": "172033",
    "holiday": "B91C1C",
    "siaga": "15803D",
    "blue": "2563EB",
    "orange": "B45309",
    "wfh": "475569",
    "normal": "172033",
    "zebra": "EEF2F7",
    "grid": "D5DBE3",
}


REPORT_LEGEND = (
    ("holiday", "HARI LIBUR"),
    ("siaga", "SIAGA"),
    ("blue", "SPRIN/DL TIDAK MEMOTONG UANG MAKAN"),
    ("orange", "SPRIN/DL MEMOTONG UANG MAKAN"),
    ("wfh", "ABSEN ONLINE WFH"),
)


def excel_font_color(color_key):
    """Return an OpenPyXL-compatible ARGB font color."""
    return "FF" + REPORT_COLORS.get(color_key, REPORT_COLORS["normal"])


def excel_fill(color_key):
    """Return a solid OpenPyXL fill using the global report palette."""
    value = REPORT_COLORS.get(color_key, REPORT_COLORS["normal"])
    return PatternFill(
        start_color=value,
        end_color=value,
        fill_type="solid",
    )


def pdf_color(color_key):
    """Return a ReportLab color using the global report palette."""
    value = REPORT_COLORS.get(color_key, REPORT_COLORS["normal"])
    return colors.HexColor("#" + value)


def add_excel_legend(ws, start_row, label_column=3, color_column=2):
    """Render the standard report legend in an Excel worksheet."""
    row = start_row

    for color_key, label in REPORT_LEGEND:
        color_cell = ws.cell(row=row, column=color_column)
        color_cell.fill = excel_fill(color_key)
        color_cell.font = Font(
            color="FFFFFFFF",
            bold=True,
        )

        label_cell = ws.cell(row=row, column=label_column, value=label)
        label_cell.font = Font(bold=True)
        row += 1

    return row


def pdf_legend_text():
    """Return the standard legend as plain text for PDF rendering."""
    return (
        "Keterangan: merah = hari libur, hijau = Siaga, "
        "biru = SPRIN/DL tidak memotong Uang Makan, "
        "oranye = SPRIN/DL memotong Uang Makan, "
        "abu-abu = Absen Online WFH."
    )
