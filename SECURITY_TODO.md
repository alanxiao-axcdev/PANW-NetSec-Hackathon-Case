# PANW1 Security Implementation TODO

**Priority**: CRITICAL - These are security gaps that must be addressed before production

---

## CRITICAL Issues (Fix Before Demo)

### 1. Encryption Not Wired Up ⚠️ CRITICAL

**Status**: Encryption module exists but NOT integrated into journal.py

**Issue**:
- All journal entries stored in plaintext JSON
- Config says `enable_encryption: true` but it's not actually encrypting
- Files visible: `cat ~/.companion/entries/*.json` shows all content

**Fix Required**:
```python
# In companion/journal.py - save_entry()
from companion.security.encryption import encrypt_entry

if config.enable_encryption:
    # Encrypt content before saving
    encrypted_data = encrypt_entry(entry.content, passphrase)
    entry_dict["content_encrypted"] = encrypted_data
    # Don't save plaintext content
```

**Files to modify**:
- companion/journal.py (save_entry, get_entry functions)
- Add passphrase management to CLI

**Estimated time**: 4-6 hours

---

### 2. Filename Privacy Leak ⚠️ HIGH

**Issue**:
- Filenames: `20251108_101758_uuid.json`
- Timestamp reveals WHEN user wrote (metadata leak)
- Allows correlation attacks

**Fix Required**:
```python
# Use UUID-only filenames
# Old: 20251108_101758_550e8400.json
# New: 550e8400-e29b-41d4-a716-446655440000.json

# Store timestamp INSIDE encrypted entry, not in filename
```

**Files to modify**:
- companion/storage.py (file naming)
- companion/journal.py (file lookup)

**Estimated time**: 2-3 hours

---

### 3. Metrics Command Broken 🐛 MEDIUM

**Issue**:
```
companion metrics
Failed: display_metrics_dashboard() missing 1 required positional argument
```

**Fix Required**:
```python
# In companion/cli.py - metrics command
# Need to collect metrics data first
from companion.monitoring import metrics

metrics_data = metrics.get_all_metrics()
dashboard.display_metrics_dashboard(metrics_data)
```

**Files to modify**:
- companion/cli.py (metrics command)

**Estimated time**: 30 minutes (EASY FIX)

---

## Quick Wins (Implement These First)

### QW1: Fix Metrics Command (30 min)

**Implementation**:
```python
# companion/cli.py - line ~520
@main.command()
def metrics() -> None:
    from companion.monitoring import metrics as metrics_module
    
    metrics_data = metrics_module.get_all_metrics()
    dashboard.display_metrics_dashboard(metrics_data)
```

### QW2: Enforce File Permissions (1-2 hours)

**Implementation**:
```python
# In storage.py - write_json()
file_path.touch(mode=0o600)  # Owner read/write only
file_path.parent.chmod(0o700)  # Owner access only

# In companion/config.py - ensure_data_dir()
data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
```

### QW3: Audit Log Sanitization (2-3 hours)

**Implementation**:
```python
# In companion/security/audit.py
def _sanitize_details(details: dict) -> dict:
    """Remove PII from audit details before logging."""
    # Filter out: content, prompts, user text
    # Keep: IDs, counts, hashes
```

---

## Enhancement Plans (Complex Features)

### EP1: Wire Up Encryption (Priority: CRITICAL)

**Threat**: All journal data readable by anyone with file access

**Implementation Steps**:

**Phase 1: Passphrase Management** (2 hours)
```python
# Add to cli.py - first run wizard
def _setup_passphrase() -> str:
    passphrase = Prompt.ask("Create passphrase (min 12 chars)", password=True)
    confirm = Prompt.ask("Confirm passphrase", password=True)
    
    if passphrase != confirm:
        raise ValueError("Passphrases don't match")
    
    # Check strength
    if not is_passphrase_acceptable(passphrase):
        raise ValueError("Passphrase too weak")
    
    # Store hash for verification (NOT the passphrase!)
    return passphrase

# Store passphrase hash in config (for verification only)
# User must enter passphrase each session
```

**Phase 2: Integrate Encryption** (2-3 hours)
```python
# companion/journal.py - save_entry()
def save_entry(entry: JournalEntry, passphrase: str) -> str:
    if config.enable_encryption:
        # Encrypt content
        encrypted_content = encryption.encrypt_entry(entry.content, passphrase)
        
        # Save with encrypted content
        entry_dict = entry.model_dump(mode="json")
        entry_dict["content"] = None  # Remove plaintext
        entry_dict["content_encrypted"] = encrypted_content
    
    storage.write_json(entry_dict, file_path)

# companion/journal.py - get_entry()
def get_entry(entry_id: str, passphrase: str) -> JournalEntry:
    entry_dict = storage.read_json(file_path)
    
    if "content_encrypted" in entry_dict:
        # Decrypt
        entry_dict["content"] = encryption.decrypt_entry(
            entry_dict["content_encrypted"],
            passphrase
        )
    
    return JournalEntry(**entry_dict)
```

**Phase 3: CLI Passphrase Flow** (1-2 hours)
```python
# Every command that reads/writes entries needs passphrase
@main.command()
def write() -> None:
    passphrase = _get_passphrase()  # Prompt or from keyring
    # ... existing code ...
    journal.save_entry(entry, passphrase)
```

**Files to Modify**:
- companion/journal.py (save_entry, get_entry, get_entries_by_date_range)
- companion/cli.py (passphrase prompts in all commands)
- companion/config.py (passphrase verification hash)

**Testing**:
- Write entry → verify file encrypted
- Read entry → verify decrypts correctly
- Wrong passphrase → verify fails gracefully

**Estimated Total**: 5-7 hours

---

### EP2: Privacy-Preserving Filenames (Priority: HIGH)

**Threat**: Timestamps in filenames reveal when user wrote entries

**Implementation**:
```python
# Old: 20251108_101758_uuid.json
# New: uuid-only.json

# companion/storage.py
def _get_entry_filename(entry_id: str) -> str:
    return f"{entry_id}.json"  # UUID only, no timestamp

# Maintain index file for chronological access
# entries_index.json: [{"id": "uuid", "timestamp": "2025-01-08T10:17:58"}]
```

**Migration Strategy**:
```python
# One-time migration script
def migrate_filenames():
    for old_file in entries_dir.glob("*.json"):
        if "_" in old_file.stem:  # Old format
            entry = read_json(old_file)
            new_name = f"{entry['id']}.json"
            old_file.rename(entries_dir / new_name)
```

**Estimated Time**: 2-3 hours

---

### EP3: Secure Deletion (Priority: MEDIUM)

**Threat**: Deleted entries recoverable via forensics

**Implementation**:
```python
# companion/journal.py
def delete_entry(entry_id: str) -> bool:
    file_path = _get_entry_path(entry_id)
    
    if file_path.exists():
        # Overwrite with random data before deleting
        file_size = file_path.stat().st_size
        
        # 3-pass DOD 5220.22-M standard
        for _ in range(3):
            with file_path.open('wb') as f:
                f.write(os.urandom(file_size))
                f.flush()
                os.fsync(f.fileno())
        
        # Now safe to unlink
        file_path.unlink()
        return True
```

**Dependency**: `os.urandom` (stdlib, no new deps)

**Estimated Time**: 2-3 hours

---

### EP4: Model Integrity Verification (Priority: MEDIUM)

**Threat**: Compromised AI model could exfiltrate data

**Implementation**:
```python
# companion/ai_backend/qwen_provider.py
KNOWN_MODEL_HASHES = {
    "Qwen/Qwen2.5-1.5B": "sha256:abc123...",  # From HuggingFace
}

def verify_model_integrity(model_path: Path, expected_hash: str) -> bool:
    import hashlib
    
    sha256 = hashlib.sha256()
    with model_path.open('rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    
    actual_hash = sha256.hexdigest()
    
    if actual_hash != expected_hash:
        raise SecurityError("Model integrity check failed!")
    
    return True

# Call before loading model
verify_model_integrity(model_path, KNOWN_MODEL_HASHES[model_name])
```

**Estimated Time**: 3-4 hours

---

### EP5: Dependency Hash Pinning (Priority: MEDIUM)

**Current**: `click>=8.1.0` (allows any version >= 8.1.0)
**Risk**: Malicious package update could be auto-installed

**Implementation**:
```toml
# pyproject.toml
dependencies = [
    "click==8.1.7",  # Pin exact version
    # ... all deps pinned
]

# Add requirements-hashes.txt
click==8.1.7 --hash=sha256:abc123...
rich==13.7.0 --hash=sha256:def456...

# Install with hash verification
pip install --require-hashes -r requirements-hashes.txt
```

**Tooling**: Use `pip-audit` and `pip-compile` with `--generate-hashes`

**Estimated Time**: 3-4 hours

---

## Immediate Action Items (Today)

**MUST FIX BEFORE DEMO**:
1. ⚠️ Fix metrics command (30 min) - Demo will break otherwise
2. ⚠️ Enable encryption OR document it's disabled in MVP (2 hours to enable)
3. ⚠️ Fix filename privacy (2 hours) - Demonstrates security awareness

**CAN DEFER** (mention in interview as "next steps"):
- Secure deletion (talk about design)
- Model integrity (reference SECURITY_ENHANCEMENTS.md)
- Dependency hardening (talk about supply chain security)
- Timing attacks (advanced topic)

---

## Implementation Priority Matrix

| Feature | Priority | Time | Impact | Demo Value |
|---------|----------|------|--------|------------|
| Fix metrics | CRITICAL | 30m | High | Essential |
| Enable encryption | CRITICAL | 5-7h | High | Core security |
| Fix filenames | HIGH | 2-3h | Medium | Privacy demo |
| Secure deletion | MEDIUM | 2-3h | Low | Nice to have |
| Model integrity | MEDIUM | 3-4h | Medium | Advanced security |
| Dep pinning | LOW | 3-4h | Low | Supply chain talk |

---

## Recommendation

**For hackathon demo SUCCESS**:

**Fix NOW** (before demo):
1. Metrics command (30 min) ← DO THIS FIRST
2. Either enable encryption OR clearly label as "MVP - encryption designed but not wired"

**Document as "Designed"** (for interview talk):
- Reference docs/MEMORY_SECURITY.md (Layer 7)
- Reference docs/SECURITY_ENHANCEMENTS.md (comprehensive plan)
- Talk about security-by-design approach

**Your story**:
> "I built comprehensive security infrastructure. Some features like encryption are designed and tested but not fully integrated in this MVP to prioritize the demo features. The architecture is production-ready - wiring up encryption is a 4-hour task, not a fundamental redesign."

This shows: (1) Security thinking, (2) Pragmatic prioritization, (3) Production awareness

---

**Want me to fix the metrics command right now? (30 min fix)**
