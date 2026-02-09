"""SonarQube API client for fetching rule details."""

import os
from typing import Optional

import requests
from pydantic import BaseModel


class RuleDescription(BaseModel):
    """SonarQube rule details."""

    key: str
    name: str
    htmlDesc: str
    type: str
    severity: str
    examples: Optional[list[dict]] = None


class SonarQubeClient:
    """Client for SonarQube API."""

    def __init__(self, base_url: str = "https://sonarcloud.io", token: Optional[str] = None):
        """Initialize SonarQube client.
        
        Args:
            base_url: SonarQube server URL
            token: Authentication token (optional, reads from SONAR_TOKEN env var)
        """
        self.base_url = base_url.rstrip("/")
        self.token = token or os.getenv("SONAR_TOKEN")
        self.session = requests.Session()
        
        if self.token:
            self.session.auth = (self.token, "")

    def get_rule(self, rule_key: str) -> Optional[RuleDescription]:
        """Fetch rule details from SonarQube.
        
        Args:
            rule_key: Rule key (e.g., 'python:S1481')
            
        Returns:
            RuleDescription or None if not found
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/rules/show",
                params={"key": rule_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            
            rule_data = data.get("rule", {})
            return RuleDescription(
                key=rule_data.get("key", rule_key),
                name=rule_data.get("name", ""),
                htmlDesc=rule_data.get("htmlDesc", ""),
                type=rule_data.get("type", ""),
                severity=rule_data.get("severity", ""),
            )
        except Exception as e:
            print(f"Warning: Could not fetch rule {rule_key}: {e}")
            return None

    def search_rules(self, language: str = "py", query: str = "") -> list[RuleDescription]:
        """Search for rules.
        
        Args:
            language: Language key (e.g., 'py', 'js', 'java')
            query: Search query
            
        Returns:
            List of RuleDescription objects
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/rules/search",
                params={
                    "languages": language,
                    "q": query,
                    "ps": 100,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            
            rules = []
            for rule_data in data.get("rules", []):
                rules.append(RuleDescription(
                    key=rule_data.get("key", ""),
                    name=rule_data.get("name", ""),
                    htmlDesc=rule_data.get("htmlDesc", ""),
                    type=rule_data.get("type", ""),
                    severity=rule_data.get("severity", ""),
                ))
            
            return rules
        except Exception as e:
            print(f"Warning: Could not search rules: {e}")
            return []
