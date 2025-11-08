# Setting Up Qwen for Production Use

**Making Companion a real AI application, not just a demo**

---

## Why Real AI Matters

**Mock AI** is fine for testing, but for your PANW presentation:
- Shows you built a **real AI application**
- Demonstrates actual model integration
- Proves you can handle production ML workflows
- More impressive than hardcoded responses

---

## Qwen2.5-1.5B Setup

### Installation

The Qwen model will be downloaded automatically on first run (~3GB).

**System requirements:**
- 4GB+ RAM
- 5GB+ disk space
- Python 3.11+
- (Optional) CUDA for GPU acceleration

### Configuration

**Update config to use Qwen:**
```python
# In companion/ai_engine.py or companion/config.py
DEFAULT_PROVIDER = "qwen"  # Change from "mock"
```

Or via environment variable:
```bash
export COMPANION_AI_PROVIDER=qwen
```

### First Run

```bash
$ companion

Initializing Qwen2.5-1.5B model...
Downloading model files: [████████] 100% 2.8GB

Model loaded successfully!

Good morning! ✨
What's on your mind today?
```

---

## Testing with Real AI

**For unit tests**: Use mock (fast, deterministic)
**For integration tests**: Use Qwen (real behavior)
**For demo**: Use Qwen (shows it works!)

---

## Performance Expectations

**With Qwen2.5-1.5B (CPU):**
- First load: ~30 seconds
- Inference: ~2-5 seconds per prompt
- Memory usage: ~3.2GB

**With quantization** (future):
- Memory: ~800MB
- Inference: ~1-2 seconds

---

**This makes Companion a real, functional AI journaling companion!**
