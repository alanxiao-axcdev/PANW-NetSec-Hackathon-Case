# Code Implementation Plan

**Generated**: 2025-11-08
**Based on**: Phase 1 plan + Phase 2 documentation

---

## Summary

Implement interactive journal editor with idle-time contextual prompts by:
1. Removing `word_count` field from JournalEntry model and all related code
2. Adding `editor_idle_threshold` configuration setting
3. Replacing basic `input()` loop with `prompt_toolkit` interactive editor
4. Implementing idle detection with gray italicized placeholder prompts
5. Tracking actual writing duration (using existing `duration_seconds` field)

**Scope**: 6 code files, ~250 lines changed/added, ~100 lines removed

---

## Files to Change

### File: companion/models.py

**Location**: `/home/nyzio/amplifier/PANW1/companion/models.py`

**Current State**:
- `JournalEntry` has `word_count: int = 0` field (line 64)
- `word_count` docstring in class (line 52)
- Auto-calculation in `__init__` (lines 72-73): calculates word count from content
- `Config` class exists (lines 120-143) but lacks `editor_idle_threshold`
- `duration_seconds` field exists but always set to 0

**Required Changes**:

**Remove**:
- Line 52: `word_count` docstring entry
- Line 64: `word_count: int = 0` field declaration
- Lines 72-73: Auto-calculation logic in `__init__`

**Add to Config class** (after line 143):
```python
editor_idle_threshold: int = 15  # Seconds of idle time before showing prompt
```

**Update docstring** (line 53):
- Change from: `duration_seconds: How long user spent writing`
- To: `duration_seconds: Writing time tracked by interactive editor (in seconds)`

**Dependencies**: None (foundational change)

**Agent Suggestion**: modular-builder

---

### File: companion/config.py

**Location**: `/home/nyzio/amplifier/PANW1/companion/config.py`

**Current State**:
- Loads and saves `Config` model from models.py
- No changes needed to load/save logic (Config is in models.py)
- Functions: `load_config()`, `save_config()`, `get_data_dir()`

**Required Changes**:

**None** - This file just loads/saves the Config model. Changes are in models.py.

**Verification**: After models.py changes, verify this still works correctly.

**Agent Suggestion**: N/A (no changes)

---

### File: companion/cli.py

**Location**: `/home/nyzio/amplifier/PANW1/companion/cli.py`

**Current State**:
- `write()` command (lines 137-223) uses basic `input()` loop
- Shows prompt BEFORE writing starts (lines 151-156)
- Basic input loop (lines 160-174)
- Calculates word_count (line 181)
- Passes word_count to JournalEntry (line 184)
- Displays word_count in confirmation (line 192)
- Hardcodes `duration_seconds=0` (line 185)
- Shows word_count in `list_entries` (line 113)
- Shows word_count in `show()` command (line 299)

**Required Changes**:

**Add new function** (before `write()` command, around line 136):
```python
async def _run_interactive_editor(
    prompter: Prompter,
    recent_entries: list[JournalEntry],
    idle_threshold: int = 15
) -> tuple[str | None, int]:
    """Run interactive editor with idle-time prompts.

    Args:
        prompter: AI prompt generator
        recent_entries: Context for prompt generation
        idle_threshold: Seconds before showing prompt

    Returns:
        Tuple of (text, duration_seconds) or (None, 0) if cancelled
    """
    # Implementation: ~100 lines
    # - Set up prompt_toolkit Application with TextArea
    # - Background task for idle detection
    # - Dynamic placeholder with gray italic styling
    # - Ctrl+D to save, Ctrl+C to cancel
    # - Track writing duration
```

**Modify `write()` command** (lines 137-223):
- Remove lines 146-158: Initial prompt display and instructions
- Remove lines 160-174: Basic input() loop
- Remove lines 181: word_count calculation
- Remove line 184: word_count parameter
- Remove line 192: word_count in output
- Update line 185: Use actual duration from editor instead of 0

**New flow**:
```python
@main.command()
def write() -> None:
    """Write a new journal entry."""
    _display_greeting()

    # Get recent entries for context
    recent_entries = journal.get_recent_entries(limit=5)

    # Load idle threshold from config
    config = load_config()
    idle_threshold = config.editor_idle_threshold

    # Run interactive editor
    result = asyncio.run(_run_interactive_editor(
        prompter=prompter,
        recent_entries=recent_entries,
        idle_threshold=idle_threshold
    ))

    content, duration = result

    if content is None:
        console.print("\n[yellow]Entry cancelled.[/yellow]")
        return

    if not content.strip():
        console.print("\n[yellow]Empty entry not saved.[/yellow]")
        return

    # Create entry with duration
    entry = JournalEntry(
        content=content,
        duration_seconds=duration
    )

    # Save and analyze (existing code, lines 188-221)
    # ... keep rest of existing logic
```

**Remove word_count display** (other commands):
- Line 113 in `list_entries()`: Remove `" {entry.word_count} words` from themes display
- Line 299 in `show()`: Remove `Word count:` line entirely

**Dependencies**: companion/models.py must be updated first (Config class)

**Agent Suggestion**: modular-builder

---

### File: companion/summarizer.py

**Location**: `/home/nyzio/amplifier/PANW1/companion/summarizer.py`

**Current State**:
- Lines 133-134: Uses `word_count` for statistics calculation
```python
word_counts = [entry.word_count for entry in entries]
avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
```

**Required Changes**:

**Remove** (lines 133-134):
```python
word_counts = [entry.word_count for entry in entries]
avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
```

**Impact**: Weekly/monthly summaries will no longer include average word count statistic.

**Verification**: Check if `avg_words` variable is used elsewhere in the function. If so, remove those references too.

**Dependencies**: None (isolated change)

**Agent Suggestion**: modular-builder

---

### File: tests/test_models.py

**Location**: `/home/nyzio/amplifier/PANW1/tests/test_models.py`

**Current State**:
- Line 87: Assertion checking `entry.word_count == 2`
- Lines 89-92: Dedicated `test_word_count_calculation()` test

**Required Changes**:

**Modify line 87** (in existing test):
- Remove assertion: `assert entry.word_count == 2`

**Remove entire test** (lines 89-92):
```python
def test_word_count_calculation(self):
    """Test that word count is calculated automatically."""
    entry = JournalEntry(content="This is a test entry with eight words")
    assert entry.word_count == 8
```

**Add new test**:
```python
def test_journal_entry_no_word_count(self):
    """Test JournalEntry no longer has word_count field."""
    entry = JournalEntry(content="Test", duration_seconds=60)
    assert not hasattr(entry, "word_count")

def test_journal_entry_duration_preserved(self):
    """Test duration_seconds field works correctly."""
    entry = JournalEntry(content="Test", duration_seconds=120)
    assert entry.duration_seconds == 120
```

**Dependencies**: None (test-only changes)

**Agent Suggestion**: modular-builder

---

### File: tests/test_cli.py

**Location**: `/home/nyzio/amplifier/PANW1/tests/test_cli.py`

**Current State**:
- Lines 112, 118, 174, 352: Mock JournalEntry creation includes `word_count=` parameter
- Tests use `CliRunner` with `input=` parameter to simulate stdin
- Tests check for word count in output

**Required Changes**:

**Remove `word_count` from mock entries**:
- Line 112: Remove `word_count=3,`
- Line 118: Remove `word_count=3,`
- Line 174: Remove `word_count=6,`
- Line 352: Remove `word_count=4,`

**Update test assertions**:
- Find and remove assertions checking for word count in command output
- Update to check for duration instead

**Add new tests for interactive editor**:
```python
@pytest.mark.asyncio
async def test_interactive_editor_save(mock_config, mock_journal):
    """Test interactive editor saves with Ctrl+D."""
    # Mock _run_interactive_editor to return text and duration
    # Verify journal.save_entry called with duration_seconds > 0

@pytest.mark.asyncio
async def test_interactive_editor_cancel(mock_config, mock_journal):
    """Test interactive editor cancels with Ctrl+C."""
    # Mock _run_interactive_editor to return (None, 0)
    # Verify journal.save_entry NOT called

async def test_idle_threshold_from_config(mock_config):
    """Test editor uses idle_threshold from config."""
    # Set mock_config.editor_idle_threshold = 20
    # Verify _run_interactive_editor called with idle_threshold=20

def test_duration_tracking(mock_config, mock_journal):
    """Test duration is properly tracked and saved."""
    # Mock editor returns duration=45
    # Verify entry saved with duration_seconds=45
```

**Dependencies**: companion/cli.py changes (editor function must exist)

**Agent Suggestion**: modular-builder + test-coverage

---

## Implementation Chunks

### Chunk 1: Remove word_count (Foundational Cleanup)

**Files**:
- `companion/models.py` - Remove field and auto-calculation
- `companion/summarizer.py` - Remove word count statistics
- `tests/test_models.py` - Remove word count tests

**Description**: Clean removal of word_count feature from data model and all usage

**Why first**: Other code depends on JournalEntry model. Removing field first prevents build errors.

**Test strategy**:
```bash
pytest tests/test_models.py -v
pytest tests/ -k "not word_count" -v
```

**Expected result**: Tests pass, no references to word_count remain

**Dependencies**: None

**Commit point**: After `pytest tests/test_models.py` passes

**Commit message**:
```
refactor: remove word_count field from JournalEntry

- Remove word_count field from model
- Remove auto-calculation in __init__
- Remove word count statistics from summarizer
- Remove word_count tests
- Duration tracking is sufficient for session analytics
```

---

### Chunk 2: Add Configuration (Prepare for Editor)

**Files**:
- `companion/models.py` - Add `editor_idle_threshold` to Config class

**Description**: Add configuration field for editor idle detection

**Why second**: Editor implementation (Chunk 3) needs this config field

**Test strategy**:
```python
# Manual verification
from companion.config import load_config
config = load_config()
assert hasattr(config, 'editor_idle_threshold')
assert config.editor_idle_threshold == 15  # Default value
```

**Expected result**: Config loads with new field, default value 15

**Dependencies**: Chunk 1 complete (models.py changes)

**Commit point**: After manual verification passes

**Commit message**:
```
feat: add configurable idle threshold for editor

- Add editor_idle_threshold field to Config (default: 15)
- Users can customize when prompts appear
```

---

### Chunk 3: Implement Interactive Editor (Core Feature)

**Files**:
- `companion/cli.py` - Add `_run_interactive_editor()` function
- `companion/cli.py` - Modify `write()` command
- `companion/cli.py` - Remove word_count display from other commands

**Description**: Replace basic input() with prompt_toolkit interactive editor

**Why third**: Requires Config changes from Chunk 2

**Specific Implementation**:

**Step 3a: Add imports** (after existing imports, around line 20):
```python
import time
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
```

**Step 3b: Add `_run_interactive_editor()` function** (before `write()`, around line 136):
```python
async def _run_interactive_editor(
    prompter: Prompter,
    recent_entries: list[JournalEntry],
    idle_threshold: int = 15
) -> tuple[str | None, int]:
    """Run interactive editor with idle-time prompts.

    Provides nano-like editing experience with intelligent AI prompts
    that appear after idle_threshold seconds of no typing.

    Args:
        prompter: AI prompt generator
        recent_entries: Recent entries for context
        idle_threshold: Seconds before showing placeholder (default 15)

    Returns:
        Tuple of (final_text, duration_seconds) if saved with Ctrl+D
        Tuple of (None, 0) if cancelled with Ctrl+C
    """
    import asyncio
    from datetime import datetime

    # Track session start for duration
    start_time = time.time()

    # Create text area
    text_area = TextArea(
        multiline=True,
        wrap_lines=True,
        text="",  # Start empty (blank slate)
        scrollbar=False,
    )

    # Track idle time
    last_activity = asyncio.get_event_loop().time()

    # Placeholder styling - gray italic
    style = Style.from_dict({
        'placeholder': 'italic #888888',
    })

    # Idle detection background task
    async def check_idle():
        """Monitor idle time and update placeholder."""
        nonlocal last_activity

        while True:
            await asyncio.sleep(1)  # Check every second

            idle_duration = asyncio.get_event_loop().time() - last_activity

            if idle_duration >= idle_threshold:
                # Get AI-generated placeholder
                try:
                    placeholder_text = await prompter.get_placeholder_text(
                        current_text=text_area.text,
                        idle_duration=idle_duration,
                        recent_entries=recent_entries
                    )

                    # Set placeholder with italic gray styling
                    if placeholder_text:
                        text_area.placeholder = FormattedText([
                            ('class:placeholder', placeholder_text)
                        ])
                except Exception as e:
                    logger.debug(f"Failed to generate placeholder: {e}")
                    # Silent failure - editor continues working

    # On text change, reset idle timer and clear placeholder
    def on_text_changed(_):
        nonlocal last_activity
        last_activity = asyncio.get_event_loop().time()
        text_area.placeholder = ""  # Clear placeholder on typing

    text_area.buffer.on_text_changed += on_text_changed

    # Key bindings
    kb = KeyBindings()

    @kb.add('c-d')  # Ctrl+D to save
    def save(event):
        """Save entry and exit."""
        event.app.exit(result=text_area.text)

    @kb.add('c-c')  # Ctrl+C to cancel
    def cancel(event):
        """Cancel without saving."""
        event.app.exit(result=None)

    # Create application
    app = Application(
        layout=Layout(text_area),
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )

    # Start idle checker
    idle_task = asyncio.create_task(check_idle())

    try:
        # Run editor
        result = await app.run_async()

        # Calculate duration
        duration = int(time.time() - start_time)

        return (result, duration)

    finally:
        # Clean up background task
        idle_task.cancel()
        try:
            await idle_task
        except asyncio.CancelledError:
            pass
```

**Step 3c: Modify `write()` command** (lines 137-223):

Replace entire function body with:
```python
@main.command()
def write() -> None:
    """Write a new journal entry.

    Opens an interactive editor with intelligent prompts that appear
    when you pause. Press Ctrl+D to save, Ctrl+C to cancel.
    """
    _display_greeting()

    # Get recent entries for context
    recent_entries = journal.get_recent_entries(limit=5)

    # Load idle threshold from config
    config_obj = config.load_config()
    idle_threshold = config_obj.editor_idle_threshold

    # Run interactive editor
    try:
        content, duration = asyncio.run(_run_interactive_editor(
            prompter=prompter,
            recent_entries=recent_entries,
            idle_threshold=idle_threshold
        ))
    except Exception as e:
        logger.error(f"Editor failed: {e}")
        console.print("\n[red]Editor error. Please try again.[/red]")
        return

    # Handle cancellation
    if content is None:
        console.print("\n[yellow]Entry cancelled.[/yellow]")
        return

    # Handle empty entry
    if not content.strip():
        console.print("\n[yellow]Empty entry not saved.[/yellow]")
        return

    # Create entry with duration
    entry = JournalEntry(
        content=content.strip(),
        duration_seconds=duration
    )

    # Save entry
    with console.status("[cyan]Saving entry..."):
        journal.save_entry(entry)

    console.print(f"\n Entry saved ({duration // 60} min)", style="green")

    # Analyze in background (existing code, keep as-is)
    console.print("\n[dim]Analyzing...[/dim]")

    try:
        async def analyze_entry() -> tuple[JournalEntry, str]:
            sentiment = await analyzer.analyze_sentiment(entry.content)
            themes = await analyzer.extract_themes(entry.content)

            entry.sentiment = sentiment
            entry.themes = [theme.name for theme in themes[:5]]
            journal.save_entry(entry)

            themes_str = ", ".join(entry.themes) if entry.themes else "None detected"
            return entry, themes_str

        analyzed_entry, themes_str = asyncio.run(analyze_entry())

        console.print(f"\nSentiment: [cyan]{analyzed_entry.sentiment.label.title()}[/cyan]", style="dim")
        console.print(f"Themes: [cyan]{themes_str}[/cyan]\n", style="dim")

    except Exception as e:
        logger.error("Analysis failed: %s", e)
        console.print("\n[yellow]Note: Analysis could not be completed[/yellow]", style="dim")

    console.print("See you next time! =š\n", style="bold green")
```

**Step 3d: Remove word_count from `list_entries()`** (line 113):
Change from:
```python
f"[dim]    Themes: {themes_str} " {entry.word_count} words[/dim]"
```
To:
```python
f"[dim]    Themes: {themes_str}[/dim]"
```

**Step 3e: Remove word_count from `show()`** (line 299):
Remove entire line:
```python
console.print(f"Word count: [cyan]{entry.word_count}[/cyan]", style="dim")
```

**Test strategy**:
```bash
# Manual test - run the actual command
python -m companion.cli write
# - Verify blank slate start
# - Verify idle prompt appears after 15s
# - Verify Ctrl+D saves
# - Verify Ctrl+C cancels
# - Verify duration tracked

# Check other commands
python -m companion.cli list
# - Verify no word count shown

python -m companion.cli show <entry-id>
# - Verify no word count shown
```

**Dependencies**: Chunks 1 and 2 complete

**Commit point**: After manual testing succeeds

**Commit message**:
```
feat: interactive editor with idle-time prompts

- Implement prompt_toolkit-based interactive editor
- Blank slate start (no upfront prompts)
- Idle detection with configurable threshold
- Gray italicized placeholder prompts from AI
- Ctrl+D to save, Ctrl+C to cancel
- Track actual writing duration
- Remove word count display from all commands
- Nano-like terminal editing experience
```

---

### File: tests/test_cli.py

**Location**: `/home/nyzio/amplifier/PANW1/tests/test_cli.py`

**Current State**:
- Mock JournalEntry objects include `word_count` parameter (lines 112, 118, 174, 352)
- Tests use `CliRunner.invoke()` with `input=` parameter
- Tests may check for word count in output

**Required Changes**:

**Remove `word_count` from all mock entries**:
- Line 112: Remove `word_count=3,`
- Line 118: Remove `word_count=3,`
- Line 174: Remove `word_count=6,`
- Line 352: Remove `word_count=4,`

**Update existing tests**:
- Remove assertions checking for "words" in output
- Update to check for duration display instead

**Add new editor tests**:
```python
@pytest.mark.asyncio
async def test_interactive_editor_returns_text():
    """Test editor returns text when Ctrl+D pressed."""
    with patch('companion.cli._run_interactive_editor') as mock_editor:
        mock_editor.return_value = ("Test content", 45)

        # Test logic
        content, duration = await _run_interactive_editor(
            prompter=MagicMock(),
            recent_entries=[],
            idle_threshold=15
        )

        assert content == "Test content"
        assert duration == 45

@pytest.mark.asyncio
async def test_interactive_editor_returns_none_on_cancel():
    """Test editor returns None when Ctrl+C pressed."""
    with patch('companion.cli._run_interactive_editor') as mock_editor:
        mock_editor.return_value = (None, 0)

        content, duration = await _run_interactive_editor(
            prompter=MagicMock(),
            recent_entries=[],
            idle_threshold=15
        )

        assert content is None
        assert duration == 0

def test_write_command_uses_config_threshold(runner, mock_config, mock_journal):
    """Test write command reads idle_threshold from config."""
    mock_config.editor_idle_threshold = 20

    with patch('companion.cli._run_interactive_editor') as mock_editor:
        mock_editor.return_value = ("Test", 30)

        result = runner.invoke(write)

        # Verify editor called with threshold from config
        mock_editor.assert_called_once()
        args, kwargs = mock_editor.call_args
        assert kwargs['idle_threshold'] == 20 or args[2] == 20

def test_write_command_saves_with_duration(runner, mock_config, mock_journal):
    """Test write command saves entry with tracked duration."""
    with patch('companion.cli._run_interactive_editor') as mock_editor:
        mock_editor.return_value = ("Content", 67)

        result = runner.invoke(write)

        # Verify save_entry called
        mock_journal.save_entry.assert_called_once()
        saved_entry = mock_journal.save_entry.call_args[0][0]
        assert saved_entry.duration_seconds == 67
        assert "67" not in result.output  # No word count shown

def test_list_entries_no_word_count(runner, mock_config, mock_journal):
    """Test list command doesn't show word count."""
    mock_journal.list_entries.return_value = [
        JournalEntry(content="Test", duration_seconds=120)
    ]

    result = runner.invoke(list_entries)

    assert "words" not in result.output.lower()
    assert "Word count" not in result.output
```

**Test strategy**:
```bash
pytest tests/test_cli.py -v
pytest tests/ -v  # Full suite
```

**Dependencies**: Chunk 3 complete (cli.py implementation)

**Commit point**: After `pytest tests/test_cli.py` passes

**Commit message**:
```
test: update tests for interactive editor

- Remove word_count from mock entries
- Add tests for editor save/cancel behavior
- Add tests for config idle_threshold
- Add tests for duration tracking
- Verify no word count in command outputs
```

---

## New Files to Create

**None** - All changes are modifications to existing files.

This aligns with ruthless simplicity - no new modules for a feature that can be implemented inline.

---

## Files to Delete

**None** - No files are being removed.

---

## Agent Orchestration Strategy

### Primary Agent: modular-builder

For all implementation chunks:

```
Task modular-builder: "Implement Chunk [N] according to spec in
code_plan.md:

- Files: [list]
- Changes: [specific modifications]
- Tests: [verification strategy]

Ensure all changes align with IMPLEMENTATION_PHILOSOPHY.md
(ruthless simplicity, no over-engineering)."
```

### Sequential Implementation

**Must be sequential** (dependencies between chunks):

```
Chunk 1 (Remove word_count)
    “
Chunk 2 (Add config field)
    “
Chunk 3 (Implement editor)
    “
Chunk 4 (Update tests)
```

**Why sequential**:
- Chunk 2 depends on Chunk 1 (models.py changes)
- Chunk 3 depends on Chunk 2 (config field must exist)
- Chunk 4 depends on Chunk 3 (tests verify implementation)

---

## Testing Strategy

### Unit Tests to Add/Modify

**File: tests/test_models.py**
- Remove: `test_word_count_calculation()` test
- Modify: Remove word_count assertion from existing tests
- Add: `test_journal_entry_no_word_count()` - Verify field removed
- Add: `test_journal_entry_duration_preserved()` - Verify duration field works

**File: tests/test_cli.py**
- Modify: Remove word_count from all mock JournalEntry creation
- Modify: Remove word count output assertions
- Add: `test_interactive_editor_returns_text()` - Editor save behavior
- Add: `test_interactive_editor_returns_none_on_cancel()` - Cancel behavior
- Add: `test_write_command_uses_config_threshold()` - Config integration
- Add: `test_write_command_saves_with_duration()` - Duration tracking
- Add: `test_list_entries_no_word_count()` - Verify removal from output

### Integration Tests

**Manual end-to-end testing** (required after Chunk 3):

```bash
# Test 1: Blank slate start
python -m companion.cli write
# Expected: Empty text area, no prompt shown initially

# Test 2: Idle prompt appears
python -m companion.cli write
# Type "Today I", pause 15+ seconds
# Expected: Gray italicized prompt appears

# Test 3: Placeholder clears
# After seeing placeholder, type one character
# Expected: Placeholder disappears immediately

# Test 4: Save with Ctrl+D
python -m companion.cli write
# Type content, press Ctrl+D
# Expected: "Entry saved (X min)" - no word count

# Test 5: Cancel with Ctrl+C
python -m companion.cli write
# Type content, press Ctrl+C
# Expected: "Entry cancelled"

# Test 6: Duration tracking
python -m companion.cli write
# Write for exactly 60 seconds, save
python -m companion.cli show <entry-id>
# Expected: "Duration: 1 minute" in output

# Test 7: List shows no word count
python -m companion.cli list
# Expected: No "(X words)" in entry list

# Test 8: Config idle threshold works
# Edit ~/.companion/config.json, set editor_idle_threshold to 5
python -m companion.cli write
# Pause 5 seconds
# Expected: Prompt appears at 5s, not 15s
```

### User Testing Plan

**Commands to run**:
```bash
# Verify full workflow
source .venv/bin/activate
python -m companion.cli write

# Verify tests pass
pytest tests/ -v

# Verify no regressions
pytest tests/ --cov=companion --cov-report=html
```

**Expected behavior**:
- All 413+ tests pass
- Coverage remains e75%
- Manual testing scenarios all pass
- No word count anywhere in UI
- Duration tracking works

---

## Philosophy Compliance

### Ruthless Simplicity

 **What we're doing**:
- Using existing `prompt_toolkit` dependency (already in pyproject.toml)
- Inline implementation (~100 lines in cli.py)
- Reusing existing `prompter.get_placeholder_text()` interface
- Simple idle timer (time since last keystroke)

 **What we're NOT doing (YAGNI)**:
- Not creating new modules/packages
- Not building custom terminal I/O layer
- Not adding syntax highlighting, themes, or rich text
- Not implementing undo/redo or complex editing features
- Not building editor toolbar or status bar
- Not adding configuration UI

 **Where we're removing complexity**:
- Removing word_count field and all related code (~50 lines removed)
- Simplifying write command (removing upfront prompt display)
- Cleaner UI (less clutter in command outputs)

### Modular Design

 **Clear module boundaries**:
- **Editor logic**: Encapsulated in `_run_interactive_editor()` function
- **Configuration**: Clean interface via `Config.editor_idle_threshold`
- **Prompt generation**: Existing `prompter.get_placeholder_text()` reused
- **Storage**: Unchanged (JournalEntry model simplified)

 **Well-defined interfaces (studs)**:
```python
# Editor interface
async def _run_interactive_editor(...) -> tuple[str | None, int]

# Config interface
config.editor_idle_threshold: int

# Prompter interface (unchanged)
async def get_placeholder_text(...) -> str
```

 **Self-contained components (bricks)**:
- Editor function is self-contained (~100 lines)
- Could be extracted to module later if needed (but YAGNI now)
- Could be regenerated from this spec

---

## Commit Strategy

### Commit 1: Remove word_count

```
refactor: remove word_count field from JournalEntry

- Remove word_count field from models.JournalEntry
- Remove auto-calculation in __init__
- Remove word count statistics from summarizer
- Remove word_count tests from test_models.py
- Duration tracking is sufficient for session analytics

> Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

**Files changed**: companion/models.py, companion/summarizer.py, tests/test_models.py

---

### Commit 2: Add configuration

```
feat: add configurable idle threshold for editor

- Add editor_idle_threshold field to Config (default: 15)
- Users can customize when prompts appear via config
- Documented in USER_GUIDE.md

> Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

**Files changed**: companion/models.py

---

### Commit 3: Implement editor

```
feat: interactive editor with idle-time prompts

- Implement prompt_toolkit-based interactive editor
- Blank slate start (no upfront prompts)
- Idle detection with configurable threshold (default 15s)
- Gray italicized placeholder prompts from AI
- Ctrl+D to save, Ctrl+C to cancel
- Track actual writing duration
- Remove word count display from all commands
- Nano-like terminal editing experience

Technical details:
- Add _run_interactive_editor() async function (~100 lines)
- Background task monitors idle time
- Calls prompter.get_placeholder_text() when idle
- Placeholder styled as gray italic (#888888)
- Duration tracking via time.time()

> Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

**Files changed**: companion/cli.py

---

### Commit 4: Update tests

```
test: update tests for interactive editor

- Remove word_count from mock JournalEntry creation
- Add tests for editor save/cancel behavior
- Add tests for config idle_threshold usage
- Add tests for duration tracking
- Verify no word count in command outputs
- All 413+ tests passing

> Generated with [Amplifier](https://github.com/microsoft/amplifier)

Co-Authored-By: Amplifier <240397093+microsoft-amplifier@users.noreply.github.com>
```

**Files changed**: tests/test_cli.py

---

## Risk Assessment

### High Risk Changes

**Risk 1: prompt_toolkit import availability**
- **Impact**: If library missing, import fails
- **Mitigation**: Library already in pyproject.toml, tested in Phase 1
- **Fallback**: N/A - dependency verified

**Risk 2: Async/await complexity**
- **Impact**: Race conditions in idle detection
- **Mitigation**: Simple pattern (single background task), asyncio.create_task() is reliable
- **Testing**: Manual testing will catch issues

**Risk 3: Breaking existing tests**
- **Impact**: Removing word_count breaks 413 tests
- **Mitigation**: Sequential chunks - fix tests immediately after breaking changes
- **Recovery**: Can revert commits if tests fail

### Dependencies to Watch

**prompt_toolkit >= 3.0.0**:
- Already in pyproject.toml (verified in Phase 1)
- Stable, mature library
- No version constraint issues

**Python 3.11+**:
- Project already requires this
- No compatibility concerns

### Breaking Changes

**For Users**:
- L **None** - UX improved (better editor)
- L **None** - Configuration backwards compatible (new optional field)
- L **None** - Existing entries still readable

**For Developers/Tests**:
-  **word_count field removed** - Tests creating JournalEntry must not pass word_count
-  **Mitigation**: Fix in Chunk 4 (test updates)

---

## Success Criteria

Code is ready when:

- [ ] All documented behavior implemented (interactive editor, idle detection, placeholders)
- [ ] All tests passing (`make check` succeeds)
- [ ] All 5 user testing scenarios work as documented
- [ ] No regressions in existing functionality (413 tests still pass)
- [ ] Code follows philosophy principles (ruthless simplicity )
- [ ] No word_count references anywhere in codebase
- [ ] Duration tracking works correctly
- [ ] Configurable idle threshold works
- [ ] Ready for Phase 5 (cleanup and finalize)

---

## Implementation Complexity Estimate

**Lines changed/added**:
- companion/models.py: ~5 lines removed, ~2 lines added (net: -3)
- companion/summarizer.py: ~2 lines removed
- companion/cli.py: ~120 lines added, ~40 lines modified, ~10 lines removed (net: +70)
- tests/test_models.py: ~10 lines modified/added
- tests/test_cli.py: ~80 lines added, ~10 lines modified (net: +90)

**Total**: ~157 net new lines across 5 files

**Complexity**: Low-Medium
- Most complex part: prompt_toolkit editor (~100 lines)
- Rest is cleanup and configuration
- Well-defined requirements
- Clear test strategy

**Estimated time**: 2-3 hours total across all chunks

---

## Next Steps

 **Phase 3 Complete: Code Plan Detailed and Ready**

Implementation plan written to: `ai_working/ddd/code_plan.md`

**Summary**:
- **Files to change**: 5 (models, summarizer, cli, 2 test files)
- **Implementation chunks**: 4 sequential chunks
- **New tests**: 6+ test functions
- **Estimated commits**: 4 focused commits
- **Net lines added**: ~157 lines

**  USER APPROVAL REQUIRED**

Please review the code plan above.

**When approved, proceed to implementation**:
```bash
/ddd:4-code
```

Phase 4 will implement the plan incrementally with testing after each chunk.

---

## Technical Notes

### prompt_toolkit Reference

**Key classes used**:
- `Application` - Main event loop coordinator
- `TextArea` - Multi-line editable text widget
- `KeyBindings` - Keyboard shortcut registry
- `Layout` - Component arrangement
- `Style` - Visual styling (gray italic placeholder)
- `FormattedText` - Styled text rendering

**Async integration**:
- `app.run_async()` - Returns awaitable future
- Compatible with `asyncio.run()` wrapper
- Background tasks via `asyncio.create_task()`

### Idle Detection Algorithm

```python
# Pseudocode
last_activity = current_time()

while editor_running:
    wait 1 second
    idle_duration = current_time() - last_activity

    if idle_duration >= threshold:
        placeholder = await get_ai_prompt(...)
        show_placeholder(placeholder)

    # On any keystroke:
    last_activity = current_time()
    clear_placeholder()
```

**Simple and reliable** - no complex state machine needed.

---

## Appendix: Current Code Locations

**Models**:
- JournalEntry class: companion/models.py:42-73
- Config class: companion/models.py:120-143

**Write command**:
- Current implementation: companion/cli.py:137-223
- Input loop to replace: companion/cli.py:160-174
- Word count usage: companion/cli.py:113, 181, 184, 192, 299

**Summarizer**:
- Word count statistics: companion/summarizer.py:133-134

**Tests**:
- Model tests: tests/test_models.py:87, 89-92
- CLI tests word_count: tests/test_cli.py:112, 118, 174, 352
