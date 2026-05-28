from pathlib import Path
import foo_clinic_patients_importer as _m

FooClinicPatientsImporter = _m.FooClinicPatientsImporter
SYSTEM_MRN = _m.SYSTEM_MRN

CLEAN = Path(__file__).parent.parent / "samples" / "clean.csv"


def test_clean_data_all_rows_import():
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    bundle = imp.generate_bundle()
    imp.verify_bundle()

    assert bundle["type"] == "batch"
    assert len(bundle["entry"]) == 5


def test_clean_data_no_warnings_or_exceptions():
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    assert imp.warnings == []
    assert imp.exceptions == []


def test_clean_data_mrn_identifiers_preserved():
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    mrn_ids = [
        id_["value"]
        for entry in imp._bundle["entry"]
        for id_ in entry["resource"]["identifier"]
        if id_["system"] == SYSTEM_MRN
    ]
    assert mrn_ids == [
        "MRN-200001",
        "MRN-200002",
        "MRN-200003",
        "MRN-200004",
        "MRN-200005",
    ]


def test_clean_data_idempotent_entries():
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    for entry in imp._bundle["entry"]:
        assert "ifNoneExist" in entry["request"]
        mrn = next(
            id_["value"]
            for id_ in entry["resource"]["identifier"]
            if id_["system"] == SYSTEM_MRN
        )
        assert entry["request"]["ifNoneExist"] == f"identifier={SYSTEM_MRN}|{mrn}"


def test_clean_data_gender_values_valid():
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    for entry in imp._bundle["entry"]:
        gender = entry["resource"].get("gender")
        if gender is not None:
            assert gender in ("male", "female", "other", "unknown")


def test_clean_data_language_mapped():
    """All four language codes present in clean.csv should map to BCP-47 tags."""
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    lang_codes = [
        entry["resource"]["communication"][0]["language"]["coding"][0]["code"]
        for entry in imp._bundle["entry"]
        if "communication" in entry["resource"]
    ]
    assert set(lang_codes) == {"fr", "en", "es", "ar"}


def test_clean_data_birthdate_format():
    imp = FooClinicPatientsImporter(CLEAN)
    imp.validate_source()
    imp.generate_bundle()

    from datetime import datetime
    for entry in imp._bundle["entry"]:
        dob = entry["resource"].get("birthDate")
        if dob:
            # Must parse without error as YYYY-MM-DD
            datetime.strptime(dob, "%Y-%m-%d")
