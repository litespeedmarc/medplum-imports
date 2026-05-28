from pathlib import Path
import foo_clinic_patients_importer as _m

FooClinicPatientsImporter = _m.FooClinicPatientsImporter
SYSTEM_MRN = _m.SYSTEM_MRN

NOT_CLEANABLE = Path(__file__).parent.parent / "samples" / "not-cleanable.csv"


def test_not_cleanable_exceptions_populated():
    """4 rows in not-cleanable.csv must be rejected."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    assert len(imp.exceptions) == 4


def test_not_cleanable_ambiguous_date_rejected():
    """Row 11: MM/DD/YYYY date '03/12/1978' is ambiguous — must be rejected."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    rejected_ids = [row_id for row_id, _ in imp.exceptions]
    assert "MRN-200011" in rejected_ids

    reasons = {row_id: reason for row_id, reason in imp.exceptions}
    assert "not-cleanable" in reasons["MRN-200011"] or "ambiguous" in reasons["MRN-200011"]


def test_not_cleanable_partial_date_rejected():
    """Row 12: partial date '2024-03' (YYYY-MM, no day) — must be rejected."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    rejected_ids = [row_id for row_id, _ in imp.exceptions]
    assert "MRN-200012" in rejected_ids

    reasons = {row_id: reason for row_id, reason in imp.exceptions}
    assert "partial" in reasons["MRN-200012"] or "not-cleanable" in reasons["MRN-200012"]


def test_not_cleanable_blank_mrn_rejected():
    """Row 13: blank MRN — must be rejected as untrackable."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    rejected_ids = [row_id for row_id, _ in imp.exceptions]
    # blank mrn shows up as "?" in exceptions
    assert "?" in rejected_ids or "" in rejected_ids


def test_not_cleanable_placeholder_mrn_rejected():
    """Row 14: MRN 'UNKNOWN' — must be rejected as untrackable."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    rejected_ids = [row_id for row_id, _ in imp.exceptions]
    assert "UNKNOWN" in rejected_ids


def test_not_cleanable_import_continues_past_bad_rows():
    """Row 15 is a valid control row — it must import despite all the bad neighbours."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    imported_mrns = [
        id_["value"]
        for entry in imp._bundle["entry"]
        for id_ in entry["resource"]["identifier"]
        if id_["system"] == SYSTEM_MRN
    ]
    assert "MRN-200015" in imported_mrns
    assert len(imp._bundle["entry"]) == 1


def test_not_cleanable_bad_rows_absent_from_bundle():
    """None of the 4 rejected rows should appear in the bundle."""
    imp = FooClinicPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    imported_mrns = [
        id_["value"]
        for entry in imp._bundle["entry"]
        for id_ in entry["resource"]["identifier"]
        if id_["system"] == SYSTEM_MRN
    ]
    # All four rejected rows must be absent — date rejections and MRN rejections alike.
    for bad_mrn in ("MRN-200011", "MRN-200012", "UNKNOWN"):
        assert bad_mrn not in imported_mrns
    # Blank MRN row never gets an MRN identifier entry, so verify no nameless entry slipped in.
    assert len(imp._bundle["entry"]) == 1
