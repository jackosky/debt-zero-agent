# Example Usage: SonarLint Visual Studio with OpenAI

This example demonstrates how to run the debt-zero-agent on the `sonarlint-visualstudio` repository using OpenAI GPT-4o.

## Prerequisites

1. **API Keys**:
   ```bash
   export OPENAI_API_KEY="your-openai-key"
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
  --llm openai \
  --limit 5 \
  --dry-run
```

### 2. Apply Fixes
Once you're satisfied with the dry run:

```bash
poetry run debt-zero-agent /Users/jacekporeda/src/sonarlint-visualstudio \
  --fetch-issues "your-project-key" \
  --llm openai \
  --limit 5
```

## Using the Example Script

A ready-to-use script is provided:

```bash
# Edit the script to add your API keys and project key
vim examples/run_openai_example.sh

# Run it
./examples/run_openai_example.sh
```

## Why OpenAI?

✅ **Better rate limits** - More generous than Gemini free tier
✅ **GPT-4o** - Latest and most capable model
✅ **Reliable** - Production-ready with good uptime
✅ **Fast** - Quick response times

## Options Explained

- `--fetch-issues PROJECT_KEY`: Automatically downloads issues from SonarQube API
- `--llm openai`: Use OpenAI GPT-4o model
- `--limit 5`: Process only 5 issues (adjust as needed)
- `--dry-run`: Preview fixes without applying them
- `--sonar-url URL`: Use custom SonarQube server (default: sonarcloud.io)
- `--max-retries 3`: Retry failed fixes up to 3 times (default)

## Expected Output

```
Fetched 5 issues from https://sonarcloud.io (excluded external rules)

Starting agent workflow with openai...
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

## Tips

1. **Start Small**: Use `--limit 5` initially to test
2. **Review Diffs**: Always run with `--dry-run` first
3. **Increase Gradually**: Once confident, increase `--limit 20` or more
4. **Check Results**: Review the generated diffs before committing
5. **Monitor Costs**: OpenAI API has usage costs, monitor your usage
