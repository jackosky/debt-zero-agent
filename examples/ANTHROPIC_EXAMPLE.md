# Example Usage: SonarLint Visual Studio with Anthropic Claude 3.5 Sonnet

This example demonstrates how to run the debt-zero-agent on the `sonarlint-visualstudio` repository using Anthropic's Claude 3.5 Sonnet model.

## Prerequisites

1. **API Keys**:
   ```bash
   export ANTHROPIC_API_KEY="your-anthropic-key"
   export SONAR_TOKEN="your-sonarqube-token"  # Optional
   ```

2. **SonarQube Project Key**: You'll need the project key from SonarQube/SonarCloud

## Quick Start

### 1. Dry Run (Recommended First)
Preview fixes without applying them:

```bash
cd /Users/jacekporeda/src/debt-zero-agent

poetry run debt-zero-agent /Users/jacekporeda/src/sonarlint-visualstudio \
  --fetch-issues "your-project-key" \
  --llm anthropic \
  --limit 5 \
  --dry-run
```

**Note**: The `--llm anthropic` flag defaults to using the **Sonnet** model (`claude-sonnet-4-5-20250929`). You can override this with `--model`.

### 2. Apply Fixes
Once you're satisfied with the dry run:

```bash
poetry run debt-zero-agent /Users/jacekporeda/src/sonarlint-visualstudio \
  --fetch-issues "your-project-key" \
  --llm anthropic \
  --limit 5
```

### 3. Using a Specific Model Version
To use a specific version of Sonnet or another Claude model:

```bash
poetry run debt-zero-agent /Users/jacekporeda/src/sonarlint-visualstudio \
  --fetch-issues "your-project-key" \
  --llm anthropic \
  --model claude-3-5-sonnet-latest \
  --limit 5 \
  --dry-run
```

## Using the Example Script

A ready-to-use script is provided:

```bash
# Edit the script to add your API keys and project key
vim examples/run_anthropic_example.sh

# Run it
./examples/run_anthropic_example.sh
```

## Why Anthropic Sonnet?

✅ **Complex Logic** - Excellent at reasoning through code logic
✅ **Code Quality** - Produces high-quality, idiomatic code fixes
✅ **Context Window** - Large context window for understanding surrounding code
✅ **Safety** - High safety standards for enterprise codebases

## Options Explained

- `--fetch-issues PROJECT_KEY`: Automatically downloads issues from SonarQube API
- `--llm anthropic`: Use Anthropic Claude 3.5 Sonnet model
- `--model NAME`: (Optional) Override the specific model name
- `--limit 5`: Process only 5 issues (adjust as needed)
- `--dry-run`: Preview fixes without applying them
- `--sonar-url URL`: Use custom SonarQube server (default: sonarcloud.io)
- `--max-retries 3`: Retry failed fixes up to 3 times (default)

## Expected Output

```
Fetched 5 issues from https://sonarcloud.io (excluded external rules)

Starting agent workflow with anthropic...
Mode: DRY RUN

Processing issue 1/5: csharpsquid:S1234
  ✓ Fix generated
  ✓ Validation passed

...

============================================================
RESULTS
============================================================

Successful fixes: 4
  ✓ AYzKb-001: src/file1.cs
  ✓ AYzKb-002: src/file2.cs
  ...

Failed fixes: 1
  ✗ AYzKb-005: Validation error

Success rate: 80.0%
```
