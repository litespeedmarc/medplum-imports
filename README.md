# medplum-imports

ETL framework for importing data into a Medplum FHIR server.

**Core principle:** Every transformation is a medical liability.
Imports must be deterministic and preserve source data fidelity.

## Usage

```bash
python run_import.py <config-type> <input-moniker>
```

`config-type` identifies both the source system and the resource type.
It must be specific — `emr-x-patients` not `csv-patients`.

```bash
python run_import.py emr-x-patients   data/export.csv
python run_import.py epic-labs        data/labs_march.csv
python run_import.py athena-encounters postgresql://localhost/athena
```

## Import Lifecycle

The framework calls these steps in order:

| Step | Method | Owner |
|---|---|---|
| 1 | `validate_source()` | Importer |
| 2 | `generate_bundle()` | Importer |
| 3 | `verify_bundle()` | Importer |
| 4 | POST bundle → `verify_import()` | Framework → Importer |

## Writing an Importer

Create `importers/{config-type}/importer.py` with a class named
`{ConfigType}Importer(BaseImporter)`:

```python
from framework import BaseImporter
from framework.exceptions import SourceValidationError, BundleValidationError, ImportVerificationError

class EmrXPatientsImporter(BaseImporter):
    def validate_source(self): ...
    def generate_bundle(self) -> dict: ...
    def verify_bundle(self): ...
    def import_bundle(self): ...   # no-op — framework posts
    def verify_import(self): ...
```

See `importers/emr-x-patients/importer.py` for a complete example.

Use `/new-importer <issue-number>` to generate an importer from a GitHub issue.

## Structure

```
framework/           Core: BaseImporter, runner, MedplumClient, exceptions
importers/           One directory per importer, named {source}-{resource}
  emr-x-patients/    Example importer
    importer.py
    log.md           Decisions, mapping rationale, test results
    samples/         Synthetic test fixtures (basic + edge-cases)
    tests/           test_clean_data.py + test_bad_data.py
edge-cases.md        Healthcare data quality reference for Ivo
infra/medplum/       Docker stack + KB docs for the local Medplum instance
run_import.py        CLI entry point
.github/workflows/   CI: tests + log.md + test file presence checks
```

### On importer logs

Each importer's `log.md` is a **first-class artifact**, not scratch space. It
captures why decisions were made, what was considered and rejected, and how the
importer reached its final form. Code is the output; the log is the reasoning.
A CI check will eventually require `log.md` to exist before an importer can merge.

## Configuration

```bash
cp .env.example .env   # then edit
```

| Variable | Default | Description |
|---|---|---|
| `MEDPLUM_BASE_URL` | `http://localhost:8103` | Medplum API |
| `MEDPLUM_EMAIL` | `admin@example.com` | Auth email |
| `MEDPLUM_PASSWORD` | `medplum_admin` | Auth password |
