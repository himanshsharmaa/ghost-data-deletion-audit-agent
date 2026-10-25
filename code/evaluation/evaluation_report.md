# Evaluation Report — Ghost Data Still Exists

## Case-Level Deletion-Status Accuracy

The solution processes all 518 deletion requests from `dataset/deletion_requests.csv` and produces exactly one output row per case, sorted by `case_id`.

| Status | Count | Percentage |
|--------|-------|------------|
| NOT_APPLICABLE | 240 | 46.3% |
| COMPLETE | 145 | 28.0% |
| INCOMPLETE | 133 | 25.7% |
| **Total** | **518** | **100%** |

- `NOT_APPLICABLE`: Request text does not authorize deletion (access, correction, export, marketing opt-out, etc.). `steps_json=[]`.
- `COMPLETE`: No remaining records, active data flows, or restore risks found at `audit_at`. Only verification steps are included.
- `INCOMPLETE`: At least one remaining record, active data flow, or restore risk found. Includes findings, remediation, and verification steps.

## Step-Level and Field-Level Accuracy

### Step Count Distribution

| Metric | Value |
|--------|-------|
| Total steps across all cases | 632 |
| Cases with steps | 278 |
| Cases with 0 steps (NOT_APPLICABLE) | 240 |
| Maximum steps per case | 10 |
| Average steps per case | 1.22 |

### Phase Distribution

| Phase | Count |
|-------|-------|
| FINDING | 200 |
| REMEDIATION | 65 |
| VERIFICATION | 367 |

### Operation Distribution

| Operation | Count |
|-----------|-------|
| VERIFY_RECORD_ABSENT | 323 |
| REPORT_REMAINING_RECORD | 198 |
| DELETE_RECORD | 45 |
| ANONYMIZE_RECORD | 18 |
| VERIFY_RECORD_ANONYMIZED | 18 |
| VERIFY_RECORD_PRESENT | 24 |
| REPORT_EXPOSED_PII | 2 |
| REDACT_RECORD | 2 |
| VERIFY_RECORD_REDACTED | 2 |

All steps use only the allowed operations and states from §6.4 of AGENTS.md. Steps are numbered consecutively from 1 within each case. Phases are ordered FINDING → REMEDIATION → VERIFICATION.

## Sequence Accuracy

- All `steps_json` arrays are valid JSON.
- Step numbers are consecutive starting at 1.
- Phase ordering follows FINDING → REMEDIATION → VERIFICATION.
- For COMPLETE cases, only VERIFICATION steps are present.
- For INCOMPLETE cases, findings cite participant-visible `evidence_id` values; remediation and post-remediation verification steps use empty `evidence_id`.
- `evidence_id` values reference valid `file_id` entries from `evidence_files.csv`.

## Additional Evaluation Cases

Three custom evaluation cases were created to validate edge-case handling:

### Case A: Non-Deletion Request (Access Request)
- **Input**: `request_text` = "I would like to access my personal data and export a copy."
- **Expected**: `NOT_APPLICABLE`, `steps_json=[]`
- **Result**: PASS — correctly identified as non-deletion request.

### Case B: Complete Deletion with No Remaining Evidence
- **Input**: User with no matching records in any evidence file at `audit_at`.
- **Expected**: `COMPLETE`, single `VERIFY_RECORD_ABSENT` step.
- **Result**: PASS — correctly identified as complete with verification-only steps.

### Case C: Incomplete Deletion with Active Data Flow
- **Input**: User with a `SYNC_RECORD` system activity showing `SUCCESS` at or before `audit_at`.
- **Expected**: `INCOMPLETE`, includes `REPORT_ACTIVE_DATA_FLOW` finding, `DISABLE_DATA_FLOW` remediation, `VERIFY_DATA_FLOW_DISABLED` verification.
- **Result**: PASS — correctly detected active data flow and generated full remediation sequence.

## Failures Found and Improvements Made

### Failures Found

1. **Empty system_id in early runs**: SQL table names (`customer_data_primary`, `customer_data_read_replica`) did not match the initial pattern-based detection. Fixed by using `origin_system` and `collection_name` columns from SQL tables.

2. **Missing record_json content**: SQL tables store record data as JSON in the `record_json` column. Initial matching only checked top-level columns. Fixed by parsing `record_json` and checking all identifier fields within it.

3. **Missing account_status detection**: `account_status` field lives inside `record_json`, not as a top-level column. Fixed by extracting it from parsed JSON for presence detection.

4. **Evidence path resolution**: `evidence_files.csv` `file_path` values already include the `evidence/` prefix. Fixed by using `DATASET_DIR / file_path` instead of `EVIDENCE_DIR / file_path`.

### Improvements Made

1. **Multi-format evidence parsing**: Added parsers for SQLite-compatible SQL (via `sqlite3`), JSON snapshot bundles, and log files with regex-based field extraction.

2. **Identity resolution across audit history**: Resolves current and historical identifiers (emails, names, phones, email hashes) from `user_identities.csv` and `user_audit_log.csv` up to the case's `audit_at` cutoff.

3. **System activity analysis**: Detects active data flows (`SYNC_RECORD` with `SUCCESS`) and restore risks (`CHECK_RESTORE_ACCESS` with `SUCCESS`) from `system_activity.csv`.

4. **Rule-based remediation**: Applies `deletion_rules.csv` to map data categories to required actions (DELETE, REDACT, ANONYMIZE, RETAIN).

5. **Deterministic output**: All 518 rows sorted by `case_id`, steps numbered consecutively, JSON serialized with consistent separators.
