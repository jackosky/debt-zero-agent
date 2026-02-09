# Example Usage: SonarLint Visual Studio with Gemini

This example demonstrates how to run the debt-zero-agent on the `sonarlint-visualstudio` repository using Google Gemini.

## Prerequisites

1. **API Keys**:
   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
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
  --llm gemini \
  --limit 10 \
  --dry-run
```

### 2. Apply Fixes
Once you're satisfied with the dry run:

```bash
poetry run debt-zero-agent /Users/jacekporeda/src/sonarlint-visualstudio \
  --fetch-issues "your-project-key" \
  --llm gemini \
  --limit 10
```

## Using the Example Script

A ready-to-use script is provided:

```bash
# Edit the script to add your API keys and project key
vim examples/run_gemini_example.sh

# Run it
./examples/run_gemini_example.sh
```

## Options Explained

- `--fetch-issues PROJECT_KEY`: Automatically downloads issues from SonarQube API
- `--llm gemini`: Use Google Gemini 2.0 Flash model
- `--limit 10`: Process only 10 issues (default, adjust as needed)
- `--dry-run`: Preview fixes without applying them
- `--sonar-url URL`: Use custom SonarQube server (default: sonarcloud.io)
- `--max-retries 3`: Retry failed fixes up to 3 times (default)

## Expected Output

```
Fetched 10 issues from https://sonarcloud.io
Loaded 10 issues

Starting agent workflow with gemini...
Mode: DRY RUN

============================================================
RESULTS
============================================================

Successful fixes: 7
  ✓ AYzKb-001: src/file1.cs
  ✓ AYzKb-002: src/file2.cs
  ...

Failed fixes: 3
  ✗ AYzKb-008: Validation error

Success rate: 70.0%
```

## Tips

1. **Start Small**: Use `--limit 10` initially to test
2. **Review Diffs**: Always run with `--dry-run` first
3. **Increase Gradually**: Once confident, increase `--limit 50` or more
4. **Check Results**: Review the generated diffs before committing
