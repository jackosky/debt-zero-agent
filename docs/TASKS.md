# debt-zero-agent: Task Breakdown

## Phase 1: Foundation
- [x] Add dependencies to `pyproject.toml`
- [x] Create package structure (empty `__init__.py` files)
- [x] **Review**: Verify dependencies install correctly

---

## Phase 2: Models
- [x] Create `models/issue.py` - SonarQube Pydantic models
- [x] Create `models/fix.py` - Fix result models
- [x] Write unit tests for models
- [x] **Review**: Validate models parse sample SonarQube response

---

## Phase 3: Validation & AST
- [ ] Create `validation/ast_validator.py` - Python syntax validation
- [ ] Create `validation/tree_sitter.py` - Multi-lang syntax check
- [ ] Create `validation/locator.py` - AST-based issue localization
- [ ] Write unit tests for validation module
- [ ] **Review**: Test locator with real code samples

---

## Phase 4: Tools
- [ ] Create `tools/file_reader.py`
- [ ] Create `tools/code_search.py`
- [ ] Create `tools/file_writer.py`
- [ ] Create `tools/diff_tool.py`
- [ ] Write unit tests for tools
- [ ] **Review**: Verify tools work with sample repo

---

## Phase 5: Agent Core
- [ ] Create `agent/llm.py` - LLM factory
- [ ] Create `agent/state.py` - Agent state model
- [ ] Create `prompts/templates.py`
- [ ] Create `agent/nodes.py` - Node functions
- [ ] Create `agent/graph.py` - LangGraph workflow
- [ ] Write unit tests for nodes
- [ ] **Review**: Test graph with mocked LLM

---

## Phase 6: CLI & Integration
- [ ] Update `cli.py` with argparse
- [ ] Wire up agent invocation
- [ ] Write CLI argument tests
- [ ] **Review**: End-to-end dry-run test

---

## Phase 7: Final Validation
- [ ] Integration test with real SonarQube issues
- [ ] Benchmark OpenAI vs Anthropic
- [ ] **Review**: Document results in walkthrough
