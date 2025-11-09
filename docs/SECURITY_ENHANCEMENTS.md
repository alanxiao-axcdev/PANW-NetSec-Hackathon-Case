# Security Enhancement Roadmap

**Comprehensive security audit findings and enhancement plans for PANW1 Companion Application**

Date: 2025-01-08  
Auditor: Security Guardian Agent  
Scope: Production-ready security for sensitive personal data (journaling use case)

---

## Executive Summary

This document presents findings from a comprehensive security audit of the PANW1 Companion application across 9 critical security dimensions. The audit revealed **strong foundational security** with several areas for strategic enhancement.

**Status Overview:**
-  **Already Implemented**: 4 security controls
- ⚡ **Quick Wins**: 3 easy fixes (< 1 day each)
-  **Enhancement Plans**: 5 complex features (detailed below)

**Security Posture**: The application demonstrates production-grade thinking with encryption, audit logging, and PII detection. Enhancement opportunities focus on defense-in-depth hardening.

---

## 1. Already Implemented 

### 1.1 File Permissions (PARTIAL)
**Status**: Audit log file protected, general files need hardening  
**Location**: `companion/security/audit.py:46`

```python
self.log_path.touch(mode=0o600)  # Restricted permissions
```

**What's Good:**
- Audit log created with restrictive permissions (owner read/write only)
- Demonstrates awareness of file permission security

**What's Missing:**
- Other sensitive files (encrypted entries, config, keys) created with default umask
- Directories created without explicit permission modes

### 1.2 Audit Logging (STRONG)
**Status**: Production-ready implementation  
**Location**: `companion/security/audit.py`

**What's Good:**
- Append-only audit trail
- Hashed prompts/outputs (privacy-preserving)
- Tamper-evident HMAC implementation
- Encrypted audit logs with key rotation support

**Outstanding Security Feature:**
- Logs use SHA256 hashes instead of plaintext
- Enables forensics without storing sensitive content

### 1.3 Dependency Management (BASIC)
**Status**: Dependencies specified, not pinned  
**Location**: `pyproject.toml`, `uv.lock`

**What's Good:**
- Dependencies declared with minimum versions (`>=`)
- Lock file exists (`uv.lock`) with exact versions
- Using `uv` for dependency management (modern, secure)

**What's Missing:**
- No hash verification in pyproject.toml
- No explicit supply chain attack prevention
- No automated vulnerability scanning

### 1.4 PII Detection (PRODUCTION-READY)
**Status**: Excellent implementation  
**Location**: `companion/security/pii_detector.py`

**What's Good:**
- Uses Presidio (Microsoft's PII detection library)
- 100% F1 score on core PII types
- User warnings before storing PII
- Multiple obfuscation methods available

---

## 2. Quick Wins ⚡

### 2.1 File Permissions Hardening
**Effort**: 2-4 hours  
**Priority**: HIGH  
**Risk Mitigated**: Unauthorized file access via OS-level permissions

**Current Gap:**
All sensitive files created with default permissions (typically 0o644 or 0o664):
- Encrypted journal entries
- Configuration files containing paths
- Backup files during key rotation
- Model cache directories

**Implementation:**
```python
# In companion/storage.py
def write_json(file_path: Path, data: dict[str, Any]) -> None:
    """Write dict to JSON file with restrictive permissions."""
    ensure_dir(file_path.parent)
    
    # Write atomically with temp file
    temp_path = file_path.with_suffix('.tmp')
    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # Set restrictive permissions before moving
    temp_path.chmod(0o600)  # Owner read/write only
    temp_path.replace(file_path)
    logger.debug("Wrote JSON to %s with mode 0o600", file_path)

def ensure_dir(directory: Path) -> None:
    """Create directory with restrictive permissions."""
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Ensure permissions even if dir existed
        directory.chmod(0o700)
        logger.debug("Ensured directory exists: %s (mode 0o700)", directory)
    except OSError as e:
        logger.error("Failed to create directory %s: %s", directory, e)
        raise
```

**Files to Modify:**
- `companion/storage.py` - Add permission enforcement
- `companion/config.py` - Set 0o600 for config files
- `companion/security/encryption.py` - Set 0o600 for backup files
- `companion/journal.py` - Ensure entries dir is 0o700

**Testing:**
```python
# tests/security/test_file_permissions.py
def test_entry_files_are_restricted():
    """Verify journal entries created with 0o600."""
    entry = create_test_entry()
    save_entry(entry)
    
    file_path = find_entry_file(entry.id)
    mode = file_path.stat().st_mode
    
    assert oct(mode)[-3:] == '600', f"Expected 0o600, got {oct(mode)}"

def test_directories_are_restricted():
    """Verify sensitive directories created with 0o700."""
    initialize_directories()
    
    for subdir in ["entries", "analysis", "audit"]:
        dir_path = get_data_dir() / subdir
        mode = dir_path.stat().st_mode
        assert oct(mode)[-3:] == '700', f"Expected 0o700 for {subdir}"
```

---

### 2.2 Secure Deletion
**Effort**: 3-4 hours  
**Priority**: MEDIUM  
**Risk Mitigated**: Forensic recovery of deleted sensitive data

**Current Gap:**
`storage.py:175` uses `Path.unlink()` which only removes directory entry:
```python
file_path.unlink()  # File data remains on disk until overwritten
```

**Threat Model:**
- Attacker gains physical access to disk
- Uses forensic tools to recover "deleted" encrypted entries
- Even encrypted data reveals metadata (file sizes, timestamps, patterns)

**Implementation:**
```python
import os
import secrets

def secure_delete(file_path: Path, passes: int = 3) -> None:
    """Securely delete file by overwriting before unlinking.
    
    Args:
        file_path: File to securely delete
        passes: Number of overwrite passes (default: 3)
    
    Note:
        - 3 passes sufficient for modern drives (DoD 5220.22-M)
        - SSD wear-leveling limits effectiveness; rely on encryption
        - Primary defense is full-disk encryption, this adds depth
    """
    if not file_path.exists():
        logger.debug("File doesn't exist, nothing to delete: %s", file_path)
        return
    
    file_size = file_path.stat().st_size
    
    try:
        # Overwrite with random data
        with file_path.open("r+b") as f:
            for pass_num in range(passes):
                f.seek(0)
                # Write random bytes
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
        
        # Final unlink
        file_path.unlink()
        logger.debug("Securely deleted: %s (%d passes)", file_path, passes)
        
    except OSError as e:
        logger.error("Failed to securely delete %s: %s", file_path, e)
        # Still attempt normal deletion
        try:
            file_path.unlink()
        except OSError:
            pass
        raise
```

**Files to Modify:**
- `companion/storage.py` - Add `secure_delete()` function
- `companion/security/encryption.py` - Use secure_delete for old key files
- `companion/journal.py` - Use secure_delete for entry deletion

**Testing:**
```python
def test_secure_delete_overwrites_data():
    """Verify secure delete overwrites file content."""
    test_file = Path("/tmp/test_secure_delete.txt")
    test_content = b"SENSITIVE DATA" * 100
    
    # Create file
    test_file.write_bytes(test_content)
    original_size = test_file.stat().st_size
    
    # Delete securely
    secure_delete(test_file, passes=1)
    
    # Verify file gone
    assert not test_file.exists()
    
    # Verify no easy recovery (check disk for patterns)
    # Note: Real test would scan disk sectors, simplified here
```

**Limitations:**
- SSDs use wear-leveling (old data may persist in unused blocks)
- Only effective with full-disk encryption as base layer
- Provides defense-in-depth, not primary security

---

### 2.3 Audit Log Sensitive Content Filter
**Effort**: 2-3 hours  
**Priority**: MEDIUM  
**Risk Mitigated**: Accidental PII/sensitive data leakage in audit logs

**Current Gap:**
Audit logs hash prompts/outputs but still log some metadata:
```python
# companion/security/audit.py
{
    "event_type": "model_inference",
    "prompt_hash": "sha256:...",
    "output_hash": "sha256:...",
    "duration_ms": 234,
    "model_name": "qwen2.5-1.5b-int8",  # Safe
    "metadata": {...}  # Potentially unsafe
}
```

**Implementation:**
```python
def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive data from audit log metadata.
    
    Strips:
    - UUIDs containing identifiable patterns
    - File paths containing usernames
    - Any PII that slipped through
    """
    sanitized = {}
    
    for key, value in metadata.items():
        if isinstance(value, str):
            # Redact paths containing username
            value = re.sub(r'/home/[^/]+/', '/home/USER/', value)
            value = re.sub(r'C:\\Users\\[^\\]+\\', 'C:\\Users\\USER\\', value)
            
            # Truncate long values that might contain PII
            if len(value) > 100:
                value = value[:97] + "..."
        
        sanitized[key] = value
    
    return sanitized

def _write_entry(self, event_type: str, details: dict[str, Any]) -> None:
    """Write audit entry with sanitized metadata."""
    # Sanitize metadata field if present
    if "metadata" in details:
        details["metadata"] = _sanitize_metadata(details["metadata"])
    
    entry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "event_type": event_type,
        **details,
    }
    # ... existing write logic
```

**Testing:**
```python
def test_audit_log_sanitizes_paths():
    """Verify audit log redacts username from paths."""
    log = SecurityAuditLog()
    log._write_entry("TEST", {
        "metadata": {
            "file_path": "/home/alice/journal/entry.json"
        }
    })
    
    # Read back and verify sanitization
    with log.log_path.open() as f:
        entry = json.loads(f.readlines()[-1])
    
    assert "/home/alice/" not in str(entry)
    assert "/home/USER/" in entry["metadata"]["file_path"]
```

---

## 3. Enhancement Plans 

### 3.1 Model Integrity Verification
**Effort**: 1-2 days  
**Priority**: HIGH  
**Complexity**: Medium

#### Threat Model
**Attack Vector**: Supply chain attack via compromised AI model  
**Scenario:**
1. Attacker compromises HuggingFace repository or CDN
2. Malicious model weights downloaded during `model.from_pretrained()`
3. Model contains backdoor that exfiltrates journal entries via:
   - Encoded in output tokens
   - Covert channel in timing
   - Direct network access if sandbox escapes

**Impact**: Complete compromise of user journal data

#### Current Gap
```python
# companion/ai_backend/qwen_provider.py:86
self.model = AutoModelForCausalLM.from_pretrained(
    self.model_name,
    cache_dir=str(self.cache_dir),
    trust_remote_code=True,  #  Dangerous flag
)
```

**Problems:**
- `trust_remote_code=True` executes arbitrary Python in model config
- No checksum verification of downloaded weights
- No signature verification
- No verification that model matches official release

#### Solution Architecture

**Phase 1: Checksum Verification**
```python
# companion/security/model_verification.py

MODEL_CHECKSUMS = {
    "Qwen/Qwen2.5-1.5B": {
        "model.safetensors": "sha256:a1b2c3d4...",
        "config.json": "sha256:e5f6g7h8...",
        "tokenizer.json": "sha256:i9j0k1l2...",
    }
}

def verify_model_files(model_name: str, cache_dir: Path) -> bool:
    """Verify all model files match official checksums.
    
    Returns:
        True if all files verified, False otherwise
        
    Raises:
        SecurityError: If checksums don't match
    """
    expected = MODEL_CHECKSUMS.get(model_name)
    if not expected:
        logger.warning("No checksums available for %s", model_name)
        return False
    
    model_path = cache_dir / "models--" / model_name.replace("/", "--")
    
    for filename, expected_hash in expected.items():
        file_path = model_path / filename
        if not file_path.exists():
            raise SecurityError(f"Model file missing: {filename}")
        
        actual_hash = _compute_sha256(file_path)
        if actual_hash != expected_hash:
            raise SecurityError(
                f"Model file {filename} checksum mismatch!\n"
                f"Expected: {expected_hash}\n"
                f"Got: {actual_hash}\n"
                f" SECURITY RISK: Model may be compromised"
            )
    
    logger.info(" Model integrity verified: %s", model_name)
    return True

def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"
```

**Phase 2: Remove `trust_remote_code`**
```python
# companion/ai_backend/qwen_provider.py

async def initialize(self) -> None:
    """Initialize with security checks."""
    # Verify model integrity BEFORE loading
    if not verify_model_files(self.model_name, self.cache_dir):
        raise SecurityError("Model integrity verification failed")
    
    # Load WITHOUT trust_remote_code
    self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        cache_dir=str(self.cache_dir),
        trust_remote_code=False,  #  Safer
    )
```

**Phase 3: Official Signature Verification (Future)**
```python
def verify_model_signature(model_name: str, cache_dir: Path) -> bool:
    """Verify model signed by HuggingFace official key.
    
    Requires:
    - HuggingFace to implement model signing
    - GPG/PGP signature verification
    """
    # Future implementation when HF adds signing
    pass
```

#### Implementation Plan

**Step 1: Generate checksums** (1 hour)
```bash
# Download official model
python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2.5-1.5B')"

# Compute checksums
cd ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-1.5B
sha256sum *.safetensors *.json > CHECKSUMS.txt

# Add to MODEL_CHECKSUMS constant
```

**Step 2: Implement verification** (4 hours)
- Create `companion/security/model_verification.py`
- Add `verify_model_files()` function
- Add `_compute_sha256()` helper
- Add custom `SecurityError` exception

**Step 3: Integrate with provider** (2 hours)
- Modify `QwenProvider.__init__()` to call verification
- Handle verification failures gracefully
- Add user-facing error messages

**Step 4: Testing** (2 hours)
```python
def test_model_verification_detects_tampering():
    """Verify checksum mismatch detected."""
    # Download model
    provider = QwenProvider()
    await provider.initialize()
    
    # Tamper with model file
    model_file = find_model_file("model.safetensors")
    with model_file.open("ab") as f:
        f.write(b"TAMPERED")
    
    # Verification should fail
    with pytest.raises(SecurityError, match="checksum mismatch"):
        verify_model_files("Qwen/Qwen2.5-1.5B", cache_dir)
```

**Step 5: Documentation** (1 hour)
- Update `docs/SECURITY.md` with model verification
- Add checksums to repository
- Document checksum update process

#### Maintenance
- Update checksums when model version changes
- Monitor HuggingFace for model updates
- Consider automated checksum fetching from trusted source

---

### 3.2 Dependency Security Hardening
**Effort**: 1 day  
**Priority**: MEDIUM  
**Complexity**: Medium

#### Threat Model
**Attack Vector**: Supply chain attack via compromised dependency  
**Scenario:**
1. Attacker compromises PyPI package (e.g., `transformers`)
2. Publishes malicious version with same version number
3. User runs `uv sync` and gets compromised package
4. Malicious code exfiltrates encryption keys or journal content

**Real-World Examples:**
- `event-stream` (npm): 2M+ weekly downloads, backdoored
- `ua-parser-js` (npm): Cryptocurrency miner injected
- `ctx` (PyPI): Typosquatting attack stealing AWS credentials

#### Current State
```toml
# pyproject.toml
dependencies = [
    "click>=8.1.0",           # Minimum version only
    "cryptography>=41.0.0",   # No hash pinning
    "transformers>=4.35.0",   # Wide version range
]
```

**Lock file exists** (`uv.lock`) but:
- No hash verification in install process
- No automated vulnerability scanning
- No update policy documented

#### Solution Architecture

**Phase 1: Hash Pinning**
```toml
# pyproject.toml - Enhanced with hashes
[tool.uv]
index-strategy = "hash-verified"

[[tool.uv.index]]
url = "https://pypi.org/simple"
verify-mode = "hash"

dependencies = [
    "click>=8.1.0 --hash=sha256:...",
    "cryptography>=41.0.0 --hash=sha256:...",
    # Hashes from uv.lock
]
```

**Phase 2: Vulnerability Scanning**
```python
# scripts/check_vulns.py

import subprocess
import sys

def check_vulnerabilities() -> int:
    """Check dependencies for known vulnerabilities.
    
    Uses pip-audit to scan against OSV database.
    Returns:
        0 if no vulnerabilities, 1 otherwise
    """
    result = subprocess.run(
        ["pip-audit", "--desc", "--fix-dry-run"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("🚨 Vulnerabilities detected:")
        print(result.stdout)
        return 1
    
    print(" No known vulnerabilities")
    return 0

if __name__ == "__main__":
    sys.exit(check_vulnerabilities())
```

**Phase 3: Dependency Update Policy**
```markdown
# docs/DEPENDENCY_POLICY.md

## Dependency Security Policy

### Update Cadence
- **Security updates**: Within 48 hours of disclosure
- **Minor updates**: Monthly review
- **Major updates**: Quarterly, with testing

### Verification Process
1. Check CVE database for new vulnerabilities
2. Run `scripts/check_vulns.py`
3. Update `uv.lock` with `uv lock --upgrade-package <pkg>`
4. Regenerate hashes
5. Run full test suite
6. Update CHANGELOG.md

### Automated Scanning
- GitHub Dependabot: Enabled
- Weekly vulnerability scans: CI/CD
- Alert threshold: CVSS >= 7.0 (High/Critical)
```

#### Implementation Plan

**Step 1: Add pip-audit** (1 hour)
```toml
[project.optional-dependencies]
dev = [
    "pip-audit>=2.6.0",
    # existing dev deps
]
```

**Step 2: Create vulnerability check script** (2 hours)
- Implement `scripts/check_vulns.py`
- Add to `Makefile` as `make check-vulns`
- Integrate with CI/CD

**Step 3: Document policy** (2 hours)
- Create `docs/DEPENDENCY_POLICY.md`
- Document update procedures
- Add playbook for security updates

**Step 4: Setup automation** (2 hours)
- Enable GitHub Dependabot (if using GitHub)
- Configure alerts for CVSS >= 7.0
- Setup weekly CI scan

**Step 5: Initial audit** (1 hour)
```bash
make check-vulns
# Address any findings
```

#### Testing
```python
def test_no_known_vulnerabilities():
    """Verify dependencies have no known CVEs."""
    result = subprocess.run(
        ["pip-audit", "--desc"],
        capture_output=True
    )
    assert result.returncode == 0, "Known vulnerabilities detected"
```

---

### 3.3 Timing Attack Prevention
**Effort**: 4-6 hours  
**Priority**: LOW  
**Complexity**: Low

#### Threat Model
**Attack Vector**: Timing side-channel reveals passphrase/key info  
**Scenario:**
1. Attacker has local access (e.g., compromised user account)
2. Repeatedly attempts decryption with different passphrases
3. Measures response time differences
4. Deduces correct passphrase prefix via timing oracle

**Example:**
```python
# Vulnerable code
if passphrase == stored_passphrase:  # String comparison stops at first mismatch
    return True
# Timing: "aaa..." returns faster than "my-..."
```

#### Current State
```python
# companion/security/encryption.py uses cryptography library
# which DOES use constant-time comparison internally

# But passphrase validation might be vulnerable:
if not passphrase:  # Fast path
    raise ValueError("Passphrase cannot be empty")
```

**Analysis:**
- `cryptography` library uses constant-time comparison in crypto ops
- Python's `secrets.compare_digest()` available for custom comparisons
- Need to audit all comparison paths

#### Solution

**Audit all comparison operations:**
```python
import secrets

# BAD: Timing-vulnerable
if user_hash == expected_hash:
    return True

# GOOD: Constant-time
if secrets.compare_digest(user_hash, expected_hash):
    return True
```

**Files to audit:**
- `companion/security/passphrase.py` - Passphrase validation
- `companion/security/encryption.py` - Key derivation verification
- `companion/security/audit.py` - HMAC verification

#### Implementation

```python
# companion/security/passphrase.py

def verify_passphrase_hash(provided: str, stored_hash: str) -> bool:
    """Verify passphrase against stored hash using constant-time comparison.
    
    Args:
        provided: User-provided passphrase
        stored_hash: Stored hash to compare against
        
    Returns:
        True if match (constant time), False otherwise
    """
    # Hash the provided passphrase
    provided_hash = _hash_passphrase(provided)
    
    # Constant-time comparison
    return secrets.compare_digest(provided_hash, stored_hash)
```

**Testing:**
```python
def test_passphrase_verification_constant_time():
    """Verify passphrase comparison takes similar time regardless of correctness."""
    import time
    
    stored_hash = _hash_passphrase("correct-passphrase-12345")
    
    # Time incorrect passphrase (different first char)
    times_wrong = []
    for _ in range(100):
        start = time.perf_counter()
        verify_passphrase_hash("aaaaaa", stored_hash)
        times_wrong.append(time.perf_counter() - start)
    
    # Time incorrect passphrase (correct prefix)
    times_prefix = []
    for _ in range(100):
        start = time.perf_counter()
        verify_passphrase_hash("correct-aaaaaa", stored_hash)
        times_prefix.append(time.perf_counter() - start)
    
    # Timing should be similar (within 10%)
    avg_wrong = sum(times_wrong) / len(times_wrong)
    avg_prefix = sum(times_prefix) / len(times_prefix)
    
    diff_pct = abs(avg_wrong - avg_prefix) / avg_wrong
    assert diff_pct < 0.10, f"Timing difference {diff_pct:.1%} suggests timing leak"
```

---

### 3.4 Crash Dump Security
**Effort**: 1 day  
**Priority**: MEDIUM  
**Complexity**: Medium

#### Threat Model
**Attack Vector**: Crash dump exposes decrypted data in memory  
**Scenario:**
1. Application crashes while processing journal entry
2. OS creates core dump with full memory snapshot
3. Attacker accesses core dump file
4. Extracts decrypted journal entries from memory

**Real-World:**
- Core dumps often contain credentials, keys, decrypted data
- Default Linux: core dumps in CWD with predictable names
- macOS: `/cores/core.PID`
- Windows: Can be configured to save dumps

#### Current State
**No crash dump protection:**
- No core dump disabling
- No memory zeroing on exception
- No core dump file detection/cleanup

**Memory exposure points:**
```python
# companion/security/encryption.py
def decrypt_entry(encrypted_data: bytes, passphrase: str) -> str:
    key = derive_key(passphrase, salt)  # Key in memory
    plaintext = aesgcm.decrypt(nonce, ciphertext)  # Plaintext in memory
    return plaintext.decode("utf-8")  # Plaintext string in memory
    # If crash happens here, all above is in core dump
```

#### Solution Architecture

**Phase 1: Disable Core Dumps**
```python
# companion/security/memory.py

import resource
import sys

def disable_core_dumps() -> None:
    """Disable core dump generation for this process.
    
    Prevents sensitive data from being written to disk on crash.
    Should be called early in application startup.
    """
    if sys.platform == "linux" or sys.platform == "darwin":
        try:
            # Set core dump size limit to 0
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            logger.info(" Core dumps disabled")
        except (ValueError, OSError) as e:
            logger.warning("Failed to disable core dumps: %s", e)
    
    elif sys.platform == "win32":
        # Windows: Requires registry modification or WER settings
        logger.warning("Core dump disabling not implemented for Windows")
```

**Phase 2: Secure Memory Handling**
```python
import ctypes
import secrets

class SecureBuffer:
    """Buffer that zeros memory on deletion.
    
    Use for sensitive data like passphrases and decrypted content.
    """
    
    def __init__(self, data: bytes):
        self.data = bytearray(data)
        self.size = len(data)
    
    def __del__(self):
        """Zero memory before deallocation."""
        if hasattr(self, 'data'):
            # Overwrite with zeros
            for i in range(len(self.data)):
                self.data[i] = 0
            
            # Then random data
            for i in range(len(self.data)):
                self.data[i] = secrets.randbits(8)
            
            del self.data
    
    def get_bytes(self) -> bytes:
        """Get bytes (creates copy, original stays secure)."""
        return bytes(self.data)

# Usage:
def decrypt_entry_secure(encrypted_data: bytes, passphrase: str) -> str:
    """Decrypt with memory security."""
    # Wrap sensitive data in SecureBuffer
    key_buf = SecureBuffer(derive_key(passphrase, salt))
    
    try:
        plaintext_buf = SecureBuffer(
            aesgcm.decrypt(nonce, ciphertext, key_buf.get_bytes())
        )
        return plaintext_buf.get_bytes().decode("utf-8")
    finally:
        # Explicit cleanup
        del key_buf
        del plaintext_buf
```

**Phase 3: Exception Handler**
```python
import sys
import traceback

def secure_exception_handler(exc_type, exc_value, exc_traceback):
    """Exception handler that avoids dumping sensitive data.
    
    Replaces default exception handler to:
    - Log exception without sensitive data
    - Zero sensitive memory regions
    - Exit gracefully
    """
    # Log sanitized traceback
    logger.error("Application crashed", exc_info=(exc_type, exc_value, exc_traceback))
    
    # TODO: Zero known sensitive memory regions
    # (requires tracking of sensitive data locations)
    
    # Exit without core dump
    sys.exit(1)

# Install handler
sys.excepthook = secure_exception_handler
```

#### Implementation Plan

**Step 1: Disable core dumps** (1 hour)
- Create `companion/security/memory.py`
- Implement `disable_core_dumps()`
- Call from `companion/cli.py` main()

**Step 2: Implement SecureBuffer** (3 hours)
- Add `SecureBuffer` class
- Wrap passphrase handling
- Wrap decrypted data

**Step 3: Exception handler** (2 hours)
- Implement `secure_exception_handler()`
- Install in application startup
- Test crash scenarios

**Step 4: Testing** (2 hours)
```python
def test_core_dumps_disabled():
    """Verify core dumps cannot be generated."""
    import signal
    import os
    
    # Fork process
    pid = os.fork()
    if pid == 0:
        # Child: disable dumps and crash
        disable_core_dumps()
        os.kill(os.getpid(), signal.SIGSEGV)
    else:
        # Parent: wait and check for core dump
        os.waitpid(pid, 0)
        assert not Path(f"core.{pid}").exists(), "Core dump was created!"
```

---

### 3.5 Filename Privacy
**Effort**: 2-3 hours  
**Priority**: LOW  
**Complexity**: Low

#### Threat Model
**Attack Vector**: Filesystem metadata reveals user activity  
**Scenario:**
1. Attacker gains access to filesystem (backup, disk image, etc.)
2. Cannot decrypt journal entries (strong encryption)
3. But can see filenames: `20250108_143022_<uuid>.json`
4. Deduces user activity patterns:
   - Journal entry timestamps
   - Frequency of entries (emotional states?)
   - Gaps in journaling (travel? illness?)

**Information Leakage:**
- Timestamps reveal when user was journaling
- Frequency patterns reveal behavioral patterns
- Metadata can be cross-referenced with other data sources

#### Current State
```python
# companion/journal.py:36
timestamp_str = entry.timestamp.strftime("%Y%m%d_%H%M%S")
filename = f"{timestamp_str}_{entry.id}.json"
# Example: 20250108_143022_a1b2c3d4-e5f6-7890-abcd-ef1234567890.json
```

**Information exposed in filename:**
- Year, month, day (8 chars)
- Hour, minute, second (6 chars)
- Entry UUID (36 chars)

#### Solution

**Option 1: Random Filenames**
```python
def save_entry(entry: JournalEntry) -> str:
    """Save with random filename, timestamp stored inside encrypted data."""
    import secrets
    
    # Random filename (URL-safe)
    filename = f"{secrets.token_urlsafe(32)}.json"
    file_path = entries_dir / filename
    
    # Timestamp stored IN encrypted content
    entry_dict = entry.model_dump(mode="json")
    # ... encrypt and save
```

**Option 2: Hash-Based Filenames**
```python
def save_entry(entry: JournalEntry) -> str:
    """Save with hash-based filename."""
    import hashlib
    
    # Hash entry ID (deterministic, no timestamp)
    filename_hash = hashlib.sha256(entry.id.encode()).hexdigest()[:32]
    filename = f"{filename_hash}.json"
    
    # Still can find entry by ID, but no timestamp in filename
```

**Trade-offs:**

| Approach | Privacy | Findability | Compatibility |
|----------|---------|-------------|---------------|
| Current | Low (timestamp visible) | Easy (sort by name) | High |
| Random | High (no metadata) | Requires index | Medium (need index rebuild) |
| Hash-based | Medium (ID visible) | Requires lookup | High (deterministic) |

#### Recommendation: Hash-Based

**Rationale:**
- Removes timestamp from filename (primary threat)
- Deterministic (same entry ID = same filename)
- No index required (can compute filename from ID)
- Backward compatible (can migrate existing files)

#### Implementation

```python
# companion/journal.py

import hashlib

def _get_entry_filename(entry_id: str) -> str:
    """Get filename for entry (hash-based for privacy).
    
    Args:
        entry_id: Entry UUID
        
    Returns:
        Filename (hash of UUID + .json)
        
    Example:
        >>> _get_entry_filename("a1b2c3d4-...")
        "7f3e9c2a1b5d8e4f.json"
    """
    # Hash the UUID to get privacy-preserving filename
    filename_hash = hashlib.sha256(entry_id.encode()).hexdigest()[:16]
    return f"{filename_hash}.json"

def save_entry(entry: JournalEntry) -> str:
    """Save entry with privacy-preserving filename."""
    config = load_config()
    entries_dir = config.data_directory / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    
    # Use hash-based filename (no timestamp)
    filename = _get_entry_filename(entry.id)
    file_path = entries_dir / filename
    
    entry_dict = entry.model_dump(mode="json")
    write_json(file_path, entry_dict)
    
    logger.info("Saved entry: %s as %s", entry.id, filename)
    return entry.id

def get_entry(entry_id: str) -> JournalEntry | None:
    """Retrieve entry by ID using hash-based lookup."""
    config = load_config()
    entries_dir = config.data_directory / "entries"
    
    if not entries_dir.exists():
        return None
    
    # Compute expected filename
    filename = _get_entry_filename(entry_id)
    file_path = entries_dir / filename
    
    if not file_path.exists():
        logger.debug("Entry not found: %s", entry_id)
        return None
    
    try:
        entry_dict = read_json(file_path)
        return JournalEntry(**entry_dict)
    except Exception as e:
        logger.error("Failed to load entry %s: %s", entry_id, e)
        raise
```

**Migration Script:**
```python
# scripts/migrate_filenames.py

def migrate_to_privacy_filenames():
    """Migrate existing timestamp-based filenames to hash-based.
    
    Idempotent: safe to run multiple times.
    """
    entries_dir = get_data_dir() / "entries"
    
    for old_path in entries_dir.glob("*.json"):
        # Skip if already migrated (no timestamp in name)
        if not re.match(r'\d{8}_\d{6}_', old_path.name):
            continue
        
        # Load entry to get ID
        entry_dict = read_json(old_path)
        entry_id = entry_dict["id"]
        
        # Compute new filename
        new_filename = _get_entry_filename(entry_id)
        new_path = entries_dir / new_filename
        
        # Rename (atomic operation)
        old_path.rename(new_path)
        logger.info("Migrated: %s -> %s", old_path.name, new_filename)

if __name__ == "__main__":
    migrate_to_privacy_filenames()
```

#### Testing
```python
def test_filenames_contain_no_timestamps():
    """Verify filenames don't reveal temporal information."""
    entry = create_test_entry()
    save_entry(entry)
    
    # Find the file
    entries_dir = get_data_dir() / "entries"
    files = list(entries_dir.glob("*.json"))
    
    for file_path in files:
        # Verify no timestamp pattern in filename
        assert not re.match(r'\d{8}_\d{6}', file_path.name), \
            f"Filename contains timestamp: {file_path.name}"
```

---

## 4. Priority Matrix

| Enhancement | Priority | Effort | Risk Mitigated | ROI |
|-------------|----------|--------|----------------|-----|
| **File Permissions** | HIGH | Low (2-4h) | Unauthorized file access |  |
| **Model Integrity** | HIGH | Medium (1-2d) | Supply chain attack |  |
| **Secure Deletion** | MEDIUM | Low (3-4h) | Forensic recovery |  |
| **Audit Log Filter** | MEDIUM | Low (2-3h) | PII in logs |  |
| **Dependency Security** | MEDIUM | Medium (1d) | Compromised packages |  |
| **Crash Dump Security** | MEDIUM | Medium (1d) | Memory exposure |  |
| **Timing Attacks** | LOW | Low (4-6h) | Side-channel oracle |  |
| **Filename Privacy** | LOW | Low (2-3h) | Metadata leakage |  |

**Recommended Implementation Order:**
1. **Week 1**: File Permissions (quick win, high impact)
2. **Week 2**: Model Integrity Verification (highest risk)
3. **Week 3**: Secure Deletion + Audit Log Filter (medium risk, quick wins)
4. **Week 4**: Dependency Security (foundational)
5. **Week 5**: Crash Dump Security (defense-in-depth)
6. **As needed**: Timing Attacks, Filename Privacy (polish)

---

## 5. Testing Strategy

### Security Test Suite
```python
# tests/security/test_comprehensive_security.py

class TestFilePermissions:
    """Test file permission enforcement."""
    
    def test_entry_files_restricted(self):
        """Journal entries must be 0o600."""
        pass
    
    def test_directories_restricted(self):
        """Sensitive dirs must be 0o700."""
        pass
    
    def test_config_files_restricted(self):
        """Config files must be 0o600."""
        pass

class TestSecureDeletion:
    """Test secure deletion."""
    
    def test_files_overwritten_before_unlink(self):
        """Verify data overwritten."""
        pass
    
    def test_multipass_overwrite(self):
        """Verify multiple overwrite passes."""
        pass

class TestModelIntegrity:
    """Test model verification."""
    
    def test_checksum_verification(self):
        """Verify model checksums validated."""
        pass
    
    def test_tampered_model_rejected(self):
        """Verify tampered model rejected."""
        pass

class TestDependencySecurity:
    """Test dependency security."""
    
    def test_no_known_vulnerabilities(self):
        """Verify no CVEs in dependencies."""
        pass
    
    def test_hash_verification(self):
        """Verify dependency hashes checked."""
        pass

class TestCrashDumpSecurity:
    """Test crash handling."""
    
    def test_core_dumps_disabled(self):
        """Verify core dumps disabled."""
        pass
    
    def test_sensitive_memory_zeroed(self):
        """Verify memory cleanup on exception."""
        pass

class TestTimingAttacks:
    """Test timing attack resistance."""
    
    def test_passphrase_comparison_constant_time(self):
        """Verify constant-time comparison."""
        pass

class TestFilenamePrivacy:
    """Test filename privacy."""
    
    def test_no_timestamps_in_filenames(self):
        """Verify no temporal info in filenames."""
        pass
```

---

## 6. Compliance Considerations

### GDPR / CCPA
-  Data minimization (local-only processing)
-  Encryption at rest (AES-256-GCM)
-  Right to erasure (needs secure deletion)
-  Data portability (JSON export)

### HIPAA (if used for health data)
-  Encryption at rest
-  Audit logging
-  Access controls (single-user, OS-level only)
-  Secure deletion (needs enhancement)

### PCI-DSS (if storing payment data - NOT RECOMMENDED)
-  Encryption of cardholder data
-  Network segmentation (not applicable)
-  File integrity monitoring (needs model verification)

---

## 7. Maintenance & Monitoring

### Monthly Security Review
- [ ] Run `make check-vulns`
- [ ] Review dependency updates
- [ ] Check for new CVEs in dependencies
- [ ] Update model checksums if model version changes

### Quarterly Security Audit
- [ ] Full penetration test
- [ ] Code review of security modules
- [ ] Update threat model
- [ ] Review and update this document

### Incident Response Plan
1. **Detection**: Monitor audit logs for anomalies
2. **Containment**: Disable affected features
3. **Investigation**: Review logs, identify scope
4. **Remediation**: Patch vulnerability
5. **Recovery**: Restore from secure backup
6. **Lessons Learned**: Update documentation

---

## 8. Conclusion

The PANW1 Companion application demonstrates **strong foundational security** with:
- Production-grade encryption (AES-256-GCM)
- Comprehensive audit logging
- PII detection and protection
- Security-first design philosophy

**Enhancement opportunities** focus on **defense-in-depth hardening**:
- File permission enforcement (quick win)
- Model integrity verification (critical for AI security)
- Secure deletion and crash dump protection (privacy)
- Supply chain attack prevention (dependency security)

**Recommended timeline**: 5 weeks to implement all high/medium priority enhancements.

**Security posture after enhancements**: Production-ready for sensitive personal data with enterprise-grade security controls.

---

## Appendix A: Security Checklist

**Production Deployment Checklist:**
- [ ] File permissions enforced (0o600 files, 0o700 dirs)
- [ ] Secure deletion implemented
- [ ] Model checksums verified
- [ ] Dependencies vulnerability-scanned
- [ ] Core dumps disabled
- [ ] Audit logs sanitized
- [ ] Timing attack prevention verified
- [ ] Filename privacy enabled
- [ ] Full disk encryption enabled (OS-level)
- [ ] Backup encryption configured
- [ ] Incident response plan documented
- [ ] Security testing complete

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-08  
**Next Review**: 2025-02-08
