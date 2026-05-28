from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from .exceptions import CleanableDataWarning, UncleanableDataError


class ImportMode(Enum):
    DEV  = "dev"   # strict — CleanableDataWarning raises immediately
    PROD = "prod"  # lenient — cleanable rows normalize+warn; uncleanable rows go to exceptions


class BaseImporter(ABC):
    """
    Base class for all Medplum importers.

    Every transformation is a medical liability. Importers must be deterministic
    and preserve source data fidelity. When data quality is ambiguous, the
    importer decides whether it is cleanable or not — never silently coerces.

    Modes:
      DEV  — strict. Use in tests. CleanableDataWarning raises like an error.
      PROD — lenient. Cleanable rows normalize and continue. Uncleanable rows
             are captured in self.exceptions and skipped. Import continues.

    Lifecycle (called by runner):
      1. validate_source()
      2. generate_bundle()
      3. verify_bundle()
      4. [framework posts bundle]
      5. verify_import()
    """

    def __init__(self, source: Any, mode: ImportMode = ImportMode.DEV):
        self.source = source
        self.mode = mode
        self._bundle: dict | None = None
        self.warnings: list[tuple[str, str]] = []    # (row_id, message)
        self.exceptions: list[tuple[str, str]] = []  # (row_id, reason)

    def _warn(self, row_id: str, message: str) -> None:
        """Cleanable issue. DEV: raises. PROD: records warning, continues."""
        if self.mode == ImportMode.DEV:
            raise CleanableDataWarning(f"{row_id}: {message}")
        self.warnings.append((row_id, message))

    def _reject(self, row_id: str, reason: str) -> None:
        """Uncleanable issue. Both modes: records to exceptions, caller must skip row."""
        self.exceptions.append((row_id, reason))
        raise UncleanableDataError(f"{row_id}: {reason}")

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
