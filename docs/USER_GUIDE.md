# Companion - User Guide

**Your empathetic journaling companion with complete privacy**

---

## What is Companion?

Companion is an AI-powered journaling application that runs entirely on your device. It provides thoughtful prompts, analyzes your emotional patterns, and generates insightful summaries—all while keeping your data completely private.

**Key Features**:
- 🤖 **Intelligent prompts** - Context-aware questions that appear when you need them
- 🔒 **Complete privacy** - Everything runs locally, nothing leaves your device
-  **Pattern recognition** - Automatic sentiment and theme detection
- 📝 **Insightful summaries** - Weekly and monthly reflection reports
- ⚡ **Zero configuration** - Works perfectly out of the box

---

## Installation

### Option 1: pipx (Recommended)

**One command install**:
```bash
pipx install companion-journal
```

That's it! Companion is now available as `companion` in your terminal.

**Why pipx?**
- Isolated environment (no conflicts with other Python tools)
- Automatically added to PATH
- Easy to upgrade: `pipx upgrade companion-journal`
- Easy to uninstall: `pipx uninstall companion-journal`

---

### Option 2: pip

```bash
pip install companion-journal
```

**Note**: Consider using a virtual environment to avoid conflicts:
```bash
python -m venv ~/.venvs/companion
source ~/.venvs/companion/bin/activate
pip install companion-journal
```

---

### Option 3: From Source (Developers)

```bash
git clone https://github.com/username/companion.git
cd companion
make install
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for details.

---

## First Run Experience

The first time you run Companion, it will:
1. Download the AI model (~3GB one-time download)
2. Create your journal directory
3. Set up encryption
4. Welcome you with a warm greeting

**Let's get started**:

```bash
$ companion

Welcome to Companion! 👋

I'm your private journaling companion. Let's get you set up.

This will take about 30 seconds:

1. Downloading AI model (Qwen2.5-1.5B, ~820MB)...
   [████████████████████] 100% - 3.2s

2. Creating your journal space at ~/.companion/

🔒 Create a passphrase to encrypt your journal:
   (Minimum 8 characters)

Passphrase: ********
Confirm: ********

 All set! Your journal is completely private and stays on this device.

Ready to start? (Press Enter)

───────────────────────────────────────────────

Good evening! 

What's on your mind today?

→ _
```

**That's it!** You're ready to journal.

---

## Daily Journaling

### Starting a New Entry

Just type `companion`:

```bash
$ companion
```

Companion will:
- Greet you based on time of day
- Give you a thoughtful prompt (if you pause for 15 seconds)
- Let you write freely
- Analyze your entry when you're done

### The Interactive Editor

**Companion uses a professional terminal editor** with intelligent prompts that appear when you need them.

**How it works**:

1. **Blank slate start** - No prompt shown initially, just an empty text area
2. **Idle detection** - After 15 seconds of no typing, contextual AI prompts appear
3. **Subtle placeholders** - Prompts show as *gray, italicized* text that disappears when you type
4. **Context-aware** - Prompts reference your recent entries and current writing
5. **Configurable timing** - Adjust idle threshold in config (default: 15 seconds)

**Keyboard Shortcuts**:
- **Ctrl+D** - Save entry and exit
- **Ctrl+C** - Cancel without saving

**Example session**:

```bash
$ companion write

Good evening! 🌙

_

[You pause for 15 seconds...]

Yesterday you mentioned work stress. How did today go?

[Gray italicized placeholder appears above. You start typing "A"...]

A_

[Placeholder disappears immediately, you continue writing...]

Actually had a breakthrough today. The solution was simpler than I thought...

[You finish and press Ctrl+D to save]

✓ Entry saved (3 min)

Sentiment: Stressed → Relief → Positive
Themes: Work, Problem-solving, Breakthrough

Great insight about perspective! See you tomorrow. 💚
```

**Duration Tracking**: Your writing time is automatically recorded for personal insights.

### Saving Your Entry

**To save and finish**:
- Press **Ctrl+D** - Saves entry and exits the editor

**To cancel without saving**:
- Press **Ctrl+C** - Exits without saving

### PII Warnings

If Companion detects personally identifiable information, you'll get a warning:

```bash
→ Had lunch with Sarah at 555-1234...

  Possible PII detected:
  • Name: "Sarah" (confidence: 85%)
  • Phone: "555-1234" (confidence: 99%)

Your journal is encrypted, but consider:
  [1] Save as-is (private journal - recommended)
  [2] Obfuscate before saving
  [3] Review and edit

Choice: _
```

**Recommendation**: Choose [1] for private journals. Your data is encrypted and never leaves your device.

---

## Viewing Past Entries

### List Recent Entries

```bash
$ companion list

Your Recent Entries
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2025-01-08  14:30  Breakthrough at work
            Positive • Work, Problem-solving

2025-01-07  19:15  Tough day, feeling overwhelmed
            Negative • Work, Stress, Anxiety

2025-01-06  10:22  Great morning run
            Positive • Health, Exercise, Mindfulness

2025-01-05  21:00  Reflecting on the week
            Neutral • Reflection, Planning

[Showing 4 of 47 entries]

Commands:
  companion list --all           Show all entries
  companion list --date 2025-01-08    Show specific date
  companion show <id>            Read full entry
```

### View Specific Entry

```bash
$ companion show 2025-01-08_143000

Entry from January 8, 2025 at 2:30 PM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actually had a breakthrough today. The solution was
simpler than I thought. I just needed to step back and
look at the problem differently. Talking to a colleague
helped me see it fresh.

───────────────────────────────────────────────

Sentiment: Frustrated → Relief → Positive
Themes: Work, Problem-solving, Collaboration
Duration: 3 minutes
```

---

## Summaries & Insights

### Weekly Summary

```bash
$ companion summary

Weekly Reflection (Jan 1-7, 2025)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 This Week: 7 entries

Emotional Journey:
  This week started with stress about the project deadline,
  but you found your footing midweek. The breakthrough on
  Wednesday marked a turning point—you shifted from feeling
  overwhelmed to feeling capable.

Dominant Themes:
  • Work & Career (5 entries)
  • Problem-solving (4 entries)
  • Self-care (3 entries)

Patterns Noticed:
  • Walks after difficult meetings help you process and reset
  • Talking through problems with colleagues provides clarity
  • Mornings tend to be more optimistic than evenings

Key Insight:
  You're learning to step back when stuck rather than pushing
  harder. This pattern of "pause → perspective → progress"
  appeared three times this week.

Looking Ahead:
  You mentioned wanting to establish better boundaries at work.
  How did that go this week?

 Reflection Prompt:
  What's one thing you learned about yourself this week?
```

### Monthly Summary

```bash
$ companion summary --month

Monthly Reflection (January 2025)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 This Month: 28 entries

[Detailed monthly analysis with trends, growth areas, and insights]
```

### Visual Trends Dashboard

See your emotional patterns at a glance with the trends visualization:

```bash
$ companion trends

Emotional Trends (Jan 1-7, 2025)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Emotional Journey
  Start of period:  0.45 (Neutral-leaning)
  End of period:    0.72 (Positive)

  Trend: ↗ Improving (+27%)

Top Themes
  work          ████████████████░░ (12 entries)
  health        ████████████░░░░░░ (9 entries)
  relationships ████████░░░░░░░░░░ (6 entries)
  stress        ██████░░░░░░░░░░░░ (4 entries)
  creativity    ████░░░░░░░░░░░░░░ (3 entries)

Emotional Distribution
  Positive  60% ████████████
  Neutral   30% ██████
  Negative  10% ██

7 entries analyzed
```

**Options:**
```bash
companion trends                    # Last week (default)
companion trends --period month     # Last 30 days
companion trends --period all       # All entries
companion trends --start 2025-01-01 --end 2025-01-31  # Custom range
```

**What the dashboard shows:**
- **Emotional Delta**: Whether you're trending more positive or negative
- **Top Themes**: What you write about most frequently
- **Sentiment Distribution**: Overall emotional breakdown

**Quick Insights:**
- Improving trend (↗) with +percentage means you're getting happier
- Top themes reveal what matters most in your life right now
- Distribution shows overall emotional balance

---

## Security Features

### Viewing Audit Log

See all AI operations for transparency:

```bash
$ companion audit

Security Audit Log
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2025-01-08 14:30:45  ENTRY_CREATED      entry_abc123
2025-01-08 14:30:48  INFERENCE_RUN      sentiment_analysis
2025-01-08 14:30:49  INFERENCE_RUN      theme_extraction
2025-01-08 14:30:50  ENTRY_ANALYZED     entry_abc123

2025-01-08 12:15:23  PII_DETECTED       entry_xyz789
                     Types: NAME, PHONE
                     Action: USER_WARNED

2025-01-07 19:20:12  ENTRY_CREATED      entry_def456
2025-01-07 19:20:15  INFERENCE_RUN      sentiment_analysis

[Showing 10 of 156 events]

Commands:
  companion audit --all              Show all events
  companion audit --date 2025-01-08  Show specific date
  companion audit --type SECURITY    Show security events only
```

### Exporting Your Journal

Export with automatic PII sanitization:

```bash
$ companion export --output my_journal.txt

  Export will be sanitized by default:
  • 12 names → [PERSON_N]
  • 3 phone numbers → [PHONE]
  • 2 addresses → [LOCATION]
  • 1 email → [EMAIL]

This protects your privacy if sharing with therapist, partner, etc.

Continue? [Y/n]: y

✓ Exported 47 entries to my_journal.txt (sanitized)

To export without sanitization (full raw journal):
  companion export --raw --output my_journal.txt
```

---

## Monitoring & Health

### Performance Metrics

View system performance:

```bash
$ companion metrics

Companion Performance Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Model Inference:
  P50:  198ms    P95:  445ms    P99:  891ms

Memory Usage:
  Current: 1.2GB    Peak: 1.4GB    Avg: 1.3GB

Storage:
  Entries: 47    Size: 235KB    Free: 128GB

Cache Performance:
  Hit Rate: 68%    Savings: 142 inference calls avoided

Health Status:  All systems operational

Last updated: 2 seconds ago
Press Ctrl+C to exit
```

### Health Check

Verify everything is working:

```bash
$ companion health

Companion Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 AI Model: Loaded and operational (Qwen2.5-1.5B-INT8)
 Storage: Accessible (~235KB used, 128GB free)
 Encryption: Operational (AES-256-GCM)
 Memory: Healthy (1.2GB / 16GB available)
 Disk Space: Sufficient (128GB free)

Overall Status:  HEALTHY

All systems operational. Your journal is ready to use.
```

---

## Configuration

### View Configuration

```bash
$ companion config

Current Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Data Directory: ~/.companion
AI Provider: Qwen (local)
Model: Qwen2.5-1.5B-INT8
Encryption: Enabled (AES-256-GCM)
PII Detection: Enabled
Cache: Enabled (68% hit rate)

To change settings, edit: ~/.companion/config.json
```

### Customize Settings

Edit `~/.companion/config.json`:

```json
{
  "editor": {
    "idle_threshold": 15
  },
  "security": {
    "pii_detection_enabled": true,
    "pii_sensitivity": "balanced"
  },
  "performance": {
    "enable_caching": true,
    "cache_similarity_threshold": 0.85
  }
}
```

**Options**:
- `editor.idle_threshold`: Seconds of idle time before showing prompt (default: 15)
- `pii_sensitivity`: `"paranoid"`, `"balanced"`, or `"relaxed"`
- `cache_similarity_threshold`: 0.0-1.0 (higher = stricter matching)

---

## All Commands Reference

### Basic Commands

```bash
companion                 # Write new entry (default action)
companion list            # List recent entries
companion show <id>       # View specific entry
companion summary         # Weekly insights
companion summary --month # Monthly insights
```

### Security Commands

```bash
companion audit           # View security audit log
companion export          # Export with PII sanitization
companion export --raw    # Export without sanitization
```

### System Commands

```bash
companion metrics         # Performance dashboard
companion health          # Health check
companion config          # View configuration
companion version         # Show version
companion help            # Show help
```

### Advanced Options

```bash
companion --no-cache      # Disable cache for this session
companion --debug         # Enable debug logging
companion --passphrase-file <path>  # Use passphrase from file
```

---

## Tips & Best Practices

### Getting the Most from Companion

**1. Write regularly** - Even 2-3 sentences daily helps establish patterns
- Consistency matters more than length
- Companion learns your style over time

**2. Be honest** - Your journal is encrypted and private
- Write authentically, no judgment
- The AI can't help if it doesn't know the real you

**3. Review summaries** - Weekly reflections reveal patterns you might miss
- Set a reminder for Sunday evenings
- Use insights for planning ahead

**4. Use prompts when stuck** - Let the 15-second pause work for you
- Don't force it if nothing comes to mind
- Prompts are suggestions, not requirements

**5. Experiment with formats** - There's no "right" way to journal
- Bullet points work fine
- Stream of consciousness works too
- Find what feels natural

### Privacy & Security Tips

**1. Choose a strong passphrase**
- Minimum 8 characters (longer is better)
- Mix letters, numbers, symbols
- Don't use common phrases or personal info
- Consider a passphrase manager (1Password, Bitwarden)

**2. Be aware of backups**
- Your system backups (Time Machine, iCloud) include encrypted journal
- Encrypted data is safe even in cloud backups
- If paranoid, exclude `~/.companion/` from cloud sync

**3. Lock your computer**
- Companion protects data at rest (when saved)
- Can't protect active session if computer unlocked
- Enable screen lock after inactivity

**4. Export carefully**
- Sanitized exports are safer for sharing
- Raw exports contain all your data
- Store exported files securely

---

## Troubleshooting

### "Model download failed"

**Problem**: Network issues during first run

**Solutions**:
```bash
# Retry download
companion --download-model

# Or download manually
mkdir -p ~/.companion/models
cd ~/.companion/models
wget https://huggingface.co/Qwen/Qwen2.5-1.5B-INT8/resolve/main/...
```

---

### "Decryption failed" or "Wrong passphrase"

**Problem**: Incorrect passphrase or corrupted data

**Solutions**:
- Double-check passphrase (case-sensitive)
- Ensure Caps Lock is off
- If truly forgotten, data cannot be recovered (this is by design for security)

---

### "Model loading slow" or "High memory usage"

**Problem**: Insufficient system resources

**Solutions**:
```bash
# Check system resources
companion health

# Close other applications
# Consider lighter model (future feature)
```

**Minimum requirements**:
- 4GB RAM (8GB recommended)
- 2GB free disk space
- Modern CPU (2015+ recommended)

---

### "Cache not working" or "Slow prompts"

**Problem**: Cache disabled or ineffective

**Solutions**:
```bash
# Check cache status
companion metrics

# Enable cache in config
# Edit ~/.companion/config.json
"performance": {
  "enable_caching": true
}

# Clear cache if corrupted
rm -rf ~/.companion/cache
```

---

### "PII detection too sensitive" (many false positives)

**Problem**: Legitimate content flagged as PII

**Solutions**:
```json
// Edit ~/.companion/config.json
"security": {
  "pii_sensitivity": "relaxed"  // Was "balanced" or "paranoid"
}
```

---

## Frequently Asked Questions

### Is my data really private?

**Yes.** Companion:
- Runs entirely on your device (no cloud processing)
- Encrypts all entries at rest (AES-256-GCM)
- Never sends data over the network (except model download)
- Logs all AI operations for transparency (audit log)

You can verify: disconnect from internet and it still works perfectly.

---

### Can I use this as actual therapy?

**No.** Companion is a **journaling tool**, not a replacement for professional mental health care.

**Use Companion for**:
- Self-reflection and insight
- Emotional processing
- Pattern recognition
- Daily mindfulness practice

**Seek professional help for**:
- Mental health conditions (depression, anxiety, etc.)
- Crisis situations
- Trauma processing
- Medical advice

If you're struggling, please contact:
- National Suicide Prevention Lifeline: 988
- Crisis Text Line: Text HOME to 741741
- Your healthcare provider

---

### Does the AI really understand me?

**Sort of.** The AI:
- Recognizes emotional patterns (sentiment analysis)
- Identifies topics and themes (natural language processing)
- Generates contextual prompts (based on your history)

But it **doesn't**:
- Have true understanding or consciousness
- Remember conversations (only patterns)
- Judge or evaluate you
- Replace human connection

Think of it as a **tool for self-reflection**, not a relationship.

---

### Can I use multiple devices?

**Currently**: Companion works on single device only.

**Future**: Encrypted cloud sync planned for v2.0

**Workaround now**:
```bash
# On device 1: Export encrypted backup
tar -czf companion_backup.tar.gz ~/.companion

# Transfer to device 2 (USB, secure file transfer)
# On device 2: Restore
tar -xzf companion_backup.tar.gz -C ~/
```

---

### How much disk space do I need?

**Initial**:
- Model: 820MB (one-time download)
- Application: ~50MB

**Ongoing**:
- Per entry: ~5KB (encrypted)
- 365 entries/year: ~1.8MB
- 10 years: ~18MB

**Cache**:
- Embeddings: ~100MB (grows slowly)

**Total for 1 year**: ~1GB

---

### Can I change the AI model?

**Currently**: Qwen2.5-1.5B-INT8 only (optimized for privacy + performance)

**Future**: Pluggable models planned
- Ollama integration
- Larger models for better quality
- Smaller models for low-end devices
- Custom fine-tuned models

---

### What happens if I lose my passphrase?

**Short answer**: Your data is **permanently inaccessible**.

**Why**: True encryption means even we (the developers) can't decrypt your data without the passphrase. This is a feature, not a bug—it ensures your privacy.

**Prevention**:
- Store passphrase in password manager (1Password, Bitwarden, etc.)
- Write it down physically in a secure location
- Use passphrase that's memorable but strong

---

## Getting Help

### Documentation

- **User Guide**: This file
- **Security Details**: [SECURITY.md](SECURITY.md)
- **Architecture**: [DESIGN.md](DESIGN.md)
- **Development**: [DEVELOPMENT.md](DEVELOPMENT.md)

### Community

- **GitHub Issues**: https://github.com/username/companion/issues
- **Discussions**: https://github.com/username/companion/discussions
- **Email**: support@companion-journal.com

### Reporting Bugs

```bash
# Include debug information
companion --debug > debug.log

# Create issue at GitHub with:
# - Description of problem
# - Steps to reproduce
# - Debug log (remove any sensitive data first!)
# - System info (OS, Python version, RAM)
```

---

## What's Next?

You're all set! Start journaling:

```bash
companion
```

Remember:
- 💭 **Be authentic** - Your journal is private
- 📝 **Write regularly** - Even a few sentences help
- 🔍 **Review summaries** - Discover patterns over time
- 🔒 **Stay secure** - Use strong passphrase, lock computer

Happy journaling! 💚

---

**Document Version**: 1.0
**Last Updated**: 2025-01-08
**For Version**: Companion v0.1.0
