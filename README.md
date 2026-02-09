# Debt-Zero-Agent

A LangChain-based agent that automatically fixes SonarQube issues using AST-based localization and LLM-powered code modifications.

## 🎯 Features

- **AST-based issue localization** - Precise targeting using tree-sitter
- **Triple LLM support** - OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini Pro
- **Multi-language validation** - Python AST + tree-sitter syntax checking
- **Native tool integration** - ripgrep for search, Unix diff for diffs
- **Dry-run mode** - Preview fixes before applying
- **Retry logic** - Automatic retry with validation feedback

## 📦 Installation

```bash
poetry install
```

## 🚀 Usage

### Basic Usage

```bash
# Option 1: Fetch issues automatically from SonarQube API
export SONAR_TOKEN=your-token
poetry run debt-zero-agent /path/to/repo --fetch-issues your-project-key --dry-run

# Option 2: Use pre-downloaded issues JSON
poetry run debt-zero-agent /path/to/repo --issues issues.json --dry-run

# Apply fixes with OpenAI
export OPENAI_API_KEY=your-key
poetry run debt-zero-agent /path/to/repo --fetch-issues your-project-key

# Apply fixes with Anthropic
export ANTHROPIC_API_KEY=your-key
poetry run debt-zero-agent /path/to/repo --fetch-issues your-project-key --llm anthropic

# Apply fixes with Google Gemini
export GOOGLE_API_KEY=your-key
poetry run debt-zero-agent /path/to/repo --fetch-issues your-project-key --llm gemini
```

### Options

```
positional arguments:
  repo_path             Path to the repository root

options:
  -h, --help            Show help message
  -i, --issues ISSUES   Path to SonarQube issues JSON file
  --fetch-issues PROJECT_KEY
                        Fetch issues from SonarQube API (requires SONAR_TOKEN)
  --sonar-url URL       SonarQube server URL (default: https://sonarcloud.io)
  --dry-run             Show proposed fixes without applying them
  --llm {openai,anthropic,gemini}
                        LLM provider to use (default: openai)
  --max-retries MAX_RETRIES
                        Maximum retry attempts per issue (default: 3)
  --limit LIMIT         Maximum number of issues to process (default: 10)
```

**Note**: Either `--issues` or `--fetch-issues` must be specified, but not both.

### Getting SonarQube Issues

Export issues from SonarQube Cloud using the API:

```bash
# Replace with your project key and token
PROJECT_KEY="your-project-key"
SONAR_TOKEN="your-token"

# Fetch issues (CODE_SMELL, BUG, VULNERABILITY)
curl -u "${SONAR_TOKEN}:" \
  "https://sonarcloud.io/api/issues/search?componentKeys=${PROJECT_KEY}&types=CODE_SMELL,BUG&resolved=false&ps=500" \
  -o issues.json

# Or for self-hosted SonarQube
curl -u "${SONAR_TOKEN}:" \
  "https://your-sonarqube.com/api/issues/search?componentKeys=${PROJECT_KEY}&types=CODE_SMELL,BUG&resolved=false&ps=500" \
  -o issues.json
```

**Note**: The agent will automatically fetch rule details (descriptions, examples) from SonarQube to enhance fix quality.

## 🧪 Development

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
├── agent/              # LangGraph orchestration
│   ├── llm.py         # LLM factory (OpenAI/Anthropic)
│   ├── state.py       # Agent state management
│   ├── nodes.py       # Workflow nodes
│   └── graph.py       # LangGraph workflow
├── models/            # Pydantic models
│   ├── issue.py       # SonarQube issue models
│   └── fix.py         # Fix result models
├── validation/        # AST validation & localization
│   ├── ast_validator.py
│   ├── tree_sitter.py
│   └── locator.py
├── tools/             # LangChain tools
│   ├── file_reader.py
│   ├── file_writer.py
│   ├── code_search.py  # ripgrep-based search
│   └── diff_tool.py    # Native diff
├── prompts/           # LLM prompt templates
└── cli.py             # CLI entry point
```

## 🏗️ Architecture

The agent uses a LangGraph workflow with the following nodes:

1. **select_next_issue** - Pick next issue to fix
2. **analyze_issue** - Understand issue context using AST
3. **apply_fix** - Generate code fix using LLM
4. **validate_fix** - Validate syntax and structure
5. **finalize** - Generate summary report

The workflow includes retry logic: if validation fails, the agent retries up to `max_retries` times with validation feedback.

## 📊 Test Coverage

**48 tests passing** across all modules:
- Models: 7 tests
- Validation: 11 tests
- Tools: 11 tests
- Agent: 8 tests
- CLI: 5 tests
- Integration: 6 tests

## 📝 Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed design
- [Tasks](docs/TASKS.md) - Development breakdown

## 🔧 Requirements

- Python 3.12+
- OpenAI API key or Anthropic API key
- Optional: ripgrep (for faster code search)

## 📄 License

MIT
