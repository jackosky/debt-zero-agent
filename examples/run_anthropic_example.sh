#!/bin/bash
# Example: Running debt-zero-agent on sonarlint-visualstudio with Anthropic (Claude 3.5 Sonnet)

# Set required API keys
export ANTHROPIC_API_KEY="-"

export SONAR_TOKEN="-"  # Optional but recommended

# Repository path
REPO_PATH="/Users/jacekporeda/src/sonarlint-visualstudio"

# SonarQube project key (replace with actual project key)
PROJECT_KEY="sonarlint-visualstudio"

# Option 1: Dry run - Preview fixes without applying them
echo "=== DRY RUN MODE (Sonnet) ==="
poetry run debt-zero-agent "$REPO_PATH" \
  --fetch-issues "$PROJECT_KEY" \
  --llm anthropic \
  --limit 5 \
  --dry-run

# Option 2: Apply fixes (remove --dry-run)
# Uncomment to actually apply fixes:
# echo "=== APPLYING FIXES (Sonnet) ==="
# poetry run debt-zero-agent "$REPO_PATH" \
#   --fetch-issues "$PROJECT_KEY" \
#   --llm anthropic \
#   --limit 5

# Option 3: Use specific model version
# echo "=== USING SPECIFIC MODEL VER ==="
# poetry run debt-zero-agent "$REPO_PATH" \
#   --fetch-issues "$PROJECT_KEY" \
#   --llm anthropic \
#   --model "claude-3-5-sonnet-latest" \
#   --limit 5 \
#   --dry-run

# Option 4: Use pre-downloaded issues file
# If you already have an issues.json file:
# poetry run debt-zero-agent "$REPO_PATH" \
#   --issues issues.json \
#   --llm anthropic \
#   --limit 5 \
#   --dry-run

# Option 5: Process more issues (increase limit)
# poetry run debt-zero-agent "$REPO_PATH" \
#   --fetch-issues "$PROJECT_KEY" \
#   --llm anthropic \
#   --limit 20 \
#   --dry-run
