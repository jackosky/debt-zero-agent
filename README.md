# debt-zero-agent

A LangChain-based agent that automatically fixes SonarQube issues using AST-based localization and LLM-powered code modifications.

## Features

- 🔍 **AST-based issue localization** - Precise targeting using tree-sitter
- 🤖 **Dual LLM support** - Benchmark OpenAI vs Anthropic
- ✅ **Validation layer** - Python AST + tree-sitter syntax checking
- 📊 **Issue filtering** - Handles BUG, VULNERABILITY, CODE_SMELL (excludes security hotspots)

## Installation

```bash
poetry install
```

## Usage

```bash
poetry run debt-zero-agent /path/to/repo --issues issues.json
```

### Options

- `--issues`, `-i` - Path to JSON file with SonarQube issues (from `api/issues/search`)
- `--dry-run` - Show proposed fixes without applying them
- `--llm` - LLM provider: `openai` or `anthropic` (default: `openai`)

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_models.py

# Run with coverage
poetry run pytest --cov=debt_zero_agent
```

### Project Structure

```
debt_zero_agent/
├── agent/          # LangGraph orchestration
├── models/         # SonarQube & fix result models
├── validation/     # AST validation & issue localization
├── tools/          # File operations & code search
└── prompts/        # LLM prompt templates
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed design and component descriptions
- [Tasks](docs/TASKS.md) - Development task breakdown

## License

MIT
