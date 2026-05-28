from abc import ABC, abstractmethod
from typing import Any


class BaseImporter(ABC):
    """
    Base class for all Medplum importers.

    Every transformation is a medical liability. Importers must be deterministic
    and preserve source data fidelity. When data quality is ambiguous, the
    importer decides whether it is cleanable or not — never silently coerces.

    Row-level data quality reporting:
      _warn(row_id, msg)      — cleanable; records to self.warnings, row imports
      _reject(row_id, reason) — not-cleanable; records to self.exceptions.
                                Caller is responsible for skipping the row (continue).

    Neither method raises. The importer controls its own flow. This works for
    any source type: CSV, DB cursor, API page, etc.

    Tests assert against self.warnings and self.exceptions:
      clean data        → both empty
      cleanable data    → warnings populated, exceptions empty
      not-cleanable     → exceptions populated, bad rows absent from bundle

    Lifecycle (called by runner):
      1. validate_source()
      2. generate_bundle()
      3. verify_bundle()
      4. [framework posts bundle]
      5. verify_import()
    """

    def __init__(self, source: Any):
        self.source = source
        self._bundle: dict | None = None
        self.warnings: list[tuple[str, str]] = []    # (row_id, message)
        self.exceptions: list[tuple[str, str]] = []  # (row_id, reason)

    def _warn(self, row_id: str, message: str) -> None:
        """Cleanable issue — row imports, warning recorded."""
        self.warnings.append((row_id, message))

    def _reject(self, row_id: str, reason: str) -> None:
        """Not-cleanable — records to self.exceptions. Caller must skip the row."""
        self.exceptions.append((row_id, reason))

    @abstractmethod
    def validate_source(self) -> None:
        """File-level check — source readable and structurally sound. Raises SourceValidationError."""

    @abstractmethod
    def generate_bundle(self) -> dict:
        """Transform source → FHIR R4 Bundle. Use _warn()/_reject() for row-level issues."""

    @abstractmethod
    def verify_bundle(self) -> None:
        """Pre-flight FHIR check on self._bundle. Raises BundleValidationError."""

    def bundle_type(self) -> str:
        """'batch' (default) or 'transaction'. Override for atomic bundles."""
        return "batch"

    def import_bundle(self) -> None:
        """Framework-owned step. Do not override."""

    @abstractmethod
    def verify_import(self) -> None:
        """Query Medplum to confirm resources landed. Raises ImportVerificationError."""
