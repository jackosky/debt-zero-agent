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
- [x] Create `validation/ast_validator.py` - Python syntax validation
- [x] Create `validation/tree_sitter.py` - Multi-lang syntax check
- [x] Create `validation/locator.py` - AST-based issue localization
- [x] Write unit tests for validation module
- [x] **Review**: Test locator with real code samples

---

## Phase 4: Tools
- [x] Create `tools/file_reader.py`
- [x] Create `tools/code_search.py`
- [x] Create `tools/file_writer.py`
- [x] Create `tools/diff_tool.py`
- [x] Write unit tests for tools
- [x] **Review**: Verify tools work with sample repo

---

## Phase 5: Agent Core
- [x] Create `agent/llm.py` - LLM factory (OpenAI/Anthropic)
- [x] Create `agent/state.py` - Agent state TypedDict
- [x] Create `prompts/templates.py` - Prompt templates
- [x] Create `agent/nodes.py` - LangGraph nodes
- [x] Create `agent/graph.py` - Workflow definition
- [x] Write unit tests for agent components
- [x] **Review**: Verify all tests pass (37/37)

---

## Phase 6: CLI Integration
- [x] Update `cli.py` with argument parsing
- [x] Wire agent workflow to CLI
- [x] Add issue loading from JSON
- [x] Write CLI tests
- [x] **Review**: Test CLI help and basic invocationest

---

## Phase 7: Final Validation
- [ ] Integration test with real SonarQube issues
- [ ] Benchmark OpenAI vs Anthropic
- [ ] **Review**: Document results in walkthrough
