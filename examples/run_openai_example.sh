#!/bin/bash
# Example: Running debt-zero-agent on sonarlint-visualstudio with OpenAI

# Set required API keys
export OPENAI_API_KEY="-"
export SONAR_TOKEN=""  # Optional but recommended

# Repository path
REPO_PATH="/Users/jacekporeda/src/sonarlint-visualstudio"

# SonarQube project key (replace with actual project key)
PROJECT_KEY="sonarlint-visualstudio"

# Option 1: Dry run - Preview fixes without applying them
echo "=== DRY RUN MODE ==="
poetry run debt-zero-agent "$REPO_PATH" \
  --fetch-issues "$PROJECT_KEY" \
  --llm openai \
  --limit 5 \
  --dry-run

# Option 2: Apply fixes (remove --dry-run)
# Uncomment to actually apply fixes:
# echo "=== APPLYING FIXES ==="
# poetry run debt-zero-agent "$REPO_PATH" \
#   --fetch-issues "$PROJECT_KEY" \
#   --llm openai \
#   --limit 5

# Option 3: Use pre-downloaded issues file
# If you already have an issues.json file:
# poetry run debt-zero-agent "$REPO_PATH" \
#   --issues issues.json \
#   --llm openai \
#   --limit 5 \
#   --dry-run

# Option 4: Process more issues (increase limit)
# poetry run debt-zero-agent "$REPO_PATH" \
#   --fetch-issues "$PROJECT_KEY" \
#   --llm openai \
#   --limit 20 \
#   --dry-run

# Option 5: Use self-hosted SonarQube
# poetry run debt-zero-agent "$REPO_PATH" \
#   --fetch-issues "$PROJECT_KEY" \
#   --sonar-url "https://your-sonarqube.com" \
#   --llm openai \
#   --limit 5 \
#   --dry-run
