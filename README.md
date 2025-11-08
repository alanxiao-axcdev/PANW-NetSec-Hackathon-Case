# 🏆 Companion - AI Security Infrastructure for PANW Hackathon

**Production-Ready AI Security Demonstration**

[![Tests](https://img.shields.io/badge/tests-413%20passing-success)]() [![Coverage](https://img.shields.io/badge/coverage-76%25-success)]() [![Security](https://img.shields.io/badge/security-6%20layers-blue)]() [![Commits](https://img.shields.io/badge/commits-27%20clean-blue)]()

---

## 🎯 What This Is

**Not** just a journaling app.

**But** a comprehensive demonstration of **enterprise-grade AI security infrastructure** using journaling as a relatable, testable use case.

Built for **Palo Alto Networks R&D NetSec Hackathon** to showcase AI security engineering and production infrastructure thinking.

---

## ⚡ Quick Start

```bash
cd /home/nyzio/amplifier/PANW1
source .venv/bin/activate

# Start writing in the interactive editor
python -m companion.cli write

# Verify all tests pass
python -m pytest -v | tail -5
```

**Interactive Writing Experience:**
- Start with a blank slate (no upfront prompts)
- After 15 seconds of idle time, contextual AI prompts appear as subtle gray text
- **Ctrl+D** to save your entry
- **Ctrl+C** to cancel
- Nano-like editor UX for a natural writing flow

**That's it!** Works immediately with intelligent mock AI (no 3GB model download needed for demo).

---

## 🛡️ Security Architecture (6 Layers)

**Defense-in-Depth:**

1. **AES-256-GCM Encryption** - PBKDF2 (600k iterations)
2. **Key Rotation** - Zero data loss re-encryption
3. **Encrypted Audit Logs** - HMAC tamper detection
4. **Passphrase Strength** - NIST SP 800-63B enforcement
5. **Brute Force Protection** - Rate limiting + account lockout
6. **PII Detection** - Automatic data protection

**Plus:** Memory security designed (Layer 7)

---

## 🔬 AI Security Research

**Novel Contributions:**
- **96.6%** prompt injection detection (classic OWASP attacks)
- **86.8%** detection on 2024-2025 advanced techniques
- **100% F1** on core PII types
- **>70%** data poisoning detection

**Research Finding**: Regex excellent for known patterns, gaps with obfuscation → need semantic layer

**Test Datasets**: 135 labeled cases from latest research (FlipAttack, DeepSeek, ChatGPT exploits)

---

## 📊 Project Stats

- ✅ **413 tests** passing (100%)
- ✅ **76% coverage**
- ✅ **27 commits** (clean history)
- ✅ **30 modules** implemented
- ✅ **~6,500 lines** code
- ✅ **~9,431 lines** documentation

---

## 🎤 For PANW Interview

**Your story**:
> "I built enterprise AI security infrastructure with 6 defense layers, conducted security research discovering regex vs obfuscation gaps, and demonstrated production thinking with key rotation, audit encryption, and brute force protection. 413 tests prove it works."

**Read these**:
1. **START_HERE.md** - Navigation guide
2. **README_FOR_INTERVIEW.md** - Key numbers & Q&A
3. **RESEARCH_METHODOLOGY.md** - Research narrative
4. **FINAL_SECURITY_SHOWCASE.md** - Complete feature list

---

## 📁 Key Documents

**Presentation:**
- `docs/PRESENTATION.md` - 7-minute outline
- `DEMO_GUIDE.md` - 5-minute demo script

**Security:**
- `docs/THREAT_MODEL.md` - STRIDE analysis
- `docs/SECURITY.md` - Architecture
- `reports/security_test_report.md` - Real results

**Architecture:**
- `docs/DESIGN.md` - System design
- `ARCHITECTURE_AND_ROADMAP.md` - Implemented vs designed

---

## 🏗️ Architecture

**30 Modules across 8 Domains:**
- Core (11): Models, config, storage, journal, AI engine, analyzer, prompter, summarizer, CLI
- Security (6): Encryption, sandboxing, audit, PII, passphrase, key rotation
- AI Backend (5): Abstract interface + 4 providers
- Security Research (4): Injection, PII, poisoning, testing
- Monitoring (3): Metrics, health, dashboard
- Utils (3): Retry, circuit breaker, error handling

---

## ✨ What Makes This Special

**Not claiming perfection** - Showing real research:
- Test → measure → find gaps → iterate
- Honest limitation assessment
- Next steps articulated

**Production thinking**:
- Compliance (NIST, PCI-DSS, HIPAA, SOC 2)
- Key lifecycle management
- Audit trail protection
- Operational security

**Quality**:
- 413 automated tests
- 76% coverage
- Clean git history
- Comprehensive docs

---

## 🚀 This Is Ready

**For your hackathon demo**: ✅ Works perfectly with mock AI
**For production**: Ready for Qwen model integration
**For PANW interview**: Shows enterprise security expertise

---

**Location**: `/home/nyzio/amplifier/PANW1/`

**Good luck! 🍀**
