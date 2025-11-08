# DDD Plan: Interactive Journal Editor with Idle-Time Contextual Prompts

## Problem Statement

### Current State
The journal's `write` command currently uses a basic Python `input()` loop (lines 160-165 in `companion/cli.py`). This approach has several UX issues:

1. **Intimidating blank slate**: Users face a prompt BEFORE they start writing, which can create pressure
2. **No help during writing**: When users get stuck mid-entry, there's no contextual assistance
3. **Dated UX**: Simple line-by-line input feels antiquated compared to modern terminal editors
4. **No writing analytics**: Doesn't track how long users spend writing (despite model supporting it)
5. **Unnecessary metrics**: Shows word count prominently when it's not core to journaling experience

### User Value
- **Reduces friction**: Start with a blank slate, get help only when needed
- **Natural flow**: Assistance appears when you pause, disappears when you type
- **Professional UX**: Nano-like editing experience (Ctrl+D save, Ctrl+C cancel)
- **Unintrusive**: Prompts are subtle (gray, italicized) and context-aware
- **Privacy-aware**: Writing duration tracked for personal insights, word counts removed

### What Problem This Solves
**Writer's block during journaling** - Users know they want to journal but get stuck:
- After starting (mid-thought paralysis)
- When processing emotions (need reflection prompts)
- During long pauses (need gentle nudges)

Traditional approach: Show prompt upfront (adds pressure)
Our approach: Wait for user to signal they need help (through idle time)

---

## Proposed Solution

### High-Level Approach
Replace the basic `input()` loop with a `prompt_toolkit`-based interactive editor that:

1. **Starts blank**: No initial prompt, just cursor in empty text area
2. **Detects idle time**: Background task monitors typing activity
3. **Shows contextual prompts**: After configurable idle time (default 15s), display gray italicized placeholder text
4. **Leverages existing AI**: Uses `prompter.get_placeholder_text()` (already implemented)
5. **Tracks duration**: Records time spent writing (use existing `duration_seconds` field)
6. **Removes clutter**: Eliminates word count display and auto-calculation
7. **Configurable**: Allow users to customize idle threshold via config

### Key Design Principles
- **Inline implementation**: Add `_run_interactive_editor()` function directly in `cli.py` (~100 lines)
- **No new modules**: Keep it simple, don't over-modularize
- **Reuse existing infrastructure**: Prompter, storage, models unchanged
- **Minimal dependencies**: `prompt_toolkit>=3.0.0` already in `pyproject.toml`

---

## Alternatives Considered

### Alternative 1: Rich Manual Implementation
**Approach**: Build custom editor using Rich Console + manual character capture

**Pros**:
- Stays within Rich ecosystem
- Complete control over details

**Cons**:
- 300-500 lines of complex code (reinventing prompt_toolkit)
- Edge cases: cursor movement, backspace, terminal compatibility
- High maintenance burden
- Violates "ruthless simplicity" principle

**Verdict**: ❌ Rejected - violates YAGNI and ruthless simplicity

### Alternative 2: Textual Framework
**Approach**: Use Textual (Rich's TUI framework) with TextArea widget

**Pros**:
- Modern, beautiful defaults
- Great async/reactive model

**Cons**:
- Overkill - full framework for single input field
- New dependency (not currently in project)
- More abstraction than needed
- Heavier than necessary

**Verdict**: ❌ Rejected - over-engineering for simple problem

### Alternative 3: prompt_toolkit Integration ⭐ CHOSEN
**Approach**: Use prompt_toolkit's Application/TextArea for rich editing

**Pros**:
- Already a dependency (no new packages)
- Handles terminal complexity (cursor, rendering, colors)
- Native async support for idle detection
- Battle-tested library
- ~100 lines of code

**Cons**:
- Small learning curve for prompt_toolkit patterns

**Verdict**: ✅ **Selected** - simple, direct, trusts in libraries

---

## Architecture & Design

### Key Interfaces

#### 1. Editor Session Interface
```python
async def _run_interactive_editor(
    prompter: Prompter,
    recent_entries: list[JournalEntry],
    idle_threshold: int = 15  # NEW: configurable threshold
) -> tuple[str | None, int]:
    """
    Run interactive editor session.

    Args:
        prompter: AI prompt generator
        recent_entries: Context for prompt generation
        idle_threshold: Seconds of idle before showing prompt (default 15)

    Returns:
        Tuple of (final_text, duration_seconds) or (None, 0) if cancelled
    """
```

#### 2. Configuration Interface
Add to `companion/config.py`:
```python
class CompanionConfig(BaseModel):
    # ... existing fields ...
    editor_idle_threshold: int = 15  # NEW: configurable idle time
```

#### 3. Prompter Interface (Already Exists)
```python
async def get_placeholder_text(
    current_text: str,
    idle_duration: float,
    recent_entries: list[JournalEntry]
) -> str:
    """Generate intelligent placeholder based on context and idle time."""
```

### Module Boundaries

**No new modules created** - this is an inline implementation.

**Module**: `companion/cli.py`
- **New function**: `_run_interactive_editor()` - Main editor session (~100 lines)
- **Modified function**: `write()` command - Replace input loop with editor call
- **Removed**: Word count display and calculations

**Module**: `companion/config.py`
- **New field**: `editor_idle_threshold` - Configurable idle time

**Module**: `companion/models.py`
- **Modified**: Remove `word_count` field and auto-calculation
- **Modified**: Ensure `duration_seconds` properly populated

**Module**: `companion/prompter.py`
- **Unchanged**: Already has `get_placeholder_text()` interface

### Data Models

#### Modified: JournalEntry
```python
class JournalEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    content: str
    prompt_used: str | None = None
    sentiment: Sentiment | None = None
    themes: list[str] = Field(default_factory=list)
    # REMOVED: word_count field
    duration_seconds: int = 0  # NOW POPULATED: actual writing time
    next_session_prompts: list[str] = Field(default_factory=list)
    analysis_complete: bool = False
```

#### Modified: CompanionConfig
```python
class CompanionConfig(BaseModel):
    # ... existing fields ...
    editor_idle_threshold: int = 15  # NEW: seconds before showing prompt
```

---

## Files to Change

### Non-Code Files (Phase 2)

- [ ] `README.md` - Document new interactive editor UX
  - Add section on idle-time prompts
  - Explain Ctrl+D / Ctrl+C keyboard shortcuts
  - Mention configurable idle threshold

- [ ] `docs/USER_GUIDE.md` - Comprehensive editor documentation
  - How to use the interactive editor
  - Understanding idle-time prompts
  - Customizing idle threshold in config
  - Writing session analytics (duration tracking)

- [ ] `docs/DESIGN.md` - Update architecture documentation
  - Remove word_count references
  - Add editor session flow diagram
  - Document idle detection mechanism

- [ ] `ai_working/ddd/plan.md` - This planning document
  - Mark as complete when approved

### Code Files (Phase 4)

- [ ] `companion/cli.py` - Main editor implementation
  - **Add**: `_run_interactive_editor()` function (~100 lines)
  - **Modify**: `write()` command - replace input loop (lines 160-165)
  - **Remove**: Word count display (lines 113, 192, 299)
  - **Remove**: Word count calculation (line 181, 184)

- [ ] `companion/config.py` - Add configuration setting
  - **Add**: `editor_idle_threshold: int = 15` to CompanionConfig

- [ ] `companion/models.py` - Remove word_count
  - **Remove**: `word_count: int = 0` field (line 64)
  - **Remove**: `word_count` docstring (line 52)
  - **Remove**: Auto-calculation in `__init__` (lines 72-73)
  - **Modify**: Ensure `duration_seconds` is properly used

- [ ] `tests/test_cli.py` - Update tests
  - **Modify**: `test_write_entry_basic` - mock editor, no word_count
  - **Modify**: `test_write_entry_empty` - adapt to new editor
  - **Add**: `test_interactive_editor_save` - Ctrl+D behavior
  - **Add**: `test_interactive_editor_cancel` - Ctrl+C behavior
  - **Add**: `test_idle_threshold_respected` - placeholder timing
  - **Add**: `test_duration_tracking` - verify time recorded

- [ ] `tests/test_models.py` - Remove word_count tests
  - **Remove**: Any tests validating word_count calculation

- [ ] `companion/summarizer.py` - Remove word_count references (if any)
  - **Audit**: Check for word_count usage and remove

---

## Philosophy Alignment

### Ruthless Simplicity

✅ **Start minimal**:
- Inline implementation (~100 lines), no new modules
- Use existing `prompt_toolkit` dependency
- Reuse existing `prompter.get_placeholder_text()` interface

✅ **Avoid future-proofing**:
- Not building: Rich text formatting, syntax highlighting, themes
- Not building: Multiple editor modes, split view, history
- Not building: Custom placeholder animation or complex UI

✅ **Clear over clever**:
- Simple idle timer (time since last keystroke)
- Direct async/await for background task
- Explicit key bindings (Ctrl+D, Ctrl+C)
- No complex state machines

✅ **Remove unnecessary**:
- Word count feature removed (not core to journaling value)
- Simple UX without visual clutter

### Modular Design

✅ **Bricks (modules)**:
- **Editor session**: Single function `_run_interactive_editor()` in cli.py
- **Configuration**: One new field in existing config.py
- **Models**: One removed field (word_count), one utilized field (duration_seconds)

✅ **Studs (interfaces)**:
- `_run_interactive_editor(prompter, entries, threshold) -> (text, duration)`
- `prompter.get_placeholder_text(text, idle, entries) -> str`
- `config.editor_idle_threshold` for user customization

✅ **Regeneratable**:
- Can rebuild `_run_interactive_editor()` from this spec
- Clear boundaries: editor logic separate from storage/analysis
- Could swap prompt_toolkit for another library if needed

---

## Test Strategy

### Unit Tests

#### Editor Function Tests
```python
# tests/test_cli.py

async def test_interactive_editor_returns_text():
    """Test editor returns text when user presses Ctrl+D."""
    # Mock prompt_toolkit Application
    # Simulate typing "Test content"
    # Simulate Ctrl+D
    # Assert returns ("Test content", duration > 0)

async def test_interactive_editor_returns_none_on_cancel():
    """Test editor returns None when user presses Ctrl+C."""
    # Mock prompt_toolkit Application
    # Simulate typing "Test content"
    # Simulate Ctrl+C
    # Assert returns (None, 0)

async def test_idle_threshold_respected():
    """Test placeholder appears after idle threshold."""
    # Mock prompter.get_placeholder_text()
    # Simulate 14s idle -> no placeholder
    # Simulate 16s idle -> placeholder appears
    # Assert placeholder called with correct idle_duration

async def test_placeholder_clears_on_typing():
    """Test placeholder disappears when user types."""
    # Show placeholder
    # Simulate keystroke
    # Assert placeholder cleared

async def test_duration_tracking():
    """Test writing duration accurately tracked."""
    # Start editor
    # Sleep 5 seconds
    # Save with Ctrl+D
    # Assert duration_seconds >= 5
```

#### Model Tests
```python
# tests/test_models.py

def test_journal_entry_no_word_count():
    """Test JournalEntry no longer has word_count field."""
    entry = JournalEntry(content="Test", duration_seconds=60)
    assert not hasattr(entry, "word_count")

def test_journal_entry_duration_preserved():
    """Test duration_seconds field works correctly."""
    entry = JournalEntry(content="Test", duration_seconds=120)
    assert entry.duration_seconds == 120
```

### Integration Tests

```python
# tests/test_cli.py

def test_write_command_with_editor(runner, mock_config, mock_journal):
    """Test full write command with interactive editor."""
    # Mock _run_interactive_editor to return ("Test content", 45)
    # Invoke write command
    # Assert journal.save_entry called with duration_seconds=45
    # Assert "Entry saved" in output
    # Assert NO word count in output

def test_write_command_respects_config_threshold():
    """Test editor uses config.editor_idle_threshold."""
    # Set config.editor_idle_threshold = 20
    # Mock editor
    # Verify editor called with idle_threshold=20
```

### User Testing Scenarios

#### Scenario 1: Blank Slate Start
1. Run `companion write`
2. Verify: Empty text area, no prompt shown
3. Start typing immediately
4. Verify: Can type freely without prompts

#### Scenario 2: Idle Prompt Appears
1. Run `companion write`
2. Type a few words, then pause
3. Wait 15 seconds without typing
4. Verify: Gray italicized placeholder text appears
5. Resume typing
6. Verify: Placeholder disappears immediately

#### Scenario 3: Save with Ctrl+D
1. Run `companion write`
2. Type journal entry
3. Press Ctrl+D
4. Verify: Entry saved with duration_seconds > 0
5. Verify: No word count shown in confirmation

#### Scenario 4: Cancel with Ctrl+C
1. Run `companion write`
2. Type some content
3. Press Ctrl+C
4. Verify: Entry not saved, graceful exit

#### Scenario 5: Custom Idle Threshold
1. Set `editor_idle_threshold: 10` in config
2. Run `companion write`
3. Pause for 10 seconds
4. Verify: Prompt appears at 10s (not 15s)

---

## Implementation Approach

### Phase 2 (Docs) - Update Non-Code Files

**Order:**
1. `docs/USER_GUIDE.md` - Document editor usage
2. `README.md` - Add quick reference
3. `docs/DESIGN.md` - Update architecture notes

**Strategy:**
- Explain the "why" (idle-time prompts solve writer's block)
- Provide examples of prompts user will see
- Document keyboard shortcuts clearly
- Explain configuration option

### Phase 4 (Code) - Implement Changes

**Chunk 1: Remove word_count** (foundational cleanup)
1. `companion/models.py` - Remove field and auto-calculation
2. `tests/test_models.py` - Remove word_count tests
3. `companion/cli.py` - Remove word_count display
4. `companion/summarizer.py` - Remove any word_count references
5. Run tests: `pytest tests/test_models.py tests/test_cli.py -v`

**Chunk 2: Add configuration** (prepare for editor)
1. `companion/config.py` - Add `editor_idle_threshold` field
2. Test: Verify config loads with default value

**Chunk 3: Implement editor** (core feature)
1. `companion/cli.py` - Add `_run_interactive_editor()` function
2. `companion/cli.py` - Modify `write()` command to use editor
3. Test manually: Run `companion write` and verify blank slate start
4. Test manually: Verify idle prompt appears after threshold
5. Test manually: Verify Ctrl+D saves, Ctrl+C cancels

**Chunk 4: Add tests** (validation)
1. `tests/test_cli.py` - Add all editor tests
2. Run full test suite: `pytest tests/ -v`
3. Verify 100% test pass rate

**Chunk 5: Final validation** (end-to-end)
1. Test all 5 user scenarios manually
2. Check duration tracking works
3. Verify no word counts shown
4. Confirm italic gray placeholder styling

---

## Success Criteria

### Functional Requirements
- [ ] User starts with blank text area (no upfront prompt)
- [ ] Idle detection triggers after configurable threshold (default 15s)
- [ ] Placeholder text appears in gray, italicized format
- [ ] Placeholder disappears immediately on next keystroke
- [ ] Ctrl+D saves entry with accurate duration tracking
- [ ] Ctrl+C cancels without saving
- [ ] Works in standard Unix terminals
- [ ] Configuration allows customizing idle threshold

### Non-Functional Requirements
- [ ] No word count displayed anywhere
- [ ] Word count field removed from model
- [ ] Duration tracking accurate (±1 second)
- [ ] All existing tests still pass (413 tests)
- [ ] Code remains under 100 lines for editor function
- [ ] No new module files created

### Quality Gates
- [ ] 100% test pass rate maintained
- [ ] No decrease in test coverage (<75%)
- [ ] Manual testing of all 5 user scenarios successful
- [ ] Documentation complete and accurate
- [ ] Philosophy alignment verified (ruthless simplicity ✓)

---

## Next Steps

✅ **Phase 1 Complete: Planning Approved**

Plan written to: `ai_working/ddd/plan.md`

**Next Phase: Update all non-code files (docs, configs, READMEs)**

Run: `/ddd:2-docs`

The plan will guide all subsequent phases. All commands can now run without arguments using this plan as their guide.

---

## Technical Notes

### prompt_toolkit Key Concepts

**Application**: Main event loop and coordinator
```python
from prompt_toolkit import Application
app = Application(layout=Layout(text_area), key_bindings=kb)
result = await app.run_async()
```

**TextArea**: Multi-line editable text widget
```python
from prompt_toolkit.widgets import TextArea
text_area = TextArea(
    multiline=True,
    wrap_lines=True,
    text="",  # Start empty
)
```

**KeyBindings**: Keyboard shortcut handlers
```python
from prompt_toolkit.key_binding import KeyBindings
kb = KeyBindings()

@kb.add('c-d')  # Ctrl+D
def save(event):
    event.app.exit(result=text_area.text)
```

**Styling Placeholders**:
```python
# Gray, italicized placeholder
text_area.placeholder = FormattedText([
    ('class:placeholder', placeholder_text)
])

# Style class definition
style = Style.from_dict({
    'placeholder': 'italic #888888'  # Gray + italic
})
```

### Async Idle Detection Pattern
```python
last_activity = asyncio.get_event_loop().time()

async def check_idle():
    while True:
        await asyncio.sleep(1)
        idle_duration = asyncio.get_event_loop().time() - last_activity
        if idle_duration >= threshold:
            # Show placeholder
            pass

# On keystroke
def on_text_changed(_):
    nonlocal last_activity
    last_activity = asyncio.get_event_loop().time()
```

### Duration Tracking Pattern
```python
start_time = time.time()
result = await app.run_async()
duration = int(time.time() - start_time)
```

---

## Risk Analysis

### Low Risks
- **Terminal compatibility**: prompt_toolkit handles cross-platform
- **Async complexity**: Simple background task, well-understood pattern
- **Test coverage**: Straightforward to mock prompt_toolkit

### Mitigation Strategies
- **Fallback**: If prompt_toolkit fails to import, fall back to basic `input()` loop
- **Timeout**: Add max idle time (e.g., 5 minutes) to prevent infinite wait
- **Error handling**: Graceful degradation if AI prompt generation fails

---

## Appendix: Code References

### Current Implementation (to be replaced)
**File**: `companion/cli.py`
**Lines**: 160-165
```python
lines = []
try:
    while True:
        line = input()
        lines.append(line)
except EOFError:
    pass
```

### Existing Interface (to be used)
**File**: `companion/prompter.py`
**Lines**: 171-205
```python
async def get_placeholder_text(
    current_text: str,
    idle_duration: float,
    recent_entries: list[JournalEntry],
) -> str:
    """Get placeholder text for idle state."""
```

### Model Field (to be removed)
**File**: `companion/models.py`
**Lines**: 64, 72-73
```python
word_count: int = 0

# In __init__:
if self.word_count == 0 and self.content:
    self.word_count = len(self.content.split())
```

### Model Field (to be utilized)
**File**: `companion/models.py`
**Line**: 65
```python
duration_seconds: int = 0
```
