# Encrypted Audit Logs - Design & Implementation

**Security Feature**: Encrypt audit logs to prevent attacker from hiding tracks

---

## Security Rationale

**Problem**: Unencrypted audit logs vulnerable to tampering
- Attacker with file access can delete/modify logs
- Covers their tracks after compromise
- Audit trail becomes unreliable for forensics

**Solution**: Encrypt audit logs with append-only protection

**Benefits**:
- Prevents log tampering without passphrase
- Maintains forensic evidence integrity
- Demonstrates defense-in-depth thinking
- Essential for compliance (SOC 2, PCI-DSS)

---

## Design

### Encrypted Audit Log Format

**Current (plaintext JSON)**:
```json
{
  "timestamp": "2025-01-08T14:30:00",
  "event_type": "MODEL_INFERENCE",
  "prompt_hash": "sha256:abc123...",
  "metadata": {...}
}
```

**New (encrypted with integrity)**:
```json
{
  "timestamp": "2025-01-08T14:30:00",
  "encrypted_event": "base64_ciphertext...",
  "integrity_hash": "hmac_sha256..."
}
```

**Integrity Protection**:
- HMAC-SHA256 of encrypted event
- Detects any tampering attempts
- Each log entry independently verified

---

## Implementation Specification

### Enhanced Functions

```python
# companion/security/audit.py

def log_event_encrypted(
    event_type: str,
    details: dict,
    passphrase: str,
    audit_file: Path
) -> None:
    """Log security event with encryption.
    
    Process:
    1. Create event JSON
    2. Encrypt with AES-256-GCM
    3. Generate HMAC for integrity
    4. Append to audit log
    5. File is append-only
    """

def verify_audit_log_integrity(
    audit_file: Path,
    passphrase: str
) -> tuple[bool, list[str]]:
    """Verify all audit log entries haven't been tampered with.
    
    Returns:
        (integrity_ok, list_of_tampered_entries)
    """

def decrypt_audit_log(
    audit_file: Path,
    passphrase: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[dict]:
    """Decrypt and return audit events.
    
    Args:
        audit_file: Path to encrypted audit log
        passphrase: Decryption passphrase
        start_date: Optional filter
        end_date: Optional filter
        
    Returns:
        List of decrypted audit events
    """
```

### CLI Commands

```bash
# View encrypted audit log (requires passphrase)
companion audit --decrypt

# Verify audit log integrity
companion audit --verify

# Export audit report (requires passphrase)
companion audit --report --start 2025-01-01
```

---

## Security Properties

**Confidentiality**:
- Audit events encrypted at rest
- Requires passphrase to read
- Protects sensitive metadata

**Integrity**:
- HMAC prevents tampering
- Detectable if entries modified
- Append-only file permissions

**Availability**:
- Graceful degradation if encryption fails
- Can still log plaintext as fallback
- Clear error messages

---

## Testing Strategy

**Unit Tests:**
- Test encrypted logging
- Test integrity verification
- Test decryption
- Test tampering detection

**Integration Tests:**
- Log events encrypted
- Verify integrity
- Decrypt and validate
- Simulate tampering (modify file, verify detects it)

---

## Compliance Benefits

**SOC 2**: Demonstrates log integrity controls
**PCI-DSS**: Audit log protection requirement
**HIPAA**: Access audit trail security
**GDPR**: Processing activity records protection

---

## User Experience

**Automatic encryption** (transparent):
```
# Normal usage - logs encrypted automatically
companion write
# Audit log updated (encrypted)
```

**Viewing encrypted logs**:
```
$ companion audit

Audit logs are encrypted. Enter passphrase to view:
Passphrase: ****

Verifying integrity... ✓ No tampering detected

Security Audit Log (Last 7 days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2025-01-08 14:30  MODEL_INFERENCE  Duration: 245ms
2025-01-08 14:28  DATA_ACCESS      Read entry: abc-123
2025-01-08 14:25  SECURITY_EVENT   PII detected: EMAIL
...
```

---

## Performance

**Overhead per log entry**:
- Encryption: ~2-3ms
- HMAC: ~1ms
- Total: ~4-5ms per event

**Impact**: Negligible for audit logging

---

## This Demonstrates (for PANW)

✅ **Defense-in-depth**: Protecting the protection mechanism
✅ **Forensics thinking**: Audit logs must be trustworthy
✅ **Tamper resistance**: Cryptographic integrity
✅ **Operational security**: How to maintain evidence in adversarial environments

---

**This shows you think about attacker perspective and counter-measures!**
