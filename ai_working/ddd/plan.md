# DDD Plan: Fix Passphrase Timing and Enable Context-Aware Prompts

## Problem Statement

**User Value**: Users want to see intelligent journal prompts based on their previous writing themes and patterns. The app generates these prompts after analyzing each entry, but users never see them.

**Root Cause**: The write command requests the passphrase AFTER the user writes, which means:
1. Recent entries can't be decrypted during session start (no passphrase available yet)
2. Context-aware prompts stored in `entry.next_session_prompts` can't be retrieved
3. Users always see generic "What's on your mind?" instead of personalized prompts

**Impact:**
- Broken feature: AI-generated context-aware prompts never display
- Poor UX: Authentication happens at wrong time (after investment, not before)
- Wasted computation: Prompts generated but never used
- Security confusion: User writes sensitive content before knowing encryption is set up

## Proposed Solution

**Approach**: Passphrase-First Flow (Option 1)

Reorder operations in the `write` command to request passphrase at the START:

```
NEW FLOW:
1. Display greeting
2. ⭐ GET PASSPHRASE (moved here from step 7!)
   - First-time: setup_first_passphrase()
   - Returning: verify and cache
   - Handle cancellation: exit early
3. Load recent entries with passphrase
   - Can now successfully decrypt!
4. Open editor with context-aware prompts
   - Shows recent_entries[0].next_session_prompts[0]
5. User writes content
6. Validation (PII, injection)
7. Save entry with cached passphrase
8. Analysis & generate next_session_prompts
```

**Key Insight**: Simply moving the passphrase request from after writing to before writing unlocks the entire context-aware prompt feature.

## Alternatives Considered

### Option 2: Wizard-Based Setup (REJECTED)
Move passphrase setup into `_first_run_wizard()`.

**Why Rejected**:
- More complex (changes wizard + write command)
- Forces setup before exploration ("defer until needed" violation)
- Unnecessary - Option 1 solves problem with less change

### Option 3: Conditional Pre-Flight (REJECTED)
Add logic to check if entries exist, prompt early only if needed.

**Why Rejected**:
- Complex branching logic
- Still delays passphrase for first-time users
- Violates ruthless simplicity
- Doesn't improve onboarding

**Chosen Option 1** because it's the simplest solution that fully solves the problem.

## Architecture & Design

### Key Interfaces (Unchanged)

All existing module interfaces remain identical - this is pure flow reordering:

```python
# These signatures don't change:
get_passphrase(prompt_text: str = "Enter passphrase") -> str
journal.get_recent_entries(limit: int = 10, passphrase: str | None = None) -> list[JournalEntry]
_run_interactive_editor(recent_entries: list[JournalEntry], idle_threshold: int) -> tuple[str | None, int]
journal.save_entry(entry: JournalEntry, passphrase: str | None = None) -> None
```

### Module Boundaries (Preserved)

**Bricks** (self-contained modules):
- `companion/passphrase_prompt.py` - Passphrase prompting and setup
- `companion/journal.py` - Entry persistence and retrieval
- `companion/cli.py` - Command orchestration
- `companion/prompter.py` - AI prompt generation

**Studs** (connection points):
- Passphrase string flows from prompt → journal operations
- JournalEntry objects flow from journal → editor → analysis
- All interfaces stay the same

### Data Flow Changes

**BEFORE** (broken):
```
write() → editor → content → passphrase → save
        ↓ (no passphrase)
        load_entries() → empty list → no context
```

**AFTER** (fixed):
```
write() → passphrase → load_entries() → context → editor → save
                      ↓ (decrypts!)
                      recent entries with next_session_prompts
```

## Files to Change

### Non-Code Files (Phase 2)

- [ ] `README.md` - Update "How it works" section to reflect passphrase-first flow
- [ ] `docs/SECURITY.md` (if exists) - Document authentication timing

### Code Files (Phase 4)

- [ ] `companion/cli.py` - **ONLY FILE TO CHANGE**
  - Lines 251-459: `write()` command function
  - Move passphrase request from lines 361-369 to after greeting (line 260)
  - Update error handling for early passphrase cancellation
  - Adjust comments to reflect new flow

### Test Files (Phase 4)

- [ ] `tests/test_cli.py` - Update write command tests to reflect new flow order
- [ ] `tests/test_integration.py` - Verify end-to-end flow with passphrase-first

## Philosophy Alignment

### Ruthless Simplicity ✅

**Start minimal**:
- Just reorder existing operations
- Move ~20 lines from position A to position B
- No new functions, classes, or modules

**Avoid future-proofing**:
- Not adding conditional logic for "what if" scenarios
- Not building elaborate caching strategies
- Just fix the order

**Clear over clever**:
- Passphrase → Load → Write is the obvious, secure order
- Authentication gates should be early, not late

### Modular Design ✅

**Bricks (unchanged)**:
- `passphrase_prompt` module: Still handles setup and verification
- `journal` module: Still handles encryption and persistence
- `prompter` module: Still generates context-aware prompts

**Studs (unchanged)**:
- `get_passphrase()` returns string
- `get_recent_entries(passphrase)` returns list
- All function signatures preserved

**Regeneratable**:
- Could rebuild write() from this spec
- Clear before/after state
- Simple sequence of operations

### Fail Fast ✅

**OLD**: User writes for 10 minutes, then wrong passphrase = lost work
**NEW**: Wrong passphrase immediately = no time wasted

### Trust in Emergence ✅

Simple reordering unlocks sophisticated feature:
- Context-aware prompts "just work" once passphrase timing is fixed
- No need to complicate prompt generation logic
- Feature emerges from correct architecture

## Implementation Approach

### Phase 2: Documentation Updates

**README.md** changes needed:
- Update "Quick Start" to show passphrase prompt happens first
- Update "How It Works" flow diagram
- Add note about context-aware prompts from previous entries

**Estimated time**: 10 minutes (minimal docs)

### Phase 3: Code Planning

Skip - changes are simple enough to implement directly.

### Phase 4: Code Implementation

**Single file change**: `companion/cli.py`

**Specific implementation** (lines to move):

```python
# CURRENT (lines 361-369) - MOVE TO line 260:
if cfg_obj.enable_encryption:
    try:
        passphrase = get_passphrase()
    except KeyboardInterrupt:
        console.print("\nCancelled.")
        return
else:
    passphrase = None
```

**New structure** (after line 258):

```python
def write():
    """Write new journal entry."""
    _display_greeting()

    # GET PASSPHRASE FIRST (moved from later)
    cfg_obj = config.load_config()
    if cfg_obj.enable_encryption:
        try:
            passphrase = get_passphrase()
        except KeyboardInterrupt:
            console.print("\nCancelled.")
            return
    else:
        passphrase = None

    # NOW load recent entries with passphrase available
    recent_entries = []
    try:
        recent_entries = journal.get_recent_entries(limit=5, passphrase=passphrase)
    except Exception as e:
        logger.debug("Could not load recent entries: %s", e)

    # ...rest of flow unchanged
```

**Error handling additions**:
- Catch `ValueError` from get_passphrase() (max attempts exceeded)
- Display helpful message: "Too many failed attempts. Please try again later."
- Return early (don't proceed to editor)

**Testing checklist**:
- [ ] First-time user: passphrase setup works before write
- [ ] Returning user: passphrase verified, prompts display
- [ ] Wrong passphrase: fails fast with clear message
- [ ] Cancelled passphrase: exits cleanly
- [ ] Encryption disabled: works without passphrase
- [ ] Context-aware prompts: show from previous entries

**Estimated time**: 30 minutes implementation + 30 minutes testing

## Test Strategy

### Unit Tests

**New test**: `test_write_passphrase_first_order()`
- Mock get_passphrase() call
- Verify it's called BEFORE get_recent_entries()
- Use call order assertions

**Updated tests**:
- `test_write_command_basic()` - Update to expect early passphrase
- `test_write_command_cancelled()` - Test cancellation at passphrase stage

### Integration Tests

**End-to-end flow test**:
```python
def test_write_with_context_prompts():
    # Write first entry
    # Verify next_session_prompts generated
    # Write second entry
    # Verify placeholder shows first entry's generated prompt
```

### User Testing

**Manual test script**:
1. Fresh install: `rm -rf ~/.companion`
2. Run: `companion write`
3. Verify: Passphrase setup happens before editor opens
4. Write: "I'm feeling stressed about work"
5. Verify: Analysis generates themes like ["work", "stress"]
6. Exit and rerun: `companion write`
7. Verify: Passphrase requested immediately
8. Verify: Prompt shows context like "How are you managing work stress today?"

## Success Criteria

### Must Have ✅

- [ ] Passphrase requested BEFORE editor opens
- [ ] Recent entries load successfully with passphrase
- [ ] Context-aware prompts display from `next_session_prompts`
- [ ] First-time setup works smoothly
- [ ] Wrong passphrase fails fast (no wasted writing time)
- [ ] All existing tests pass
- [ ] Manual end-to-end test confirms context prompts work

### Nice to Have 🎯

- [ ] Improve passphrase error messages
- [ ] Add progress indicator for loading entries
- [ ] Document the fix in DISCOVERIES.md

### Out of Scope ❌

- Changing encryption algorithms
- Adding password recovery
- Modifying prompt generation logic
- Changing session caching strategy

## Detailed File Change Specifications

### `companion/cli.py` - write() command

**Location**: Lines 251-459

**Changes Required**:

1. **Move passphrase request** (currently lines 361-369 → new position after line 258):
   ```python
   # After _display_greeting()
   cfg_obj = config.load_config()
   passphrase = None

   if cfg_obj.enable_encryption:
       try:
           passphrase = get_passphrase()
       except KeyboardInterrupt:
           console.print("\nCancelled.")
           return
       except ValueError as e:
           # Max attempts exceeded
           console.print(f"\n[red]{e}[/red]")
           console.print("[yellow]Please try again later.[/yellow]")
           return
   ```

2. **Update entry loading** (lines 260-273 become simpler):
   ```python
   # Load recent entries for context (passphrase now available!)
   recent_entries = []
   try:
       recent_entries = journal.get_recent_entries(limit=5, passphrase=passphrase)
   except Exception as e:
       logger.debug("Could not load recent entries: %s", e)
       # Continue with empty list - graceful degradation
   ```

3. **Remove old passphrase request** (delete lines 361-369):
   - Already moved to earlier position
   - Variable `passphrase` already available from step 1

4. **Update comments**:
   - Add comment: "# Get passphrase early to enable context loading"
   - Update comment at save step: "# Save with passphrase (already cached)"

**Lines changed**: ~15 lines moved/modified
**Complexity**: Low (reordering only)
**Risk**: Low (same operations, different order)

### Test File Updates

**`tests/test_cli.py`**:

Add new test:
```python
@patch('companion.cli.get_passphrase')
@patch('companion.journal.get_recent_entries')
def test_write_passphrase_before_entries(mock_get_entries, mock_get_pass):
    """Verify passphrase requested before loading entries."""
    mock_get_pass.return_value = "test123"
    mock_get_entries.return_value = []

    # Run write command (will be intercepted)
    # Verify call order: get_passphrase() called BEFORE get_recent_entries()
    assert mock_get_pass.call_count == 1
    assert mock_get_entries.call_count == 1
    # Verify passphrase passed to get_recent_entries
    assert mock_get_entries.call_args[1]['passphrase'] == "test123"
```

Update existing test:
```python
@patch('companion.cli.get_passphrase')
def test_write_cancelled_at_passphrase(mock_get_pass):
    """Verify cancelling at passphrase prompt exits cleanly."""
    mock_get_pass.side_effect = KeyboardInterrupt()

    result = runner.invoke(cli.write)

    assert result.exit_code == 0  # Clean exit
    assert "Cancelled" in result.output
    # Verify editor never opened
```

## Risk Analysis

### Low Risk ✅
- Moving existing code (not rewriting)
- All modules unchanged
- Session caching already handles this
- Graceful fallback if entries can't load

### Potential Issues 🟡

1. **Performance**: Prompting for passphrase adds latency at start
   - **Mitigation**: Session caching minimizes this (one prompt per session)

2. **User abandonment**: User might cancel at passphrase prompt
   - **Mitigation**: This is better than losing work after writing

3. **Legacy entries**: Might have unencrypted entries
   - **Mitigation**: Already handled by journal.get_recent_entries() gracefully

### Testing Focus

- Verify passphrase prompt happens first
- Verify entries load with correct passphrase
- Verify prompts display from loaded entries
- Test all error paths (wrong password, cancellation, etc.)

## Implementation Order

### Phase 2: Documentation (First)
1. Update README.md flow diagram
2. Add comments in code explaining new flow

### Phase 4: Code (Second)
1. Modify `companion/cli.py` write() function:
   - Move passphrase request to position after greeting
   - Remove old passphrase request location
   - Update comments
2. Update tests in `tests/test_cli.py`
3. Run full test suite
4. Manual end-to-end testing

### Phase 5: Cleanup (Third)
1. Verify all tests pass
2. Run `make check`
3. Test manually with fresh install
4. Document in DISCOVERIES.md if needed

## Success Metrics

**Technical Success**:
- [ ] All tests pass
- [ ] `make check` passes
- [ ] No new lint errors

**Functional Success**:
- [ ] Context-aware prompts display on second+ session
- [ ] Passphrase requested before writing
- [ ] Wrong passphrase fails fast
- [ ] Cancellation at passphrase exits cleanly

**User Experience Success**:
- [ ] Clear security model (encrypt from start)
- [ ] Intelligent prompts from previous themes
- [ ] Smooth onboarding flow

## Next Steps

✅ **Phase 1 Complete**: Planning approved

➡️ **Ready for** `/ddd:2-docs` - Update non-code files (README, comments)

**Estimated Total Time**:
- Phase 2 (Docs): 15 minutes
- Phase 4 (Code): 60 minutes
- Phase 5 (Testing): 30 minutes
- **Total**: ~2 hours

**Complexity**: Low
**Risk**: Low
**Impact**: High (unlocks broken feature)
