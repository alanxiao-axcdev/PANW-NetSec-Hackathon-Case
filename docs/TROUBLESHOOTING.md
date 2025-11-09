# Troubleshooting Guide

This guide helps diagnose and resolve common issues with Companion.

---

## AI Provider Issues

### Qwen Initialization Failures

The Qwen AI provider requires specific dependencies and system resources. If sentiment analysis or theme extraction isn't working, the Qwen model may have failed to initialize.

#### Quick Diagnostic

```bash
# Check AI provider health
companion health --ai
```

This command reports:
- Provider name and initialization status
- Model loading status
- Last inference time
- Recent error count
- Specific error messages with solutions

#### Common Causes

**1. Missing Dependencies**

**Symptom**: Error about missing `torch` or `transformers`

**Cause**: PyTorch or Transformers not installed

**Solution**:
```bash
# Ensure in project directory
cd PANW1

# Install dependencies
uv add torch transformers
```

**2. Insufficient Memory**

**Symptom**: `RuntimeError: CUDA out of memory` or system freeze during initialization

**Cause**: Qwen2.5-1.5B requires ~3-4GB RAM

**Solution**:
- Close other applications
- Use CPU mode (automatic fallback)
- Upgrade system RAM

**3. CUDA Not Available**

**Symptom**: Warning about CUDA, slow inference times

**Cause**: No NVIDIA GPU or CUDA drivers not installed

**Solution**: This is not an error - Qwen automatically falls back to CPU mode. CPU inference works but is slower (2-5 seconds vs <1 second on GPU).

**4. Model Download Failure**

**Symptom**: Long initialization with network errors

**Cause**: HuggingFace model download interrupted or blocked

**Solution**:
```bash
# Check network connectivity
ping huggingface.co

# Manually download model (if needed)
python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2.5-1.5B')"

# Check disk space (model is ~3GB)
df -h ~
```

**5. Incompatible Transformers Version**

**Symptom**: Deprecation warnings or parameter errors

**Cause**: Using outdated transformers library

**Solution**:
```bash
# Update transformers
uv add transformers>=4.35.0

# Verify version
python -c "import transformers; print(transformers.__version__)"
```

#### Expected Behavior

When Qwen initializes successfully:

```bash
$ companion health --ai
AI Provider Health Check
========================

Provider: QwenProvider
Status: ✓ Initialized
Model: Qwen/Qwen2.5-1.5B loaded
Device: cuda (or cpu if no GPU)
Last Inference: 245ms
Error Count: 0

All systems operational.
```

#### Error Messages Explained

**"Qwen initialization failed"**
- Check logs for specific error
- Run `companion health --ai` for detailed diagnosis
- Ensure dependencies installed: `torch>=2.0.0`, `transformers>=4.35.0`

**"Provider not initialized"**
- AI engine couldn't load any provider
- Run diagnostic: `companion health --ai`
- Check system resources (RAM, disk space)

**"Generation failed"**
- Model loaded but inference failed
- Usually transient - retry works
- If persistent, check logs for details

#### Debugging Steps

1. **Check provider health**:
   ```bash
   companion health --ai
   ```

2. **Verify dependencies**:
   ```bash
   python -c "import torch, transformers; print('torch:', torch.__version__); print('transformers:', transformers.__version__)"
   ```

3. **Check system resources**:
   ```bash
   # RAM usage
   free -h

   # Disk space
   df -h ~/.cache/huggingface
   ```

4. **Test manual initialization**:
   ```python
   from companion.ai_backend.qwen_provider import QwenProvider
   import asyncio

   async def test():
       qp = QwenProvider()
       await qp.initialize()
       result = await qp.generate("Test prompt", max_tokens=10)
       print(f"Success: {result}")

   asyncio.run(test())
   ```

5. **Check logs**:
   - Logs show initialization details
   - Look for specific error messages
   - Errors include actionable solutions

---

## Encryption Issues

### Passphrase Not Working

**Symptom**: "Incorrect passphrase" error even with correct passphrase

**Cause**: Passphrase hash may be corrupted

**Solution**:
```bash
# Check passphrase hash exists
ls ~/.companion/config.json

# If corrupted, you'll need to reset (loses access to encrypted entries)
# Backup first!
cp -r ~/.companion ~/.companion.backup
```

### Can't Decrypt Old Entries

**Symptom**: Entries from before key rotation won't decrypt

**Cause**: This shouldn't happen - key rotation re-encrypts all entries

**Solution**: File a bug report with logs

---

## Performance Issues

### Slow Sentiment Analysis

**Expected**: First analysis takes longer (model loading)
**Subsequent**: Should be fast (<1 second)

**If consistently slow**:
1. Check if running on CPU (see CUDA issues above)
2. Verify model is cached: `ls ~/.cache/huggingface/hub/`
3. Close other applications consuming RAM

### High Memory Usage

**Expected**: ~4GB with Qwen loaded
**If higher**: May indicate memory leak

**Solution**:
```bash
# Restart application
# If persistent, file bug report
```

---

## Installation Issues

### uv command not found

**Symptom**: `make install` fails with "uv: command not found"

**Solution**:
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### Permission Denied Errors

**Symptom**: Can't write to ~/.companion

**Solution**:
```bash
# Check permissions
ls -ld ~/.companion

# Fix if needed
chmod 700 ~/.companion
```

---

## Getting Help

If issues persist:

1. **Check logs** - Look for specific error messages
2. **Run diagnostics** - `companion health --ai`
3. **File bug report** - Include:
   - Error message
   - Output of `companion health --ai`
   - Python version: `python --version`
   - OS: `uname -a` (Linux/Mac) or `ver` (Windows)
   - Steps to reproduce

---

## Quick Reference

| Issue | Command | Expected Result |
|-------|---------|-----------------|
| AI not working | `companion health --ai` | Shows provider status |
| Slow analysis | Check CPU vs GPU | GPU = <1s, CPU = 2-5s |
| Missing deps | `uv add torch transformers` | Installs AI dependencies |
| Model download | `ls ~/.cache/huggingface` | Shows cached models |
| Test Qwen | Python script above | Prints "Success: [text]" |
