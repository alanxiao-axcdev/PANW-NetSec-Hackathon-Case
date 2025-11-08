# Key Rotation - Design & Implementation

**Security Feature**: Automatic encryption key rotation without data loss

---

## Security Rationale

**Problem**: Using same passphrase indefinitely increases risk
- If passphrase compromised, all historical data exposed
- Long-lived keys give attackers more time to crack
- Compliance requirements (PCI-DSS, HIPAA) mandate key rotation

**Solution**: Periodic key rotation with transparent re-encryption

**Benefits**:
- Limits exposure window
- Forces passphrase refresh
- Demonstrates security maturity
- Enables compliance with standards

---

## Design

### Key Rotation Strategy

**Envelope Encryption Approach:**
1. Master key (from passphrase) encrypts data encryption keys (DEKs)
2. Each entry encrypted with unique DEK
3. DEKs encrypted with master key
4. Rotation: Re-encrypt DEKs with new master key
5. Entry ciphertext unchanged (only DEK wrapper re-encrypted)

**Simpler Direct Approach (for MVP):**
1. Track passphrase generation/rotation timestamp
2. When rotation triggered (manual or time-based):
   - Prompt for new passphrase
   - Decrypt all entries with old key
   - Re-encrypt with new key
   - Update rotation timestamp
   - Log rotation event

---

## Implementation Specification

### New Functions

```python
# companion/security/encryption.py

def rotate_keys(
    old_passphrase: str,
    new_passphrase: str,
    entries_dir: Path,
    backup_dir: Path | None = None
) -> RotationResult:
    """Rotate encryption keys for all journal entries.
    
    Process:
    1. Verify old passphrase works (test decrypt one entry)
    2. Create backup of all encrypted files (optional)
    3. For each entry:
       a. Decrypt with old passphrase
       b. Re-encrypt with new passphrase
       c. Atomic replace (write temp, rename)
    4. Update rotation metadata
    5. Log rotation event
    
    Args:
        old_passphrase: Current passphrase
        new_passphrase: New passphrase
        entries_dir: Directory containing encrypted entries
        backup_dir: Optional backup location
        
    Returns:
        RotationResult with status, entries rotated, errors
        
    Raises:
        ValueError: If old passphrase incorrect
        RotationError: If rotation fails
    """

def verify_passphrase(passphrase: str, encrypted_file: Path) -> bool:
    """Verify passphrase can decrypt a file.
    
    Args:
        passphrase: Passphrase to verify
        encrypted_file: Sample encrypted file
        
    Returns:
        True if passphrase works, False otherwise
    """

def get_rotation_metadata() -> RotationMetadata:
    """Get last rotation timestamp and next due date.
    
    Returns:
        RotationMetadata with timestamps
    """

def should_rotate(rotation_interval_days: int = 90) -> bool:
    """Check if key rotation is due.
    
    Args:
        rotation_interval_days: Days between rotations (default: 90)
        
    Returns:
        True if rotation is due
    """
```

### New Data Model

```python
# companion/models.py

class RotationMetadata(BaseModel):
    """Key rotation metadata.
    
    Attributes:
        last_rotation: When keys were last rotated
        rotation_interval_days: Days between rotations
        next_rotation_due: When next rotation is due
        total_rotations: Count of rotations performed
    """
    last_rotation: datetime
    rotation_interval_days: int = 90
    next_rotation_due: datetime
    total_rotations: int = 0

class RotationResult(BaseModel):
    """Result of key rotation operation.
    
    Attributes:
        success: Whether rotation succeeded
        entries_rotated: Number of entries re-encrypted
        entries_failed: Number that failed
        errors: List of errors encountered
        duration_seconds: How long rotation took
    """
    success: bool
    entries_rotated: int
    entries_failed: int = 0
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
```

### CLI Command

```bash
# Trigger key rotation
companion rotate-keys

# Check rotation status
companion rotation-status

# Configure rotation interval
companion config set rotation_interval 60  # 60 days
```

---

## Security Considerations

**Atomic Operations:**
- Write to temporary file
- Only rename if encryption successful
- Prevents corruption if rotation interrupted

**Backup:**
- Optional backup before rotation
- Keep old encrypted files until rotation verified
- Rollback capability if issues detected

**Audit Trail:**
- Log rotation start/completion
- Record entries rotated
- Track any failures
- Timestamp for compliance

**Verification:**
- Test old passphrase before starting
- Verify new encryption after each entry
- Final verification pass on all entries

---

## Testing Strategy

**Unit Tests:**
- Test rotate_keys with mock entries
- Test passphrase verification
- Test should_rotate logic
- Test backup creation

**Integration Tests:**
- Create encrypted entries
- Rotate keys
- Verify all entries still readable with new key
- Verify old key no longer works

**Error Scenarios:**
- Wrong old passphrase
- Disk full during rotation
- Interrupted rotation (resume capability)

---

## Compliance Benefits

**PCI-DSS**: Requires key rotation
**HIPAA**: Best practice for PHI protection
**GDPR**: Demonstrates data protection by design
**SOC 2**: Shows operational security maturity

---

## User Experience

**Manual Rotation:**
```
$ companion rotate-keys

⚠️  Key Rotation will re-encrypt all journal entries.
   This limits exposure if your passphrase is compromised.

Current passphrase: ****
New passphrase: ****
Confirm new passphrase: ****

Creating backup to ~/.companion/backup_2025-01-08/...
✓ Backup created

Rotating keys for 47 entries...
[████████████████████] 47/47

✓ Rotation complete
  Entries rotated: 47
  Duration: 3.2 seconds
  Old passphrase no longer works

Next rotation due: 2025-04-08 (90 days)
```

**Automatic Reminder:**
```
$ companion

⚠️  Key rotation recommended (last rotated 95 days ago)
   Run: companion rotate-keys
   Or: companion config set rotation_reminder false

[Continue to journaling...]
```

---

## Performance Considerations

**Rotation Time:**
- ~60-80ms per entry (decrypt + encrypt)
- 100 entries = ~6-8 seconds
- 1000 entries = ~1 minute

**Recommendations:**
- Run during low-usage periods
- Show progress bar for >50 entries
- Option to rotate in background

---

## This Demonstrates (for PANW)

✅ **Security best practices**: Key rotation is standard practice
✅ **Operational thinking**: How do you maintain security over time?
✅ **Zero-downtime operations**: Rotate without data loss
✅ **Compliance awareness**: PCI-DSS, HIPAA requirements
✅ **User experience**: Make security transparent

---

**Implementing this shows you understand production security operations!**
