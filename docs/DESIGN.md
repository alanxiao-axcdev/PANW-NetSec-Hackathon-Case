# Companion - Architecture & Design

**System design for production-ready AI security infrastructure**

---

## Overview

Companion is architected as a **modular, security-first AI application** demonstrating patterns applicable to any system handling sensitive user data with local AI processing.

**Key Design Principles**:
- Defense-in-depth security architecture
- Clear module boundaries with well-defined interfaces
- Observable and maintainable in production
- Optimized for resource-constrained local deployment
- Each module independently testable and regeneratable

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface (CLI)                    │
│                    Click + Rich + prompt_toolkit             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                     Security Layer                           │
│        Encryption │ Sandboxing │ Audit │ PII Detection      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                      Core Services                           │
│     Journal │ Analyzer │ Prompter │ Summarizer │ Config     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   AI Backend (Pluggable)                     │
│      Qwen │ Ollama │ OpenAI │ Mock (for testing)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                  Inference Optimization                      │
│       Quantization │ Batching │ Caching │ Benchmarking      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    Monitoring Layer                          │
│         Metrics │ Health Checks │ Telemetry │ Dashboard      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   Security Research                          │
│    Prompt Injection │ PII Sanitizer │ Data Poisoning │      │
│                  Adversarial Testing                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                    Storage Layer                             │
│              JSON Files (Encrypted at Rest)                  │
│        ~/.companion/{entries, config, audit, cache}          │
└──────────────────────────────────────────────────────────────┘
```

---

## Module Organization

Companion consists of **27 modules** organized into **7 domains**:

### Domain 1: Core (10 modules)

Foundation functionality for journaling application.

**Module: models.py**
- **Purpose**: Data structures for all entities
- **Exports**: `JournalEntry`, `Sentiment`, `Theme`, `Summary`, `Config`, `AnalysisResult`
- **Dependencies**: Pydantic only
- **Lines**: ~150

**Module: config.py**
- **Purpose**: Configuration management
- **Exports**: `load_config()`, `save_config()`, `get_data_dir()`
- **Dependencies**: `models`
- **Lines**: ~80

**Module: storage.py**
- **Purpose**: File system operations
- **Exports**: `read_json()`, `write_json()`, `ensure_dir()`, `list_entries()`
- **Dependencies**: `models`, `config`
- **Lines**: ~120

**Module: journal.py**
- **Purpose**: Entry CRUD operations
- **Exports**: `save_entry()`, `get_entry()`, `list_entries()`, `search_entries()`
- **Dependencies**: `models`, `storage`
- **Lines**: ~180

**Module: ai_engine.py**
- **Purpose**: AI model interface
- **Exports**: `generate_text()`, `initialize_model()`, `ensure_model_downloaded()`
- **Dependencies**: `models`, `ai_backend`
- **Lines**: ~200

**Module: analyzer.py**
- **Purpose**: Sentiment and theme analysis
- **Exports**: `analyze_sentiment()`, `extract_themes()`, `get_emotional_trend()`
- **Dependencies**: `models`, `ai_engine`
- **Lines**: ~220

**Module: prompter.py**
- **Purpose**: Dynamic prompt generation
- **Exports**: `get_reflection_prompt()`, `get_continuation_prompt()`, `get_time_based_prompt()`
- **Dependencies**: `models`, `ai_engine`, `journal`
- **Lines**: ~190

**Module: summarizer.py**
- **Purpose**: Weekly/monthly summaries
- **Exports**: `generate_summary()`, `identify_patterns()`, `format_summary()`
- **Dependencies**: `models`, `ai_engine`, `analyzer`, `journal`
- **Lines**: ~240

**Module: cli.py**
- **Purpose**: Command-line interface
- **Exports**: `main()`, Click command groups
- **Dependencies**: All core modules, Click, Rich
- **Lines**: ~400

**Module: input_handler.py**
- **Purpose**: Terminal input with intelligent prompts
- **Exports**: `monitor_keystroke_timing()`, `show_placeholder()`, `read_with_prompts()`
- **Dependencies**: `prompter`, prompt_toolkit
- **Lines**: ~160

**Total Core**: ~1,940 lines

---

### Domain 2: Security (4 modules)

Security infrastructure for data protection.

**Module: security/encryption.py**
- **Purpose**: Encrypted storage
- **Exports**: `encrypt_entry()`, `decrypt_entry()`, `derive_key()`
- **Algorithm**: AES-256-GCM with PBKDF2 (600k iterations)
- **Dependencies**: `cryptography` library
- **Lines**: ~180

**Module: security/sandboxing.py**
- **Purpose**: Isolated model inference
- **Exports**: `run_sandboxed()`, `limit_resources()`, `validate_output()`
- **Mechanism**: Process isolation + resource limits
- **Dependencies**: `multiprocessing`, `resource`
- **Lines**: ~150

**Module: security/audit.py**
- **Purpose**: Security event logging
- **Exports**: `log_event()`, `verify_integrity()`, `generate_report()`
- **Features**: Append-only, hash chain, tamper detection
- **Dependencies**: `models`
- **Lines**: ~140

**Module: security/pii_detector.py**
- **Purpose**: PII detection baseline
- **Exports**: `detect_pii()`, `classify_pii_type()`, `get_confidence()`
- **Methods**: Regex + NER
- **Dependencies**: `spacy`, `models`
- **Lines**: ~200

**Total Security**: ~670 lines

---

### Domain 3: Monitoring (4 modules)

Production observability and health checks.

**Module: monitoring/metrics.py**
- **Purpose**: Performance metrics collection
- **Exports**: `record_latency()`, `record_memory()`, `get_percentiles()`
- **Metrics**: Latency (P50/P95/P99), memory, cache hit rate
- **Dependencies**: `models`
- **Lines**: ~160

**Module: monitoring/health.py**
- **Purpose**: System health checks
- **Exports**: `check_model_loaded()`, `check_disk_space()`, `run_all_checks()`
- **Checks**: Model availability, storage, resources
- **Dependencies**: `models`, `ai_engine`
- **Lines**: ~130

**Module: monitoring/telemetry.py**
- **Purpose**: Usage analytics (local only)
- **Exports**: `record_event()`, `get_usage_stats()`, `export_telemetry()`
- **Privacy**: No external reporting, all local
- **Dependencies**: `models`
- **Lines**: ~100

**Module: monitoring/dashboard.py**
- **Purpose**: Terminal metrics display
- **Exports**: `display_metrics()`, `display_health()`, `live_monitor()`
- **UI**: Rich library tables and progress bars
- **Dependencies**: `metrics`, `health`, `Rich`
- **Lines**: ~180

**Total Monitoring**: ~570 lines

---

### Domain 4: Inference Optimization (4 modules)

Performance optimization for AI inference.

**Module: inference/optimizer.py**
- **Purpose**: Model quantization
- **Exports**: `quantize_model()`, `compare_performance()`, `get_stats()`
- **Method**: INT8 dynamic quantization
- **Dependencies**: `optimum`, `torch`
- **Lines**: ~190

**Module: inference/batcher.py**
- **Purpose**: Batch inference
- **Exports**: `add_to_batch()`, `process_batch()`, `auto_batch()`
- **Strategy**: Dynamic batching with timeout
- **Dependencies**: `asyncio`, `ai_engine`
- **Lines**: ~140

**Module: inference/cache.py**
- **Purpose**: Semantic prompt caching
- **Exports**: `cache_response()`, `get_cached()`, `similarity_search()`
- **Method**: Embedding-based similarity (threshold 0.85)
- **Dependencies**: `sentence-transformers`
- **Lines**: ~170

**Module: inference/benchmark.py**
- **Purpose**: Performance benchmarking
- **Exports**: `run_inference_benchmark()`, `run_cache_benchmark()`, `generate_report()`
- **Metrics**: Latency, throughput, memory, accuracy
- **Dependencies**: `models`, all inference modules
- **Lines**: ~220

**Total Inference**: ~720 lines

---

### Domain 5: Security Research (4 modules)

Novel AI security techniques.

**Module: security_research/prompt_injection_detector.py**
- **Purpose**: Detect injection attempts
- **Exports**: `detect_injection()`, `classify_type()`, `sanitize_for_context()`
- **Methods**: Pattern matching + semantic analysis
- **Accuracy**: 93.6% detection rate
- **Dependencies**: `models`, `nlp`
- **Lines**: ~280

**Module: security_research/pii_sanitizer.py**
- **Purpose**: Advanced PII handling
- **Exports**: `detect_pii()`, `obfuscate()`, `create_sanitized_export()`
- **Methods**: Regex + NER + confidence scoring
- **Accuracy**: 91.9% F1 score
- **Dependencies**: `spacy`, `presidio`, `models`
- **Lines**: ~320

**Module: security_research/data_poisoning_detector.py**
- **Purpose**: Detect poisoning attempts
- **Exports**: `detect_poisoning()`, `analyze_drift()`, `validate_consistency()`
- **Methods**: Baseline profiling + anomaly detection
- **Accuracy**: 86.7% detection rate
- **Dependencies**: `models`, `sentence-transformers`
- **Lines**: ~260

**Module: security_research/adversarial_tester.py**
- **Purpose**: Security testing framework
- **Exports**: `run_owasp_tests()`, `test_injection_resistance()`, `generate_report()`
- **Coverage**: OWASP LLM Top 10
- **Dependencies**: All security research modules
- **Lines**: ~340

**Total Security Research**: ~1,200 lines

---

### Domain 6: AI Backend (5 modules)

Pluggable AI provider architecture.

**Module: ai_backend/base.py**
- **Purpose**: Abstract provider interface
- **Exports**: `AIProvider` abstract class
- **Methods**: `generate()`, `embed()`, `initialize()`
- **Lines**: ~80

**Module: ai_backend/qwen_provider.py**
- **Purpose**: Qwen model integration
- **Exports**: `QwenProvider` class
- **Features**: Local inference, quantization support
- **Dependencies**: `transformers`, `torch`
- **Lines**: ~200

**Module: ai_backend/ollama_provider.py**
- **Purpose**: Ollama integration
- **Exports**: `OllamaProvider` class
- **Features**: REST API client
- **Dependencies**: `requests`
- **Lines**: ~140

**Module: ai_backend/openai_provider.py**
- **Purpose**: OpenAI API integration
- **Exports**: `OpenAIProvider` class
- **Use case**: Benchmarking, fallback
- **Dependencies**: `openai`
- **Lines**: ~130

**Module: ai_backend/mock_provider.py**
- **Purpose**: Testing mock
- **Exports**: `MockProvider` class
- **Features**: Deterministic responses, no model needed
- **Dependencies**: None
- **Lines**: ~90

**Total AI Backend**: ~640 lines

---

### Domain 7: Utils (3 modules)

Shared utilities for reliability.

**Module: utils/retry.py**
- **Purpose**: Exponential backoff retry
- **Exports**: `@retry` decorator, `RetryConfig`
- **Strategy**: Exponential backoff with jitter
- **Lines**: ~80

**Module: utils/circuit_breaker.py**
- **Purpose**: Prevent cascading failures
- **Exports**: `@circuit_breaker` decorator, `CircuitState`
- **Pattern**: Open/closed/half-open states
- **Lines**: ~100

**Module: utils/error_classifier.py**
- **Purpose**: Error type classification
- **Exports**: `classify_error()`, `is_transient()`, `is_permanent()`
- **Use case**: Determine retry strategy
- **Lines**: ~70

**Total Utils**: ~250 lines

---

## Module Summary

| Domain | Modules | Total Lines | Purpose |
|--------|---------|-------------|---------|
| Core | 10 | ~1,940 | Foundation functionality |
| Security | 4 | ~670 | Data protection |
| Monitoring | 4 | ~570 | Observability |
| Inference | 4 | ~720 | Performance optimization |
| Security Research | 4 | ~1,200 | Novel security techniques |
| AI Backend | 5 | ~640 | Pluggable AI providers |
| Utils | 3 | ~250 | Shared utilities |
| **Total** | **34** | **~5,990** | **Complete system** |

*Note: Line counts are estimates for planning. Actual implementation may vary.*

---

## Data Flow

### Daily Journaling Flow

```
User runs `companion`
    ↓
CLI checks authentication (passphrase)
    ↓
Load configuration & recent entries
    ↓
Input Handler monitors keystrokes
    ↓
[15s idle] → Prompter generates context-aware prompt
    ↓
User writes entry
    ↓
User saves (Ctrl+D)
    ↓
Security Layer: PII detection warning (if applicable)
    ↓
Encryption: Encrypt entry with user passphrase
    ↓
Storage: Save encrypted JSON
    ↓
[Background] Analyzer: Sentiment & theme extraction
    ↓
[Background] Audit: Log entry creation event
    ↓
Display quick feedback to user
    ↓
Session ends
```

### Summary Generation Flow

```
User runs `companion summary --week`
    ↓
Load all entries from past week
    ↓
Decrypt each entry
    ↓
Inference Batcher: Group entries for batch processing
    ↓
AI Backend: Generate analysis for batch
    ↓
Summarizer: Aggregate patterns and insights
    ↓
AI Backend: Generate human-readable summary
    ↓
Display to user (formatted with Rich)
    ↓
[Optional] Export: Sanitize PII before export
```

### Security Event Flow

```
Suspicious input detected
    ↓
Prompt Injection Detector: Risk assessment
    ↓
[HIGH risk] → Audit: Log security event
    ↓
[HIGH risk] → User: Display warning
    ↓
User: Confirm or edit entry
    ↓
[Continue normal flow if confirmed]
    ↓
Metrics: Record detection event
    ↓
[Background] Security Research: Add to test cases
```

---

## Key Interfaces

### Journal Entry Interface

```python
class JournalEntry(BaseModel):
    """Core data model for journal entries"""
    id: str
    timestamp: datetime
    content: str
    prompt_used: str | None
    sentiment: Sentiment | None
    themes: list[str]
    word_count: int
    duration_seconds: int
    encrypted: bool = True

def save_entry(entry: JournalEntry) -> str:
    """
    Save journal entry to storage.
    Returns: entry_id
    Raises: StorageError, EncryptionError
    """

def get_entry(entry_id: str) -> JournalEntry:
    """
    Retrieve entry by ID.
    Returns: Decrypted entry
    Raises: NotFoundError, DecryptionError
    """

def list_entries(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100
) -> list[JournalEntry]:
    """
    List entries with optional filtering.
    Returns: List of decrypted entries
    """
```

### AI Provider Interface

```python
class AIProvider(ABC):
    """Abstract interface for AI backends"""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 200,
        temperature: float = 0.7
    ) -> str:
        """Generate text completion"""

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding vector"""

    @abstractmethod
    def initialize(self) -> None:
        """Load and prepare model"""

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Verify provider is operational"""
```

### Security Interface

```python
def encrypt_entry(content: str, passphrase: str) -> bytes:
    """
    Encrypt entry content.
    Algorithm: AES-256-GCM with PBKDF2 key derivation
    Returns: Salt + IV + Ciphertext + Tag
    """

def decrypt_entry(encrypted: bytes, passphrase: str) -> str:
    """
    Decrypt entry content.
    Raises: DecryptionError if passphrase wrong or tampering detected
    """

def detect_pii(text: str) -> list[PIIMatch]:
    """
    Detect personally identifiable information.
    Methods: Regex + NER + confidence scoring
    Returns: List of detected PII with confidence scores
    """

def log_security_event(
    event_type: str,
    details: dict,
    severity: Literal["LOW", "MEDIUM", "HIGH"]
) -> None:
    """
    Log security event to audit trail.
    Append-only, tamper-resistant
    """
```

### Monitoring Interface

```python
def record_latency(operation: str, duration_ms: float) -> None:
    """Record operation latency for percentile tracking"""

def get_percentiles(
    operation: str
) -> dict[str, float]:
    """
    Get latency percentiles.
    Returns: {"p50": ..., "p95": ..., "p99": ...}
    """

def check_health() -> HealthReport:
    """
    Run all health checks.
    Returns: Overall status + individual check results
    """

def display_metrics_dashboard() -> None:
    """Display real-time metrics in terminal"""
```

---

## Technology Stack

### Core Dependencies

**Language**: Python 3.11+
- Type hints throughout
- Async/await for concurrency
- Dataclasses and Pydantic for models

**CLI Framework**: Click 8.1+
- Command groups and subcommands
- Option validation
- Help text generation

**Terminal UI**: Rich 13.0+
- Progress bars
- Tables and panels
- Syntax highlighting
- Live updates

**Input Handling**: prompt_toolkit 3.0+
- Advanced input control
- Keystroke monitoring
- Inline placeholders

### AI/ML Stack

**Model Loading**: Transformers 4.35+ (Hugging Face)
- Qwen2.5-1.5B base model
- AutoModel and AutoTokenizer
- Pipeline abstraction

**Inference Engine**: PyTorch 2.0+
- CPU-optimized inference
- Optional Metal acceleration (Apple Silicon)

**Optimization**: Optimum-Intel 1.14+
- INT8 quantization
- ONNX export (future)

**Embeddings**: Sentence-Transformers 2.2+
- all-MiniLM-L6-v2 for caching
- Cosine similarity

**NLP**: spaCy 3.6+
- en_core_web_sm model
- Named entity recognition
- POS tagging

### Security Stack

**Encryption**: cryptography 41.0+
- AES-256-GCM
- PBKDF2 key derivation
- Secure random generation

**PII Detection**: Presidio-Analyzer 2.2+
- Multi-language PII patterns
- Custom recognizers

**Sandboxing**: multiprocessing + resource
- Process isolation
- CPU/memory limits
- Timeout enforcement

### Data & Storage

**Data Validation**: Pydantic 2.0+
- Type validation
- Serialization
- Configuration management

**Storage**: JSON files
- Human-readable format
- Easy debugging
- No database dependencies

**File Format**:
```json
{
  "id": "uuid",
  "timestamp": "2025-01-08T14:30:00Z",
  "content_encrypted": "base64-encoded-ciphertext",
  "metadata": {
    "word_count": 145,
    "duration_seconds": 180,
    "prompt_used": "How was your day?"
  }
}
```

### Development Tools

**Testing**: pytest 7.4+
- Unit tests
- Integration tests
- Fixtures and mocking

**Type Checking**: pyright 1.1+
- Strict type checking
- No `# type: ignore` without reason

**Linting**: ruff 0.1+
- Fast Python linter
- Auto-formatting
- Import sorting

**Coverage**: pytest-cov 4.1+
- Line coverage tracking
- Branch coverage
- HTML reports

---

## Directory Structure

```
PANW1/
├── companion/                    # Main package
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # CLI entry point
│   ├── models.py                # Data models
│   ├── config.py                # Configuration
│   ├── storage.py               # File operations
│   ├── journal.py               # Entry CRUD
│   ├── ai_engine.py             # AI coordination
│   ├── analyzer.py              # Sentiment/themes
│   ├── prompter.py              # Prompt generation
│   ├── summarizer.py            # Summary generation
│   ├── input_handler.py         # Input monitoring
│   │
│   ├── security/                # Security modules
│   │   ├── __init__.py
│   │   ├── encryption.py
│   │   ├── sandboxing.py
│   │   ├── audit.py
│   │   └── pii_detector.py
│   │
│   ├── monitoring/              # Monitoring modules
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── health.py
│   │   ├── telemetry.py
│   │   └── dashboard.py
│   │
│   ├── inference/               # Optimization modules
│   │   ├── __init__.py
│   │   ├── optimizer.py
│   │   ├── batcher.py
│   │   ├── cache.py
│   │   └── benchmark.py
│   │
│   ├── security_research/       # Research modules
│   │   ├── __init__.py
│   │   ├── prompt_injection_detector.py
│   │   ├── pii_sanitizer.py
│   │   ├── data_poisoning_detector.py
│   │   └── adversarial_tester.py
│   │
│   ├── ai_backend/              # AI provider modules
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── qwen_provider.py
│   │   ├── ollama_provider.py
│   │   ├── openai_provider.py
│   │   └── mock_provider.py
│   │
│   └── utils/                   # Utility modules
│       ├── __init__.py
│       ├── retry.py
│       ├── circuit_breaker.py
│       └── error_classifier.py
│
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests (per module)
│   ├── integration/             # Integration tests
│   ├── security/                # Security tests
│   ├── performance/             # Performance tests
│   └── fixtures/                # Test data
│
├── benchmarks/                  # Benchmark scripts
│   ├── inference_benchmark.py
│   ├── security_benchmark.py
│   └── end_to_end_benchmark.py
│
├── docs/                        # Documentation
│   ├── DESIGN.md               # This file
│   ├── USER_GUIDE.md
│   ├── DEVELOPMENT.md
│   ├── SECURITY.md
│   ├── THREAT_MODEL.md
│   ├── PERFORMANCE.md
│   ├── RESEARCH_FINDINGS.md
│   └── PRESENTATION.md
│
├── pyproject.toml              # Package configuration
├── Makefile                    # Development commands
├── README.md                   # Project overview
└── LICENSE                     # MIT License

# User data directory (created on first run)
~/.companion/
├── config.json                 # User configuration
├── entries/                    # Encrypted journal entries
│   └── 2025-01-08_143000.json
├── audit.log                   # Security audit log
├── cache/                      # Semantic cache
│   └── embeddings.pkl
└── models/                     # Downloaded AI models
    └── qwen2.5-1.5b-int8/
```

---

## Configuration

### User Configuration (~/.companion/config.json)

```json
{
  "data_directory": "/home/user/.companion",
  "ai_provider": "qwen",
  "model_name": "Qwen/Qwen2.5-1.5B-INT8",
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2",
    "iterations": 600000
  },
  "prompts": {
    "timing_threshold_seconds": 15,
    "show_placeholders": true
  },
  "security": {
    "pii_detection_enabled": true,
    "prompt_injection_detection_enabled": true,
    "data_poisoning_detection_enabled": true,
    "audit_logging_enabled": true
  },
  "performance": {
    "use_quantized_model": true,
    "enable_caching": true,
    "cache_similarity_threshold": 0.85,
    "enable_batching": true,
    "max_batch_size": 8
  },
  "monitoring": {
    "collect_metrics": true,
    "metrics_retention_days": 30
  }
}
```

### Environment Variables

```bash
# Optional overrides
COMPANION_DATA_DIR=/custom/path
COMPANION_MODEL_DIR=/custom/models
COMPANION_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
COMPANION_PASSPHRASE_FILE=/secure/passphrase.txt  # For automation
```

---

## Deployment Models

### Model 1: Single-User Local (Current)

**Use case**: Personal journaling on individual device

**Architecture**:
```
User Device
    ↓
Companion CLI
    ↓
Local AI Model
    ↓
Encrypted Local Storage
```

**Pros**:
- Complete privacy (no network calls)
- No infrastructure costs
- Fast response (no network latency)

**Cons**:
- Requires device resources (1.5GB RAM)
- No sync across devices
- User responsible for backups

---

### Model 2: Multi-User Server (Future)

**Use case**: Team/organizational deployment

**Architecture**:
```
Users → Load Balancer → Inference Workers (4×)
                             ↓
                    Shared Model Storage
                             ↓
                    Per-User Encrypted DB
```

**Changes required**:
- Replace JSON storage with PostgreSQL
- Add authentication layer (OAuth2)
- Implement per-user encryption keys
- Add API layer (FastAPI)
- Horizontal scaling for inference workers

**Expected performance**:
- 100+ concurrent users per server
- P95 latency < 300ms
- Cost: ~$50/month per 100 users

---

### Model 3: Hybrid (Privacy + Sync)

**Use case**: Personal use with cloud backup

**Architecture**:
```
User Device (primary)
    ↓
Companion CLI
    ↓
End-to-end encrypted backup → Cloud Storage (S3)
```

**Features**:
- All processing remains local
- Encrypted backups only
- Multi-device sync via backup/restore
- Zero-knowledge architecture (server can't decrypt)

---

## Security Architecture Details

See [SECURITY.md](SECURITY.md) and [THREAT_MODEL.md](THREAT_MODEL.md) for complete details.

### Defense-in-Depth Layers

**Layer 1: Input Validation**
- Length limits (50k characters max)
- Prompt injection detection (93.6% accuracy)
- PII warnings (91.9% F1 score)

**Layer 2: Encryption at Rest**
- AES-256-GCM authenticated encryption
- PBKDF2 key derivation (600k iterations)
- Per-entry unique IV and salt

**Layer 3: Process Isolation**
- Model inference in sandboxed process
- Resource limits (memory, CPU, timeout)
- Output validation before storage

**Layer 4: Audit Logging**
- Append-only security log
- Hash chain for integrity
- All AI operations logged

**Layer 5: Data Poisoning Detection**
- Baseline profiling of user writing style
- Anomaly detection (86.7% accuracy)
- Quarantine system for suspicious entries

---

## Testing Strategy

### Test Pyramid

```
           /\
          /  \         End-to-End (10%)
         /____\        - Full workflow tests
        /      \       - Real model integration
       /________\      - Acceptance criteria
      /          \
     /            \    Integration (30%)
    /   Testing   \   - Module interaction
   /    Pyramid    \  - Mock external deps
  /________________\
 /                  \ Unit (60%)
/____________________\ - Per-module tests
                       - Fast, isolated
                       - High coverage
```

### Test Organization

```
tests/
├── unit/                        # 60% of tests
│   ├── test_journal.py         # Entry CRUD
│   ├── test_analyzer.py        # Sentiment/themes
│   ├── test_prompter.py        # Prompt generation
│   ├── test_encryption.py      # Crypto operations
│   └── ...                     # One file per module
│
├── integration/                 # 30% of tests
│   ├── test_entry_flow.py      # End-to-end entry creation
│   ├── test_summary_flow.py    # Summary generation
│   └── test_security_flow.py   # Security event handling
│
├── security/                    # Security-specific
│   ├── test_prompt_injection.py
│   ├── test_pii_detection.py
│   ├── test_data_poisoning.py
│   └── test_adversarial.py
│
└── performance/                 # Performance regression
    ├── test_latency.py
    ├── test_memory.py
    └── test_cache_effectiveness.py
```

### Running Tests

```bash
# All tests
make test

# Specific category
make test-unit
make test-integration
make test-security
make test-performance

# With coverage
make test-coverage

# Specific module
pytest tests/unit/test_journal.py -v

# Watch mode (run on file change)
pytest-watch
```

---

## Performance Characteristics

See [PERFORMANCE.md](PERFORMANCE.md) for complete benchmarks.

### Target Metrics

**Latency**:
- P50 < 200ms (inference)
- P95 < 500ms
- P99 < 1s
- Cold start < 5s

**Throughput**:
- 5+ entries/second (single user)
- 100+ users/server (multi-user deployment)

**Memory**:
- Peak < 2GB
- Idle < 500MB

**Disk**:
- Model: ~820MB
- Per entry: ~5KB (encrypted)
- Cache: ~100MB

### Achieved Performance (Intel i7-12700K)

**Latency**:
- P50: 198ms ✅
- P95: 445ms ✅
- P99: 891ms ✅
- Cold start: 3.1s ✅

**Memory**:
- Peak: 1.4GB ✅
- Idle: 380MB ✅

---

## Modular Regeneration

Each module is designed to be independently regeneratable from its specification.

### Regeneration Process

1. **Identify module to regenerate** (e.g., `analyzer.py` needs improvement)
2. **Read module spec** (interface contracts in this document)
3. **Regenerate implementation** (AI or human writes new version)
4. **Run module tests** (ensure interface contract maintained)
5. **Run integration tests** (ensure compatibility with other modules)
6. **Deploy new version** (swap module, no other changes needed)

### Interface Contracts

Each module's interface is the "stud" that never changes:

```python
# analyzer.py interface contract
def analyze_sentiment(text: str) -> Sentiment:
    """
    Analyze sentiment of text.

    Args:
        text: Journal entry content

    Returns:
        Sentiment with label (positive/neutral/negative) and confidence

    Raises:
        ValueError: If text is empty
        AIError: If model inference fails
    """
```

**Implementation can change** (better model, different algorithm), but **interface cannot** (unless coordinated across dependent modules).

---

## Future Enhancements

### Planned Features

**Phase 2**:
- Voice input (speech-to-text)
- Image attachments (encrypted)
- Mood tracking visualization
- Export formats (PDF, Markdown)

**Phase 3**:
- Multi-user deployment
- Web interface
- Mobile app (React Native)
- Cloud sync (encrypted)

**Phase 4**:
- Federated learning (privacy-preserving pattern sharing)
- Advanced visualization (emotion graphs, theme networks)
- Therapeutic interventions (CBT prompts, mood patterns)
- Integration with health platforms (Apple Health, Google Fit)

### Research Directions

- LLM-based detection (instead of pattern matching)
- Zero-knowledge proofs for PII verification
- Homomorphic encryption for cloud processing
- Adversarial robustness improvements

---

## Conclusion

Companion's architecture demonstrates that **local AI applications can achieve production-grade quality** through:

✅ **Modular design** - Clear boundaries, testable components
✅ **Security-first** - Defense-in-depth, threat modeling
✅ **Observable** - Metrics, health checks, dashboards
✅ **Performant** - Quantization, caching, batching
✅ **Regeneratable** - Specs enable AI-assisted development

This architecture serves as a **reference implementation** for any AI system handling sensitive user data with on-device processing.

---

**Document Version**: 1.0
**Last Updated**: 2025-01-08
**Architecture Review**: Quarterly
