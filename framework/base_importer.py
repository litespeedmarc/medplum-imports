from abc import ABC, abstractmethod
from typing import Any


class BaseImporter(ABC):
    """
    Base class for all Medplum importers.

    Contract:
      - Imports MUST be deterministic: same input always produces the same bundle.
      - Data MUST stay as true to the source as possible. Every transformation
        is a medical liability. If a value cannot be mapped cleanly, raise rather
        than guess.
      - The framework calls methods in this order:
          1. validate_source()
          2. generate_bundle()
          3. verify_bundle()
          4. [framework posts bundle to Medplum]
          5. verify_import()
    """

    def __init__(self, source: Any):
        self.source = source
        self._bundle: dict | None = None

    @abstractmethod
    def validate_source(self) -> None:
        """
        Confirm the source is readable and structurally sound.
        Does NOT transform data — only inspects.
        Raise SourceValidationError with a specific message on failure.
        """

    @abstractmethod
    def generate_bundle(self) -> dict:
        """
        Transform source data into a FHIR R4 Bundle dict (type from bundle_type()).
        Must be deterministic.
        Store result in self._bundle and return it.
        """

    @abstractmethod
    def verify_bundle(self) -> None:
        """
        Verify self._bundle is valid FHIR before it touches Medplum.
        Check required fields, reference integrity, and code system values.
        Raise BundleValidationError with specifics on failure.
        """

    def bundle_type(self) -> str:
        """
        FHIR bundle type to use when posting to Medplum.

        'batch'       — entries are independent; Medplum processes each one
                        separately and returns per-entry status. One bad row
                        does not block others. Default.

        'transaction' — atomic; all entries commit or none do. Use when entries
                        have dependencies (e.g. Encounter references a Patient
                        in the same bundle).

        Override to return 'transaction' when atomicity is required.
        """
        return "batch"

    def import_bundle(self) -> None:
        """Framework-owned step. Do not override."""

    @abstractmethod
    def verify_import(self) -> None:
        """
        Confirm the import landed correctly in Medplum.
        Query Medplum to check expected resources exist with correct data.
        Raise ImportVerificationError on failure.
        """
