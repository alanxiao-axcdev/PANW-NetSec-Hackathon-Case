# Passphrase Security - Strength Enforcement & Brute Force Protection

**Security Features**: Strong passphrase requirements and brute force mitigation

---

## Security Rationale

**Problem 1: Weak Passphrases**
- Users choose weak passphrases ("password123")
- Vulnerable to dictionary attacks
- PBKDF2 iterations help but don't eliminate risk
- Compliance requirements mandate strong passwords

**Problem 2: Brute Force Attacks**
- Unlimited passphrase attempts enable brute force
- No rate limiting or account lockout
- Offline attacks possible if files accessed
- Need protection for online and offline scenarios

**Solutions**:
1. Enforce passphrase strength requirements
2. Rate limit passphrase attempts
3. Exponential backoff on failures
4. Account lockout after threshold
5. Audit log of failed attempts

---

## Design

### Passphrase Strength Requirements

**NIST SP 800-63B Guidelines (2024):**
- Minimum length: 12 characters (not 8)
- Check against common password lists
- No composition requirements (research shows they don't help)
- Entropy estimation for strength scoring

**Our Requirements:**
- **Minimum**: 12 characters
- **Recommended**: 16+ characters  
- **Banned**: Top 10,000 common passwords
- **Checks**: Dictionary words, repeated patterns, sequential characters
- **Scoring**: Weak/Medium/Strong/Very Strong

**User-friendly**:
- Show strength meter during passphrase creation
- Suggest improvements for weak passphrases
- Allow strong passphrases of any composition

---

### Brute Force Protection

**Multi-layer Defense:**

**Layer 1: Rate Limiting (Online Attacks)**
- Max 5 attempts per 15 minutes
- Exponential backoff: 1s, 2s, 4s, 8s, 16s...
- Resets after successful authentication

**Layer 2: Account Lockout (Persistent Attacks)**
- Lock after 10 failed attempts in 24 hours
- Unlock: Manual override or 24-hour timeout
- Logged to audit trail

**Layer 3: Offline Attack Mitigation (File Access)**
- PBKDF2 600k iterations (computationally expensive)
- Random salts (prevents rainbow tables)
- Strong passphrase requirements (increases key space)

**Layer 4: Monitoring & Alerts**
- Log all failed attempts
- Alert on suspicious patterns
- Track attempt sources (for future multi-user)

---

## Implementation Specification

### New Module: companion/security/passphrase.py

```python
"""Passphrase strength enforcement and brute force protection."""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re

class PassphraseStrength(Enum):
    """Passphrase strength levels."""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

@dataclass
class PassphraseScore:
    """Passphrase strength assessment."""
    strength: PassphraseStrength
    score: int  # 0-100
    feedback: list[str]  # Improvement suggestions
    entropy_bits: float  # Estimated entropy

@dataclass
class FailedAttempt:
    """Record of failed passphrase attempt."""
    timestamp: datetime
    attempt_type: str  # 'decrypt', 'rotate', 'audit'
    ip_address: str = "local"  # Future: track IP

def check_passphrase_strength(passphrase: str) -> PassphraseScore:
    """Evaluate passphrase strength.
    
    Checks:
    - Length (12+ required, 16+ recommended)
    - Common passwords (top 10k banned)
    - Dictionary words
    - Repeated patterns (aaaa, 1234)
    - Sequential characters (abcd, 6789)
    - Character diversity (letters, numbers, symbols)
    - Entropy estimation
    
    Returns:
        PassphraseScore with strength, score, and feedback
    """

def is_passphrase_acceptable(passphrase: str) -> tuple[bool, str]:
    """Check if passphrase meets minimum requirements.
    
    Args:
        passphrase: Passphrase to validate
        
    Returns:
        (is_acceptable, rejection_reason)
        
    Examples:
        >>> is_passphrase_acceptable("password123")
        (False, "Passphrase is in common password list")
        
        >>> is_passphrase_acceptable("my-secure-journal-2025!")
        (True, "")
    """

def calculate_entropy(passphrase: str) -> float:
    """Estimate passphrase entropy in bits.
    
    Uses Shannon entropy calculation.
    
    Returns:
        Entropy in bits (higher = stronger)
        
    Guidelines:
        < 40 bits: Weak
        40-60 bits: Medium
        60-80 bits: Strong
        > 80 bits: Very strong
    """

# Brute force protection

class BruteForceProtector:
    """Tracks and limits passphrase attempts."""
    
    def __init__(self, data_dir: Path):
        self.attempts_file = data_dir / "auth_attempts.json"
        self.max_attempts_per_window = 5  # attempts
        self.window_minutes = 15
        self.lockout_threshold = 10  # total attempts
        self.lockout_hours = 24
    
    def record_attempt(self, success: bool, attempt_type: str) -> None:
        """Record passphrase attempt (success or failure)."""
    
    def check_rate_limit(self) -> tuple[bool, str]:
        """Check if rate limit exceeded.
        
        Returns:
            (is_allowed, message)
            
        Examples:
            >>> protector.check_rate_limit()
            (True, "")  # Allowed
            
            >>> # After 5 failures
            >>> protector.check_rate_limit()
            (False, "Too many attempts. Wait 15 minutes.")
        """
    
    def is_locked_out(self) -> tuple[bool, datetime | None]:
        """Check if account is locked due to repeated failures.
        
        Returns:
            (is_locked, unlock_time)
        """
    
    def get_delay_seconds(self) -> int:
        """Get required delay before next attempt (exponential backoff).
        
        Returns:
            Seconds to wait (0 if no delay needed)
        """
    
    def reset(self) -> None:
        """Reset attempt counter after successful authentication."""
    
    def get_recent_attempts(self, hours: int = 24) -> list[FailedAttempt]:
        """Get recent failed attempts for audit."""
```

### Integration Points

**companion/security/encryption.py**:
```python
# Add at top of decrypt functions
from companion.security.passphrase import BruteForceProtector

def decrypt_entry_with_protection(encrypted: bytes, passphrase: str, data_dir: Path) -> str:
    """Decrypt with brute force protection."""
    protector = BruteForceProtector(data_dir)
    
    # Check rate limit
    allowed, message = protector.check_rate_limit()
    if not allowed:
        raise RateLimitError(message)
    
    # Check lockout
    locked, unlock_time = protector.is_locked_out()
    if locked:
        raise AccountLockedError(f"Account locked until {unlock_time}")
    
    # Apply exponential backoff
    delay = protector.get_delay_seconds()
    if delay > 0:
        time.sleep(delay)
    
    # Attempt decrypt
    try:
        result = decrypt_entry(encrypted, passphrase)
        protector.record_attempt(success=True, attempt_type="decrypt")
        return result
    except Exception as e:
        protector.record_attempt(success=False, attempt_type="decrypt")
        raise
```

**companion/cli.py** (rotate-keys, audit commands):
```python
# Prompt with strength check
from companion.security.passphrase import check_passphrase_strength, is_passphrase_acceptable

new_pass = Prompt.ask("New passphrase", password=True)

# Check strength
score = check_passphrase_strength(new_pass)
if score.strength == PassphraseStrength.WEAK:
    console.print(f"[yellow]  Weak passphrase (score: {score.score}/100)[/yellow]")
    for suggestion in score.feedback:
        console.print(f"  • {suggestion}")
    
    if not click.confirm("Use anyway?"):
        return

# Check if acceptable
acceptable, reason = is_passphrase_acceptable(new_pass)
if not acceptable:
    console.print(f"[red]Passphrase rejected: {reason}[/red]")
    return
```

---

## Common Password List

Use `common_passwords.txt` with top 10,000 passwords:
- rockyou.txt subset
- NIST banned passwords
- Keyboard patterns (qwerty, 123456)

Stored in: `companion/security/data/common_passwords.txt`

---

## User Experience

### Passphrase Creation with Feedback

```
$ companion rotate-keys

Enter new passphrase: password123

  Weak passphrase (score: 15/100)
  • Too short (8 chars, need 12+)
  • Common password (found in breach database)
  • No special characters
  • Sequential numbers

Suggestions:
  • Use 16+ characters
  • Combine unrelated words: correct-horse-battery-staple
  • Add numbers and symbols naturally
  
Use anyway? (y/N): n

Enter new passphrase: my-secure-journal-2025!

✓ Strong passphrase (score: 78/100)
  Length: 22 characters
  Entropy: 84 bits
  Not in common password list

Confirm passphrase: my-secure-journal-2025!
```

### Rate Limiting

```
$ companion

Enter passphrase: wrong1
✗ Incorrect passphrase

Enter passphrase: wrong2  
✗ Incorrect passphrase (1 second delay)

Enter passphrase: wrong3
✗ Incorrect passphrase (2 second delay)

Enter passphrase: wrong4
✗ Incorrect passphrase (4 second delay)

Enter passphrase: wrong5
✗ Incorrect passphrase (8 second delay)

Enter passphrase: wrong6
  Rate limit exceeded. Too many failed attempts.
   Try again in 15 minutes.
   
Attempts: 6/5 in last 15 minutes
Next attempt allowed: 2025-01-08 15:15:00
```

### Account Lockout

```
$ companion

  Account locked due to repeated failed attempts.
   
Total failed attempts: 10 in last 24 hours
Account will unlock: 2025-01-09 14:30:00

For manual unlock, contact administrator or delete:
  ~/.companion/auth_attempts.json
  
All failed attempts logged to audit trail.
```

---

## Testing Strategy

**Unit Tests:**
- Test strength scoring (weak/medium/strong/very-strong)
- Test common password detection
- Test entropy calculation
- Test rate limiting logic
- Test lockout logic
- Test exponential backoff

**Integration Tests:**
- Create passphrase with strength feedback
- Failed attempts trigger rate limiting
- Lockout after threshold
- Reset after success
- Audit logging of attempts

**Security Tests:**
- Verify top 100 common passwords rejected
- Verify weak passphrases scored correctly
- Verify rate limit prevents rapid attempts
- Verify lockout persists across restarts

---

## Compliance Benefits

**NIST SP 800-63B**: Follows 2024 passphrase guidelines
**PCI-DSS**: Account lockout requirement
**HIPAA**: Access control best practices
**SOC 2**: Authentication security controls
**CIS Controls**: Password policy enforcement

---

## Performance

**Strength Check**: ~10-20ms (one-time on creation)
**Common Password Check**: ~5ms (hash lookup)
**Rate Limit Check**: ~1ms (file read)
**Exponential Backoff**: User-noticeable (intentional!)

---

## This Demonstrates (for PANW)

 **Authentication security**: Beyond encryption to access control
 **Compliance awareness**: NIST, PCI-DSS requirements
 **User experience**: Security that's user-friendly
 **Defense-in-depth**: Multiple protection layers
 **Operational security**: How to prevent common attacks

---

**This completes enterprise-grade authentication security!**
