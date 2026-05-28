# Healthcare Data Edge Cases

Reference for Ivo when generating test data and importer logic.
Pick the cases relevant to the source system. Document decisions in log.md.

---

## Hard Fails — raise, never import

These have ambiguous clinical meaning. A wrong guess is worse than no data.

| Case | Example | Why hard fail |
|---|---|---|
| Ambiguous date format | `12-01-2023` — Jan 12 or Dec 1? | Wrong date changes clinical record |
| Null / placeholder MRN | `000-000-000`, `UNKNOWN`, empty | Orphaned resource, untraceable |
| Orphaned reference | Medication → patient ID that doesn't exist | Broken referential integrity |
| Timezone-shifted encounter | 11:30 PM → crosses midnight on conversion | Encounter date changes |

## Soft Fails — warn + continue

Safe to import as-is. Log a warning, don't halt.

| Case | Example | Handling |
|---|---|---|
| Missing optional field | No phone number | Omit field, continue |
| Unknown coded value | Gender code `Z` | Map to `unknown`, log warning |
| Uncoded free text | Allergy: `"penicillin rash"` | Import as text, flag for review |
| Case-variant duplicate | `Metformin 500mg` vs `METFORMIN 500 mg` | Import both, flag for dedup review — do not auto-merge |

## Judgement Calls — document your decision in log.md

| Case | Tension |
|---|---|
| Duplicate patients | `Jon Smith` vs `Jonathan Smith` — same person? Cannot auto-merge patient records. Hard fail or flag for manual review. |
| Proprietary code mapping | Clinic-internal code with no standard mapping — import unmapped or reject? |
| Partial dates | `2024-03` — valid FHIR date, but is it useful? Import as-is or reject? |

---

## Principle

If a wrong guess changes clinical meaning, it is a hard fail.
If the data is genuinely missing or ambiguous in a non-clinical way, it is a soft fail.
When in doubt, raise. Document the decision.
