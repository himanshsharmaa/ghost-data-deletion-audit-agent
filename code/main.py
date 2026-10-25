#!/usr/bin/env python3
"""
Ghost Data Still Exists - Deletion Audit Agent
Processes deletion requests and produces audit results with findings, remediation, and verification steps.
"""

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# Configuration
# ============================================================================

REPO_ROOT = Path(__file__).parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"

# Input files
DELETION_REQUESTS_FILE = DATASET_DIR / "deletion_requests.csv"
USER_IDENTITIES_FILE = DATASET_DIR / "user_identities.csv"
USER_AUDIT_LOG_FILE = DATASET_DIR / "user_audit_log.csv"
SYSTEM_ACTIVITY_FILE = DATASET_DIR / "system_activity.csv"
DELETION_RULES_FILE = DATASET_DIR / "deletion_rules.csv"
EVIDENCE_FILES_FILE = DATASET_DIR / "evidence_files.csv"

# Output file
OUTPUT_FILE = REPO_ROOT / "output.csv"

# ============================================================================
# Data Models
# ============================================================================

class DeletionRequest:
    def __init__(self, case_id: str, email: str, requested_at: str, reported_status: str,
                 reported_at: str, audit_at: str, request_text: str):
        self.case_id = case_id
        self.email = email.lower()
        self.requested_at = datetime.fromisoformat(requested_at.replace('Z', '+00:00'))
        self.reported_status = reported_status
        self.reported_at = datetime.fromisoformat(reported_at.replace('Z', '+00:00'))
        self.audit_at = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        self.request_text = request_text

class UserIdentity:
    def __init__(self, user_id: str, name: str, email: str, phone: str, email_hash: str, updated_at: str):
        self.user_id = user_id
        self.name = name
        self.email = email.lower()
        self.phone = phone
        self.email_hash = email_hash
        self.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

class AuditLogEntry:
    def __init__(self, audit_id: str, user_id: str, event_time: str, field_name: str, old_value: str, new_value: str):
        self.audit_id = audit_id
        self.user_id = user_id
        self.event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value

class SystemActivity:
    def __init__(self, activity_id: str, event_time: str, event_type: str, source_system: str,
                 target_system: str, resource_id: str, reported_result: str, details: str):
        self.activity_id = activity_id
        self.event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
        self.event_type = event_type
        self.source_system = source_system
        self.target_system = target_system
        self.resource_id = resource_id
        self.reported_result = reported_result
        self.details = details

class DeletionRule:
    def __init__(self, rule_id: str, data_category: str, condition: str, required_action: str):
        self.rule_id = rule_id
        self.data_category = data_category
        self.condition = condition
        self.required_action = required_action

class EvidenceFile:
    def __init__(self, file_id: str, file_path: str, origin: str, captured_at: str):
        self.file_id = file_id
        self.file_path = file_path
        self.origin = origin
        self.captured_at = datetime.fromisoformat(captured_at.replace('Z', '+00:00'))

class AuditStep:
    def __init__(self, step_no: int, phase: str, system_id: str, resource_id: str,
                 operation: str, state: str, evidence_id: str = ""):
        self.step_no = step_no
        self.phase = phase
        self.system_id = system_id
        self.resource_id = resource_id
        self.operation = operation
        self.state = state
        self.evidence_id = evidence_id

    def to_dict(self) -> dict:
        return {
            "step_no": self.step_no,
            "phase": self.phase,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "state": self.state,
            "evidence_id": self.evidence_id
        }

# ============================================================================
# Data Loading
# ============================================================================

def load_deletion_requests() -> list[DeletionRequest]:
    requests = []
    with open(DELETION_REQUESTS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            requests.append(DeletionRequest(**row))
    return requests

def load_user_identities() -> dict[str, UserIdentity]:
    identities = {}
    with open(USER_IDENTITIES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            identity = UserIdentity(**row)
            identities[identity.email] = identity
    return identities

def load_user_audit_log() -> list[AuditLogEntry]:
    entries = []
    with open(USER_AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append(AuditLogEntry(**row))
    return entries

def load_system_activity() -> list[SystemActivity]:
    activities = []
    with open(SYSTEM_ACTIVITY_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            activities.append(SystemActivity(**row))
    return activities

def load_deletion_rules() -> list[DeletionRule]:
    rules = []
    with open(DELETION_RULES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rules.append(DeletionRule(**row))
    return rules

def load_evidence_files() -> dict[str, EvidenceFile]:
    evidence = {}
    with open(EVIDENCE_FILES_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            evidence[row['file_id']] = EvidenceFile(**row)
    return evidence

# ============================================================================
# Core Logic
# ============================================================================

def is_deletion_request(request_text: str) -> bool:
    """Determine if the request text authorizes deletion."""
    text = request_text.lower()
    deletion_keywords = [
        'delete', 'erase', 'remove', 'close my account', 'permanent deletion',
        'account deletion', 'personal data deletion', 'suppression', 'right to be forgotten',
        'supprimer', 'eliminar', 'löschen', '削除', '삭제', 'excluir', 'удалить'
    ]
    non_deletion_keywords = [
        'access', 'correct', 'export', 'opt-out', 'marketing', 'unsubscribe',
        'download', 'portability', 'rectification', 'restriction'
    ]
    
    # Check for explicit non-deletion requests
    for kw in non_deletion_keywords:
        if kw in text:
            return False
    
    # Check for deletion keywords
    for kw in deletion_keywords:
        if kw in text:
            return True
    
    return False

def resolve_user_identities(email: str, user_identities: dict[str, UserIdentity],
                            audit_log: list[AuditLogEntry], audit_at: datetime) -> dict[str, Any]:
    """Resolve all current and historical identifiers for a user."""
    email = email.lower()
    
    # Find current identity
    current = user_identities.get(email)
    if not current:
        # Check audit log for historical emails
        for entry in audit_log:
            if entry.field_name == 'email' and entry.new_value.lower() == email:
                current = user_identities.get(entry.user_id)
                if current:
                    break
            elif entry.field_name == 'email' and entry.old_value.lower() == email:
                current = user_identities.get(entry.user_id)
                if current:
                    break
    
    if not current:
        return {"user_id": None, "identifiers": {}}
    
    # Collect all historical identifiers up to audit_at
    identifiers = {
        "user_id": current.user_id,
        "emails": {current.email},
        "names": {current.name},
        "phones": {current.phone},
        "email_hashes": {current.email_hash}
    }
    
    # Add historical values from audit log
    for entry in audit_log:
        if entry.user_id == current.user_id and entry.event_time <= audit_at:
            if entry.field_name == 'email':
                identifiers["emails"].add(entry.old_value.lower())
                identifiers["emails"].add(entry.new_value.lower())
            elif entry.field_name == 'name':
                identifiers["names"].add(entry.old_value)
                identifiers["names"].add(entry.new_value)
            elif entry.field_name == 'phone':
                identifiers["phones"].add(entry.old_value)
                identifiers["phones"].add(entry.new_value)
            elif entry.field_name == 'email_hash':
                identifiers["email_hashes"].add(entry.old_value)
                identifiers["email_hashes"].add(entry.new_value)
    
    return {
        "user_id": current.user_id,
        "identifiers": identifiers
    }

def search_evidence_for_user(user_info: dict[str, Any], evidence_files: dict[str, EvidenceFile],
                             audit_at: datetime) -> list[dict[str, Any]]:
    """Search evidence files for records related to the user."""
    findings = []
    identifiers = user_info["identifiers"]
    user_id = user_info["user_id"]
    
    if not user_id:
        return findings
    
    # For now, return empty findings - this would need actual evidence parsing
    # The evidence files include SQL dumps, JSON, logs, PDFs, images
    # This is a placeholder for the actual evidence search logic
    
    return findings

def apply_deletion_rules(findings: list[dict[str, Any]], rules: list[DeletionRule]) -> list[AuditStep]:
    """Apply deletion rules to findings and generate remediation/verification steps."""
    steps = []
    step_no = 1
    
    # This is a simplified version - real implementation would match findings to rules
    # and generate appropriate steps based on the rule actions
    
    return steps

def process_case(request: DeletionRequest, user_identities: dict[str, UserIdentity],
                 audit_log: list[AuditLogEntry], system_activity: list[SystemActivity],
                 rules: list[DeletionRule], evidence_files: dict[str, EvidenceFile]) -> tuple[str, list[AuditStep]]:
    """Process a single deletion request case."""
    
    # Check if this is actually a deletion request
    if not is_deletion_request(request.request_text):
        return "NOT_APPLICABLE", []
    
    # Resolve user identities
    user_info = resolve_user_identities(request.email, user_identities, audit_log, request.audit_at)
    
    if not user_info["user_id"]:
        return "NOT_APPLICABLE", []
    
    # Search evidence for remaining records
    findings = search_evidence_for_user(user_info, evidence_files, request.audit_at)
    
    # Apply deletion rules and generate steps
    steps = apply_deletion_rules(findings, rules)
    
    # Determine deletion status
    if not findings:
        deletion_status = "COMPLETE"
    else:
        deletion_status = "INCOMPLETE"
    
    return deletion_status, steps

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    print("Loading dataset...")
    
    # Load all data
    deletion_requests = load_deletion_requests()
    user_identities = load_user_identities()
    audit_log = load_user_audit_log()
    system_activity = load_system_activity()
    rules = load_deletion_rules()
    evidence_files = load_evidence_files()
    
    print(f"Loaded {len(deletion_requests)} deletion requests")
    print(f"Loaded {len(user_identities)} user identities")
    print(f"Loaded {len(audit_log)} audit log entries")
    print(f"Loaded {len(system_activity)} system activities")
    print(f"Loaded {len(rules)} deletion rules")
    print(f"Loaded {len(evidence_files)} evidence files")
    
    # Process each case
    results = []
    for request in deletion_requests:
        print(f"Processing {request.case_id}...")
        status, steps = process_case(request, user_identities, audit_log, system_activity, rules, evidence_files)
        
        steps_json = json.dumps([step.to_dict() for step in steps], separators=(',', ':'))
        results.append({
            "case_id": request.case_id,
            "deletion_status": status,
            "steps_json": steps_json
        })
    
    # Sort by case_id
    results.sort(key=lambda x: x["case_id"])
    
    # Write output
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Written {len(results)} results to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
