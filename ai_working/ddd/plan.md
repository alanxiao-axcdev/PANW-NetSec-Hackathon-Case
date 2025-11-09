# DDD Plan: Visual Emotional Trends Dashboard

## Problem Statement

### Current State
The application provides text-based summaries of emotional patterns, but lacks visual representation of trends over time. Users have sentiment and theme data from all journal entries, but can't easily see:
- How their emotional state is trending (getting better/worse)
- Which themes appear most frequently in their journaling
- Overall emotional distribution across a time period

**Text summaries exist** (`companion summary`) but visual patterns are processed faster by humans.

### User Value
- **See emotional journey at a glance** - Visualization reveals patterns text can't
- **Identify recurring themes quickly** - Bar chart shows what you write about most
- **Track emotional progress** - Delta shows if trending more positive
- **Motivation through visibility** - Seeing progress encourages continued journaling
- **Actionable insights** - Visual patterns suggest life adjustments

### What Problem This Solves
**Hidden patterns in emotional data** - Users can't easily answer:
- "Am I getting happier over time?"
- "What do I write about most?"
- "Is my emotional state improving?"

Visual dashboard makes these insights immediate and actionable.

---

## Proposed Solution

### High-Level Approach
Create a dedicated `companion/trends.py` module that:

1. **Aggregates existing data** - No new analysis, uses sentiment/themes already in entries
2. **Calculates key metrics**:
   - Emotional delta (trending more positive/negative)
   - Theme frequencies (top 10 most common)
   - Sentiment distribution (% positive/neutral/negative)
3. **Renders compact dashboard** - Fits in single terminal screen using Rich
4. **Supports date ranges** - week/month/all with custom start/end dates

**CLI Command**: `companion trends [--period week|month|all] [--start DATE] [--end DATE]`

### Key Design Principles
- **New dedicated module**: `companion/trends.py` (~100-150 lines)
- **Reuse existing data**: No re-analysis, uses stored sentiment/themes
- **Terminal-based**: Rich library (Table, Panel, text-based bars)
- **Privacy maintained**: All processing on-device
- **Fast**: < 1 second for typical data (100 entries)
- **Compact**: Single-screen output

---

## Alternatives Considered

### Alternative 1: Inline in CLI
**Approach**: Add trends logic directly in `cli.py`

**Pros**:
- Zero new files
- Very fast to implement

**Cons**:
- cli.py already 400+ lines
- Hard to test without running CLI
- Violates single responsibility
- Grows messily with new features

**Verdict**: L Rejected - violates modular design principles

### Alternative 2: Extend monitoring/dashboard.py
**Approach**: Add emotional trends to existing dashboard module

**Pros**:
- Reuses dashboard module
- All dashboards in one place

**Cons**:
- Mixes system monitoring with journal analytics (different concerns)
- "monitoring" namespace implies infrastructure, not content
- Conceptual confusion

**Verdict**: L Rejected - separation of concerns violation

### Alternative 3: Dedicated Trends Module P CHOSEN
**Approach**: Create `companion/trends.py` with clear separation

**Pros**:
- Clear module boundary
- Easy to test
- Regeneratable
- Grows cleanly
- Follows existing patterns

**Cons**:
- One new file

**Verdict**:  Selected - aligns with modular design and ruthless simplicity

---

## Architecture & Design

### Key Interfaces

#### 1. Main Entry Point
```python
def show_trends(
    period: str = "week",
    start_date: date | None = None,
    end_date: date | None = None
) -> None:
    """
    Display emotional trends dashboard.

    Args:
        period: Time period (week/month/all)
        start_date: Custom start date (overrides period)
        end_date: Custom end date (overrides period)

    Side Effects:
        Prints Rich-formatted dashboard to terminal
    """
```

#### 2. CLI Integration
```python
# In companion/cli.py
@main.command()
@click.option('--period', type=click.Choice(['week', 'month', 'all']), default='week')
@click.option('--start', type=str, help='Start date (YYYY-MM-DD)')
@click.option('--end', type=str, help='End date (YYYY-MM-DD)')
def trends(period: str, start: str | None, end: str | None) -> None:
    """Show visual emotional trends and patterns."""
    from companion.trends import show_trends

    # Parse dates if provided
    start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else None
    end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else None

    show_trends(period=period, start_date=start_date, end_date=end_date)
```

### Module Boundaries

**New Module**: `companion/trends.py`
- **Purpose**: Aggregate and visualize emotional trends
- **Dependencies**: journal, models, Rich
- **No dependencies on**: analyzer, summarizer (uses their output, doesn't call them)

**Functions**:
```python
# Public interface
def show_trends(period, start_date, end_date) -> None

# Private helpers
def _get_date_range(period, start, end) -> tuple[date, date]
def _filter_entries_by_range(entries, start, end) -> list[JournalEntry]
def _calculate_emotional_delta(entries) -> dict
def _count_theme_frequencies(entries) -> Counter
def _calculate_sentiment_distribution(entries) -> dict
def _render_dashboard(delta, themes, distribution, date_range) -> None
```

### Data Models

**No new models needed** - uses existing:
- `JournalEntry` (has sentiment, themes, timestamp)
- `Sentiment` (has label, confidence)

**Aggregated data structures** (internal to module):
```python
EmotionalDelta = {
    "trend": "improving" | "declining" | "stable",
    "change": float,  # e.g., +0.15 (15% more positive)
    "start_avg": float,
    "end_avg": float
}

ThemeFrequencies = Counter({
    "work": 12,
    "health": 8,
    "relationships": 5,
    ...
})

SentimentDistribution = {
    "positive": 0.6,  # 60%
    "neutral": 0.3,   # 30%
    "negative": 0.1   # 10%
}
```

---

## Files to Change

### Non-Code Files (Phase 2)

- [ ] `README.md` - Add `companion trends` command to quick reference
- [ ] `docs/USER_GUIDE.md` - Document trends visualization feature
- [ ] `docs/DESIGN.md` - Add trends.py module to architecture

### Code Files (Phase 4)

- [ ] `companion/trends.py` - NEW: Create trends visualization module (~120 lines)
- [ ] `companion/cli.py` - Add `trends` command (~15 lines)
- [ ] `tests/test_trends.py` - NEW: Create test module (~80 lines)

---

## Philosophy Alignment

### Ruthless Simplicity

 **Start minimal**:
- Single module, single purpose
- ~120 lines total
- Uses existing data (no new analysis)
- Simple aggregation (Counter, averages)

 **Avoid future-proofing**:
- NOT building: Interactive charts, export to image, web dashboard
- NOT building: Advanced statistics, correlations, predictions
- NOT building: Custom date ranges beyond what's needed
- Building ONLY: Compact visual dashboard with essential metrics

 **Clear over clever**:
- Simple aggregation logic (count, average, percentages)
- Text-based bars (not complex charting libraries)
- Direct Rich usage (no abstractions)

### Modular Design

 **Brick (module)**:
- `companion/trends.py` - Self-contained visualization module
- Clear single responsibility: aggregate ’ visualize

 **Studs (interfaces)**:
```python
# Input interface
show_trends(period: str, start_date: date | None, end_date: date | None)

# Uses existing interfaces
journal.get_entries_by_date_range(start, end) -> list[JournalEntry]
journal.get_recent_entries(limit) -> list[JournalEntry]
```

 **Regeneratable**:
- Could rebuild entire trends.py from this spec
- Clear boundaries with other modules
- No hidden state or complex dependencies

---

## Test Strategy

### Unit Tests

**File**: `tests/test_trends.py`

```python
def test_calculate_emotional_delta_improving():
    """Test delta calculation for improving trend."""
    # Create entries with sentiment improving over time
    # Verify delta shows "improving" with correct change value

def test_count_theme_frequencies():
    """Test theme counting across entries."""
    # Create entries with various themes
    # Verify Counter has correct counts

def test_calculate_sentiment_distribution():
    """Test percentage calculation."""
    # Create entries: 6 positive, 3 neutral, 1 negative
    # Verify distribution: 60% pos, 30% neutral, 10% neg

def test_get_date_range_week():
    """Test week period calculation."""
    # Verify returns last 7 days

def test_filter_entries_by_range():
    """Test date filtering."""
    # Create entries across different dates
    # Verify filtering works correctly

def test_show_trends_with_no_entries():
    """Test graceful handling of empty data."""
    # Verify clear message, no crash
```

### Integration Tests

```python
def test_trends_command_week(runner, mock_journal):
    """Test trends command with week period."""
    # Mock journal entries
    # Run trends command
    # Verify output contains expected elements

def test_trends_command_custom_dates(runner, mock_journal):
    """Test trends with custom date range."""
    # Run with --start and --end
    # Verify correct filtering
```

### User Testing

**Manual test scenarios**:
```bash
# Scenario 1: Week view
companion trends

# Scenario 2: Month view
companion trends --period month

# Scenario 3: All entries
companion trends --period all

# Scenario 4: Custom range
companion trends --start 2025-01-01 --end 2025-01-31

# Scenario 5: No entries
# (with empty journal)
companion trends
```

---

## Implementation Approach

### Phase 2 (Docs)

**Order**:
1. `docs/USER_GUIDE.md` - Document trends command with examples
2. `README.md` - Add to command reference
3. `docs/DESIGN.md` - Add trends.py to module organization

**What to document**:
- How to use trends command
- What each visualization shows
- Date range options
- Example outputs

### Phase 4 (Code)

**Chunk 1: Create trends module** (core logic)
1. Create `companion/trends.py`
2. Implement aggregation functions:
   - `_calculate_emotional_delta()`
   - `_count_theme_frequencies()`
   - `_calculate_sentiment_distribution()`
3. Implement `_get_date_range()` helper
4. Test aggregation functions

**Chunk 2: Implement visualization** (Rich rendering)
1. Implement `_render_dashboard()` in trends.py
2. Use Rich Table, Panel, text-based bars
3. Color coding (green=positive, yellow=neutral, red=negative)
4. Compact single-screen layout
5. Manual visual verification

**Chunk 3: CLI integration**
1. Add `trends` command to `companion/cli.py`
2. Wire up date parsing
3. Call `trends.show_trends()`
4. End-to-end testing

**Chunk 4: Add tests**
1. Create `tests/test_trends.py`
2. Unit tests for aggregation
3. Integration tests for command
4. Edge case testing

---

## Success Criteria

### Functional Requirements
- [ ] `companion trends` command works
- [ ] Shows emotional delta (improving/declining/stable) with percentage change
- [ ] Shows top 10 themes with frequency bars
- [ ] Shows sentiment distribution percentages
- [ ] Supports --period week/month/all
- [ ] Supports custom --start and --end dates
- [ ] Fits in single terminal screen (compact output)
- [ ] Renders in < 1 second for typical data

### Non-Functional Requirements
- [ ] Module is < 150 lines
- [ ] No new dependencies (uses existing Rich)
- [ ] All aggregation tested
- [ ] Privacy maintained (on-device only)
- [ ] Graceful handling of empty data

### Quality Gates
- [ ] All tests passing (414+ tests)
- [ ] Coverage maintained (>74%)
- [ ] Manual visual verification successful
- [ ] Documentation complete

---

## Detailed Dashboard Layout

### Compact Single-Screen Design

```
Emotional Trends (Jan 1-7, 2025)


Emotional Journey
  Start of period:  0.45 (Neutral-leaning)
  End of period:    0.72 (Positive)

  Trend: — Improving (+27%)

Top Themes
  work          ˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆˆ‘‘ (12 entries)
  health        ˆˆˆˆˆˆˆˆˆˆˆˆ‘‘‘‘‘‘ (9 entries)
  relationships ˆˆˆˆˆˆˆˆ‘‘‘‘‘‘‘‘‘‘ (6 entries)
  stress        ˆˆˆˆˆˆ‘‘‘‘‘‘‘‘‘‘‘‘ (4 entries)
  creativity    ˆˆˆˆ‘‘‘‘‘‘‘‘‘‘‘‘‘‘ (3 entries)

Emotional Distribution
  Positive  60% ˆˆˆˆˆˆˆˆˆˆˆˆ
  Neutral   30% ˆˆˆˆˆˆ
  Negative  10% ˆˆ

7 entries analyzed
```

**Key elements**:
1. **Date range** in header
2. **Emotional delta** - Start/end averages + trend direction + percentage
3. **Theme frequencies** - Top 10 with text-based bars
4. **Sentiment distribution** - Percentages with bars
5. **Entry count** at bottom

**Visual Design**:
- Green for positive/improving
- Yellow for neutral/stable
- Red for negative/declining
- Gray for bars
- Compact spacing (no wasted lines)

---

## Next Steps

 **Phase 1 Complete: Planning Approved**

Plan written to: `ai_working/ddd/plan.md`

**Next Phase: Update all non-code files (docs, configs, READMEs)**

Run: `/ddd:2-docs`

The plan will guide all subsequent phases. All commands can now run without arguments using this plan as their guide.
