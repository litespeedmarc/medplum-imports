from pathlib import Path
import emr_x_patients_importer as _m; EmrXPatientsImporter = _m.EmrXPatientsImporter

NOT_CLEANABLE = Path(__file__).parent.parent / "samples" / "not-cleanable.csv"


def test_not_cleanable_rows_go_to_exceptions():
    imp = EmrXPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    # All 3 rows are rejected — ambiguous date, (valid row used as control won't
    # appear here), placeholder MRN
    assert len(imp.exceptions) == 2  # EMR-3001 (bad date) + UNKNOWN (placeholder MRN)


def test_not_cleanable_import_continues_past_bad_rows():
    imp = EmrXPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    # EMR-3002 has a valid date and real MRN — should import despite bad neighbours
    assert len(imp._bundle["entry"]) == 1
    assert imp._bundle["entry"][0]["resource"]["identifier"][0]["value"] == "EMR-3002"


def test_not_cleanable_exception_details():
    imp = EmrXPatientsImporter(NOT_CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    rejected_ids = [row_id for row_id, _ in imp.exceptions]
    assert "EMR-3001" in rejected_ids
    assert "UNKNOWN" in rejected_ids
