# Security Fixes Required

## Overview

This document tracks the security enhancements needed for the Companion journaling application. It outlines what has been fixed, what remains, and the security posture of each component.

**Last Updated**: 2025-11-08

---

##  FIXED: Critical Entry Metadata Encryption Vulnerability

### Issue
Entry files exposed sensitive metadata in plaintext:
- Timestamps
- Sentiment analysis results  
- Themes (topics like "work", "health", "relationships")
- AI-generated prompts
- Session duration

### Fix Applied (2025-11-08)
**Status**:  COMPLETE

**Changes**:
1. **Full Entry Encryption**: Entire entry (content + all metadata) now encrypted as single blob
2. **Minimal Storage Format**: Only safe fields stored in plaintext:
   ```json
   {
     "id": "uuid",              // Required for file lookup
     "encrypted": true,         // Flag  
     "salt": "base64",          // Required for decryption
     "nonce": "base64",         // Required for decryption
     "ciphertext": "base64"     // ALL entry data encrypted here
   }
   ```
3. **Backward Compatibility**: Reads legacy content-only encrypted entries correctly
4. **Test Coverage**: 7 new tests verify no metadata leaks

**Files Modified**:
- `/companion/security/encryption.py` - Added `encrypt_full_entry_to_dict()` and `decrypt_full_entry_from_dict()`
- `/companion/journal.py` - Updated to use full metadata encryption
- `/tests/test_full_metadata_encryption.py` - Comprehensive tests

**Verification**:
```bash
uv run pytest tests/test_full_metadata_encryption.py -v
#  7/7 tests pass
```

---

## 🔍 Audit Log Encryption Status

### Current State
**Audit log encryption EXISTS but appears UNUSED**

**Evidence**:
- `companion/security/audit.py` contains:
  - `log_event_encrypted()` (line 353) - Encrypts events with AES-256-GCM + HMAC-SHA256
  - `verify_audit_log_integrity()` (line 414) - Tamper detection via HMAC
  - `decrypt_audit_log()` (line 470) - Decrypts audit events
  
**Tests confirm functionality**:
```bash
uv run pytest tests/test_audit_encryption.py -v
#  11/11 tests pass
```

### Issue
**Default audit logging appears to use PLAINTEXT**

The main `SecurityAuditLog` class (line 24) writes plaintext JSON:
```python
def _write_entry(self, event_type: str, details: dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event_type": event_type,
        **details,
    }
    with self.log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")  #  PLAINTEXT
```

### Required Fix

**Option 1**: Wire up encrypted audit logging as default
- Modify `SecurityAuditLog._write_entry()` to use `log_event_encrypted()`
- Requires passphrase management (where to store? how to access?)

**Option 2**: Document audit log security model
- If audit logs contain only hashes (no sensitive data), plaintext may be acceptable
- Review actual audit log content to confirm

**Action Required**: 
1. Audit what data goes into audit logs (model inference hashes? entry IDs?)
2. Determine if sensitive data is logged
3. If yes: implement Option 1
4. If no: document why plaintext is safe in Option 2

---

##  Config File Security

### Status
**Config file is SAFE as plaintext**

**Rationale**:
- Contains: model settings, paths, feature flags
- Does NOT contain: passphrases, API keys, secrets
- Passphrase is never stored (used transiently for encryption/decryption)

**Config structure** (`companion/models.py:112-137`):
```python
class Config(BaseModel):
    data_directory: Path
    model_name: str
    max_prompt_tokens: int
    max_summary_tokens: int
    first_run_complete: bool
    enable_encryption: bool       # Just a flag
    enable_pii_detection: bool
    enable_audit_logging: bool
    editor_idle_threshold: int
```

**No action required**.

---

## Security Checklist

### Data at Rest
- [x] Entry content encrypted (AES-256-GCM)
- [x] Entry metadata encrypted (timestamp, sentiment, themes, prompts, duration)
- [ ] Audit logs encrypted (functionality exists, not wired up as default)
- [x] Config file reviewed (safe as plaintext)
- [x] UUID-only filenames (no timestamp leaks)

### Encryption Implementation
- [x] PBKDF2 with 600,000 iterations (OWASP 2023 recommendation)
- [x] AES-256-GCM authenticated encryption
- [x] Random salt per entry
- [x] Random nonce per entry
- [x] Backward compatibility with legacy entries

### Testing
- [x] Full metadata encryption verified
- [x] No plaintext leaks confirmed
- [x] Legacy entry compatibility tested
- [x] Encrypted audit log functionality tested
- [x] Wrong passphrase rejection tested
- [x] Filename privacy verified

---

## Remaining Work

### High Priority
1. **Audit Log Security Decision** (see "Audit Log Encryption Status" above)
   - Review audit log contents
   - Determine if encryption is needed
   - Either wire up encrypted logging OR document why plaintext is safe

### Medium Priority
2. **Key Rotation Documentation**
   - Document key rotation process (code exists in `encryption.py:295`)
   - Create user guide for changing passphrases
   - Add tests for key rotation with full metadata encryption

3. **Security Best Practices Guide**
   - Document passphrase requirements
   - Explain backup procedures
   - Clarify what is/isn't encrypted and why

### Low Priority
4. **Performance Optimization**
   - Profile encryption overhead with full metadata vs content-only
   - Consider caching decrypted entries (with security review)

---

## Testing Commands

**Full encryption suite**:
```bash
uv run pytest tests/ -k "encryption" -v
# Expected: 55 passed
```

**Specific tests**:
```bash
# Full metadata encryption
uv run pytest tests/test_full_metadata_encryption.py -v

# Legacy compatibility
uv run pytest tests/test_journal_encryption.py -v

# Audit log encryption
uv run pytest tests/test_audit_encryption.py -v

# Core encryption primitives
uv run pytest tests/test_security_encryption.py -v
```

---

## Security Contact

For security concerns or to report vulnerabilities, please contact the project maintainer.

**Responsible Disclosure**: We request 90 days for fixes before public disclosure.

---

## Version History

**2025-11-08**: 
- Fixed critical entry metadata encryption vulnerability
- Added full metadata encryption with backward compatibility
- Documented audit log encryption status
- Confirmed config file security model
