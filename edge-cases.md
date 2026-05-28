# Healthcare Data Edge Cases

Reference for Ivo when generating samples and importer logic.
Read this before Phase 3. Identify which cases apply to the source system.
Document decisions (and why) in log.md.

---

## Three data tiers

| Tier | Exception | DEV mode | PROD mode |
|---|---|---|---|
| Clean | — | imports | imports |
| Cleanable | `CleanableDataWarning` | raises immediately | normalizes, records warning, imports |
| Not-cleanable | `UncleanableDataError` | row skipped, recorded in exceptions | row skipped, recorded in exceptions |

In the importer: use `self._warn(row_id, msg)` for cleanable, `self._reject(row_id, reason)` for not-cleanable.

---

## Cleanable — safe to normalize

Clinical meaning is unambiguous; transformation is safe.

| Case | Example | Handling |
|---|---|---|
| Unknown coded value | Gender `Z` or `"Unknown"` | Map to `None`/`unknown`, warn |
| Missing optional field | No phone number | Omit field, warn if unexpected |
| Whitespace / case on non-clinical fields | `" SMITH "`, `"smith"` | Strip/normalize, warn |
| Free-text allergy | `"penicillin rash"` | Import as text, warn — flag for coding review |

## Not-cleanable — always reject

A wrong guess changes clinical meaning. Reject in all modes.

| Case | Example | Why |
|---|---|---|
| Ambiguous date format | `12-01-2023` — Jan 12 or Dec 1? | Wrong date changes clinical record |
| Null / placeholder MRN | `000-000-000`, `UNKNOWN`, empty | Orphaned resource, untraceable |
| Orphaned reference | Medication → patient ID that doesn't exist | Broken referential integrity |
| Timezone-shifted encounter | 11:30 PM → crosses midnight | Encounter date changes |
| Case-variant duplicate | `Metformin 500mg` vs `METFORMIN 500 mg` | Cannot auto-merge clinical records |

## Judgement calls — document decision in log.md

| Case | Tension |
|---|---|
| Duplicate patients | `Jon Smith` vs `Jonathan Smith` — same person? Cannot auto-merge. Reject or flag. |
| Proprietary code mapping | Clinic-internal code with no standard mapping — import unmapped or reject? |
| Partial dates | `2024-03` — valid FHIR date, but is it useful? Import as-is or reject? |

---

## Principle

If a wrong guess changes clinical meaning → not-cleanable → `_reject()`.
If the transformation is unambiguous and safe → cleanable → `_warn()`.
When in doubt, reject. Document the decision.
