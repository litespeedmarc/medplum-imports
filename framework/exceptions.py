class SourceValidationError(Exception):
    """File-level hard fail — source is unreadable or structurally invalid. Always aborts."""

class BundleValidationError(Exception):
    """Generated FHIR bundle fails pre-flight checks."""

class ImportVerificationError(Exception):
    """Resources did not land in Medplum as expected after import."""

class ImporterNotFoundError(Exception):
    """No importer found for the given config-type."""
