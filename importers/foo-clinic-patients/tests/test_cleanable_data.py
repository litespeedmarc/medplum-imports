from pathlib import Path
import foo_clinic_patients_importer as _m

FooClinicPatientsImporter = _m.FooClinicPatientsImporter
SYSTEM_MRN = _m.SYSTEM_MRN
SYSTEM_HEALTH_CARD = _m.SYSTEM_HEALTH_CARD

CLEANABLE = Path(__file__).parent.parent / "samples" / "cleanable.csv"


def test_cleanable_all_rows_import():
    """All 5 rows in cleanable.csv must import — none are rejected."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    assert imp.exceptions == []
    assert len(imp._bundle["entry"]) == 5


def test_cleanable_warnings_populated():
    """Warnings must fire — this file has cleanable issues in every row."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    assert len(imp.warnings) > 0


def test_cleanable_whitespace_stripped_from_names():
    """Row 6 has leading/trailing whitespace on first_name and last_name."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    # Find MRN-200006
    entry = next(
        e for e in imp._bundle["entry"]
        if any(id_["system"] == SYSTEM_MRN and id_["value"] == "MRN-200006"
               for id_ in e["resource"]["identifier"])
    )
    name = entry["resource"]["name"][0]
    assert name["family"] == "Garcia"
    assert name["given"] == ["Maria"]

    # Warn fired for whitespace
    warn_msgs = [msg for _, msg in imp.warnings]
    assert any("whitespace" in m and "Garcia" in m or "whitespace" in m and "Maria" in m
               for m in warn_msgs)


def test_cleanable_placeholder_health_card_omitted():
    """Row 8 has health_card_number '000-000-000' — identifier entry must be omitted, warn fired."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    entry = next(
        e for e in imp._bundle["entry"]
        if any(id_["system"] == SYSTEM_MRN and id_["value"] == "MRN-200008"
               for id_ in e["resource"]["identifier"])
    )
    hc_ids = [id_ for id_ in entry["resource"]["identifier"] if id_["system"] == SYSTEM_HEALTH_CARD]
    assert hc_ids == []

    warn_msgs = [msg for _, msg in imp.warnings]
    assert any("000-000-000" in m for m in warn_msgs)


def test_cleanable_missing_first_name_warns():
    """Row 9 has no first_name — field omitted from name, warning fires."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    entry = next(
        e for e in imp._bundle["entry"]
        if any(id_["system"] == SYSTEM_MRN and id_["value"] == "MRN-200009"
               for id_ in e["resource"]["identifier"])
    )
    # 'given' key should be absent
    assert "given" not in entry["resource"]["name"][0]

    warn_msgs = [msg for _, msg in imp.warnings]
    assert any("first_name" in m for m in warn_msgs)


def test_cleanable_unknown_gender_maps_to_unknown():
    """Row 10 has gender 'EXTRATERRESTRIAL' — must map to 'unknown', warn fires."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    entry = next(
        e for e in imp._bundle["entry"]
        if any(id_["system"] == SYSTEM_MRN and id_["value"] == "MRN-200010"
               for id_ in e["resource"]["identifier"])
    )
    assert entry["resource"]["gender"] == "unknown"

    warn_msgs = [msg for _, msg in imp.warnings]
    # The importer lowercases the raw value before the lookup, so the warning
    # contains the normalised form "extraterrestrial", not the original casing.
    assert any("extraterrestrial" in m.lower() for m in warn_msgs)


def test_cleanable_allergies_warn_fires():
    """Rows with non-null allergies must trigger a per-row warning."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    warn_msgs = [msg for _, msg in imp.warnings]
    assert any("allergies" in m for m in warn_msgs)


def test_cleanable_medications_warn_fires():
    """Rows with non-null medications must trigger a per-row warning."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    warn_msgs = [msg for _, msg in imp.warnings]
    assert any("medications" in m for m in warn_msgs)


def test_cleanable_all_genders_valid_fhir():
    """Every imported row must have a FHIR-valid gender if gender is set."""
    imp = FooClinicPatientsImporter(CLEANABLE)
    imp.validate_source()
    imp.generate_bundle()

    for entry in imp._bundle["entry"]:
        gender = entry["resource"].get("gender")
        if gender is not None:
            assert gender in ("male", "female", "other", "unknown")
