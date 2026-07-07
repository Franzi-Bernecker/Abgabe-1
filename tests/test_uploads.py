"""Tests für Upload-Validierung und -Normalisierung (EKG/GPX)."""

from cardioconnect.repositories.activities import parse_gpx_metadata
from cardioconnect.repositories.ekg_tests import (
    normalize_ekg_text,
    validate_ekg_bytes,
)


def _csv_bytes(rows: int) -> bytes:
    lines = ["idx,MLII"] + [f"{i},{0.1 * (i % 7)}" for i in range(rows)]
    return "\n".join(lines).encode()


def test_validate_ekg_accepts_numeric_csv():
    assert validate_ekg_bytes(_csv_bytes(500)) is None


def test_validate_ekg_rejects_garbage():
    assert validate_ekg_bytes(b"\x00\xff\x00\xff kein csv") is not None


def test_validate_ekg_rejects_too_few_rows():
    assert validate_ekg_bytes(_csv_bytes(50)) is not None


def test_validate_ekg_rejects_non_numeric():
    content = b"idx,text\n0,a\n1,b\n" + b"\n".join(
        f"{i},x".encode() for i in range(200)
    )
    assert validate_ekg_bytes(content) is not None


def test_normalize_converts_tabs_in_txt():
    raw = b"0\t0.1\n1\t0.2\n"
    assert normalize_ekg_text(raw, "export.txt") == b"0,0.1\n1,0.2\n"


def test_normalize_leaves_csv_untouched():
    raw = b"0,0.1\n1,0.2\n"
    assert normalize_ekg_text(raw, "export.csv") == raw


_GPX = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><name>Morgenlauf</name><type>running</type>
    <trkseg>
      <trkpt lat="47.0" lon="10.0"><ele>500</ele><time>2026-05-01T08:00:00Z</time></trkpt>
      <trkpt lat="47.001" lon="10.001"><ele>502</ele><time>2026-05-01T08:00:05Z</time></trkpt>
    </trkseg>
  </trk>
</gpx>
"""


def test_parse_gpx_metadata():
    meta = parse_gpx_metadata(_GPX)
    assert meta == {"name": "Morgenlauf", "type": "running", "date": "2026-05-01"}


def test_parse_gpx_rejects_invalid_xml():
    assert parse_gpx_metadata(b"<gpx>kaputt") is None


def test_parse_gpx_rejects_single_point_track():
    single = _GPX.replace(
        b'<trkpt lat="47.001" lon="10.001"><ele>502</ele>'
        b"<time>2026-05-01T08:00:05Z</time></trkpt>",
        b"",
    )
    assert parse_gpx_metadata(single) is None
