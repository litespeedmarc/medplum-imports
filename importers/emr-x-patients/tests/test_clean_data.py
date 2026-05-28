from pathlib import Path
import pytest
import emr_x_patients_importer as _m; EmrXPatientsImporter = _m.EmrXPatientsImporter

CLEAN = Path(__file__).parent.parent / "samples" / "clean.csv"


def test_clean_data_bundle():
    imp = EmrXPatientsImporter(CLEAN)
    imp.validate_source()
    bundle = imp.generate_bundle()
    imp.verify_bundle()

    assert bundle["type"] == "batch"
    assert len(bundle["entry"]) == 3
    assert imp.warnings == []
    assert imp.exceptions == []


def test_clean_data_identifiers_preserved():
    imp = EmrXPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    ids = [
        e["resource"]["identifier"][0]["value"]
        for e in imp._bundle["entry"]
    ]
    assert ids == ["EMR-1001", "EMR-1002", "EMR-1003"]


def test_clean_data_idem_potent_entries():
    imp = EmrXPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    for entry in imp._bundle["entry"]:
        assert "ifNoneExist" in entry["request"]
