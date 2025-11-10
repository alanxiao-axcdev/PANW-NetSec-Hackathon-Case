# Companion - AI Security Infrastructure

**Production-Ready AI Security Demonstration** [youtube](https://youtu.be/SMf7vAfeAGY)

[![Tests](https://img.shields.io/badge/tests-413%20passing-success)]() [![Coverage](https://img.shields.io/badge/coverage-76%25-success)]() [![Security](https://img.shields.io/badge/security-6%20layers-blue)]()

---

## Overview

Companion is a comprehensive demonstration of enterprise-grade AI security infrastructure. While implemented as a journaling application, it showcases security patterns and research applicable to any AI system handling sensitive data.

The application demonstrates production-level security engineering and AI threat research methodologies suitable for security intelligence platforms, healthcare AI systems, legal technology, and enterprise automation.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/alanxiao-axcdev/PANW-NetSec-Hackathon-Case.git
cd PANW-NetSec-Hackathon-Case/PANW1

# Install dependencies
make install

# Activate virtual environment
source .venv/bin/activate

# Run the application
python -m companion.cli write

# Or view emotional trends
python -m companion.cli trends

# Verify all tests pass
python -m pytest -v | tail -5
```

**Interactive Writing Experience:**
- Authenticate at session start (passphrase requested first)
- Context-aware prompts from previous entries show as subtle gray placeholder text
- AI analyzes your writing patterns and suggests relevant reflection questions
- Meta+Enter or Esc+Enter to save your entry
- Ctrl+C to cancel at any time
- Natural terminal editor UX with intelligent guidance

**Visualize Your Patterns:**
```bash
# See emotional trends and recurring themes
python -m companion.cli trends
```
- Emotional delta (trending more positive/negative)
- Top themes frequency chart
- Sentiment distribution breakdown

---

## Security Architecture (6 Implemented Layers + 1 Designed)

**Defense-in-Depth (Implemented):**

1. **AES-256-GCM Encryption** - PBKDF2 (600k iterations)
2. **Key Rotation** - Zero data loss re-encryption
3. **Encrypted Audit Logs** - HMAC tamper detection
4. **Passphrase Strength** - NIST SP 800-63B enforcement
5. **Brute Force Protection** - Rate limiting + account lockout
6. **PII Detection** - Automatic data protection

**Designed (Not Yet Implemented):**
- **Layer 7: Memory Security** - Complete architecture designed (see docs/MEMORY_SECURITY.md)

---

## AI Security Research

**Novel Contributions:**
- 96.6% prompt injection detection (classic OWASP attacks)
- 86.8% detection on 2024-2025 advanced techniques
- 100% F1 on core PII types
- 70% data poisoning detection

**Research Finding**: Regex excellent for known patterns, gaps with obfuscation require semantic layer

**Test Datasets**: 135 labeled cases from latest research (FlipAttack, DeepSeek, ChatGPT exploits)

---

## Project Metrics

- 413 tests passing (100%)
- 76% coverage
- 71 commits total
- 38 modules implemented
- ~6,500 lines code
- ~9,431 lines documentation

---

## Key Documentation

**Technical Documentation:**
- `docs/THREAT_MODEL.md` - STRIDE analysis
- `docs/SECURITY.md` - Architecture
- `reports/security_test_report.md` - Real results
- `docs/DESIGN.md` - System design
- `ARCHITECTURE_AND_ROADMAP.md` - Implemented vs designed features

**Security Research:**
- `RESEARCH_METHODOLOGY.md` - Research narrative and findings

---

## Architecture

**38 Modules across 6 Domains:**
- Core (13): Models, config, storage, journal, session, passphrase prompt, AI engine, analyzer, prompter, summarizer, trends, CLI
- Security (6): Encryption, sandboxing, audit, PII detector, passphrase
- AI Backend (6): Base, Qwen, Ollama, OpenAI, Mock providers
- Security Research (5): Prompt injection, PII sanitizer, data poisoning, adversarial tester
- Monitoring (4): Metrics, health, dashboard
- Utils (4): Retry, circuit breaker, error classifier

---

## What Makes This Special

**Research Methodology:**
- Test, measure, find gaps, iterate
- Honest limitation assessment
- Next steps articulated

**Production Thinking:**
- Compliance (NIST, PCI-DSS, HIPAA, SOC 2)
- Key lifecycle management
- Audit trail protection
- Operational security

**Quality Assurance:**
- 413 automated tests
- 76% coverage
- Clean git history
- Comprehensive documentation

---

## AI Backend

**Qwen 2.5-1.5B (Default)**:
- Local inference (no API costs)
- Runs on CPU or GPU (CUDA auto-detected)
- First run downloads model (~3GB, cached)
- Requirements: `torch>=2.0.0`, `transformers>=4.35.0`
- Diagnostics: `companion health --ai`

**System Requirements**:
- 8GB+ RAM for Qwen
- 3-5GB disk space for model cache
- GPU optional (CPU mode works, ~2-5s per analysis)

**Installation**:
```bash
# Install with AI dependencies
make install

# Or manually add dependencies
uv add torch transformers

# Verify AI provider
companion health --ai
```

**Troubleshooting**: See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues.

---

## Deployment Status

**Demonstration**: Works with mock AI (no dependencies)
**Production**: Works with Qwen model integration
**Enterprise**: Demonstrates security patterns for production AI systems
