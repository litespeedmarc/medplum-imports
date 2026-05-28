from pathlib import Path
import emr_x_patients_importer as _m; EmrXPatientsImporter = _m.EmrXPatientsImporter

CLEANABLE = Path(__file__).parent.parent / "samples" / "cleanable.csv"


def test_cleanable_data_imports_with_warnings():
    imp = EmrXPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    # All rows import — nothing rejected
    assert imp.exceptions == []
    assert len(imp._bundle["entry"]) == 3


def test_cleanable_data_warns():
    imp = EmrXPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    # Warnings fired for missing names and unknown gender codes
    assert len(imp.warnings) > 0
    warning_messages = [msg for _, msg in imp.warnings]
    assert any("last_name" in m or "first_name" in m or "gender" in m for m in warning_messages)


def test_cleanable_unknown_gender_maps_to_unknown():
    imp = EmrXPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    genders = [
        e["resource"].get("gender")
        for e in imp._bundle["entry"]
        if e["resource"].get("gender")
    ]
    assert all(g in ("male", "female", "other", "unknown") for g in genders)
