# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Intent Test Framework: an AI-driven web automation testing platform with a Flask Web UI and a Node.js AI engine (MidSceneJS) for visual/NL-based testing. Real-time status via Socket.IO; layered architecture with API-first design.
- Two intelligent agents: Requirements Analysis Agent (Alex Chen) and Test Analysis Agent (Lisa Song) for structured workflow guidance.
- See README.md for a fuller feature list and quickstart.

Conventions and important rules (from CLAUDE.md and repo)
- Primary language in docs/UI: Chinese (中文)。
- **NEVER hardcode configurations**: All configurations must come from environment variables (.env), database, or config files. No hardcoded API keys, URLs, model names, or business logic in source code.
- Architecture constraints: service-layer abstraction (web_gui/services/*); no mock/placeholder business logic in production; API-first with modular blueprints; database access via DatabaseService; keep UI consistent with minimal-preview patterns.
- Testing policy: API integration tests are the focus; do not add unit tests unless explicitly required.

Common commands
- Environment setup
  - Python deps: use your virtualenv of choice, then install:
    ```bash path=null start=null
    pip install -r requirements.txt
    ```
  - Node deps (for proxy/Jest tests and MidScene server):
    ```bash path=null start=null
    npm install
    ```
  - Optional: install Playwright browsers if needed by your platform
    ```bash path=null start=null
    python -m playwright install
    ```
  - One-shot helper scripts (if you prefer scripted setup):
    ```bash path=null start=null
    bash scripts/install-test-deps.sh
    python scripts/setup_dev_env.py
    cp .env.example .env  # then edit .env for your AI keys/models
    ```

- Run the application locally
  - Start the Flask Web UI (templates/static baked into web_gui/):
    ```bash path=null start=null
    python web_gui/run_enhanced.py
    # UI: http://localhost:5001
    # API: http://localhost:5001/api/
    # Requirements Agent: http://localhost:5001/requirements
    # Test Agent: accessible through testcase management UI
    ```
  - Start the AI engine server (Node/MidSceneJS) when required by AI steps:
    ```bash path=null start=null
    node midscene_server.js
    ```
  - Health and convenience: there is a helper dev.sh, but it references start.py which may not exist in this tree; prefer the explicit commands above.

- Tests (pytest; API integration focused)
  - Run full suite:
    ```bash path=null start=null
    pytest -v
    ```
  - Run tests with coverage:
    ```bash path=null start=null
    pytest --cov=web_gui --cov-report=term --cov-report=html
    ```
  - Run a single test file / test / keyword:
    ```bash path=null start=null
    pytest tests/api/test_testcase_api.py -v
    pytest tests/api/test_testcase_api.py::TestClassName::test_method -v
    pytest -k "dashboard and not slow" -v
    ```
  - Markers and config: see pytest.ini (strict markers, asyncio auto, python>=3.11).

- Proxy/Node-side tests (Jest) if you modify midscene_service or proxy logic:
  ```bash path=null start=null
  npm run test:proxy
  npm run test:proxy:watch
  npm run test:proxy:coverage
  ```

- Lint/format and quality
  - Use the repo’s quality gate script:
    ```bash path=null start=null
    python scripts/quality_check.py --fix
    ```
  - Under the hood, the project uses black/flake8; prefer the script to keep consistency. Performance benchmarks are available:
    ```bash path=null start=null
    python scripts/benchmark.py --parallel --save
    ```

Key architecture and flow
- Web application (Flask)
  - Entry: web_gui/app_enhanced.py exposes create_app; static and templates under web_gui/static and web_gui/templates.
  - Blueprints: registered via web_gui/api/base.register_blueprints; endpoints include testcases, executions, statistics, dashboard, requirements, etc.
  - Database: SQLAlchemy configured in web_gui/app_enhanced.py. Models in web_gui/models.py. Engine options adapt to Postgres vs SQLite.
  - Realtime: web_gui/core/extensions initializes Socket.IO; execution lifecycle events emitted (execution_started, step_completed, execution_completed).

- Services (business logic)
  - ExecutionService (web_gui/services/execution_service.py)
    - Orchestrates async execution threads, persists ExecutionHistory, StepExecution, updates step counts and emits realtime events.
    - Integrates AI service for step execution; honors headless/browser modes; supports variable resolution with get_variable_manager.
  - AI services
    - get_ai_service and ai_step_executor integrate with MidSceneJS via the Node server and the Python bridge (midscene_python.py).
  - Variable resolution
    - variable_resolver_service supports ${var} syntax, output_variable propagation between steps.
  - DatabaseService abstracts DB access; keep controllers thin and defer logic to services.

- AI engine and bridge
  - Node server: midscene_server.js exposes AI/vision capabilities used by the executor.
  - Python bridge: midscene_python.py for Python↔Node interoperability.

- Intelligent Agents System
  - Requirements Analysis Agent (Alex Chen): web_gui/services/requirements_ai_service.py provides IntelligentAssistantService for structured requirements clarification.
    - Four-step methodology: Elevator Pitch → User Persona → User Journey → Business Requirements Document (BRD)
    - Persona bundle: intelligent-requirements-analyzer/dist/intelligent-requirements-analyst-bundle.txt
  - Test Analysis Agent (Lisa Song): Same service architecture, focused on test strategy and test case generation.
    - Four-step methodology: Test Scope Analysis → Test Strategy Design → Test Case Generation → Test Plan Document (TPD)
    - Persona bundle: intelligent-requirements-analyzer/dist/testmaster-song-bundle.txt
  - Agent configuration: intelligent-requirements-analyzer/config.yaml defines document locations and workflow settings.

- Testing structure
  - Focus: API integration tests under tests/api/ (health, dashboard, statistics, requirements, testcases, executions, error scenarios, midscene endpoints).
  - Global pytest config in pytest.ini; fixtures in tests/conftest.py and tests/api/conftest.py.
  - Migration validations: test_migrations.py plus scripts/validate_migration*.py.

Important repository files to know
- README.md: Quickstart (clone, env setup, start MidScene server and Flask UI, open http://localhost:5001), architecture diagram, sample natural-language steps, contribution and CI badges.
- CLAUDE.md: Enforces service-layer abstraction, no mocks in production, API integration-first testing strategy, minimal-preview UI standards.
- requirements*.txt, package.json: authoritative dependencies and Node test scripts.
- scripts/: rich operational helpers (quality_check.py, benchmark.py, migrate_to_supabase.py, test-local.sh, install-test-deps.sh, init_default_config.py, validate_migration.py, etc.). Prefer these when available.
- intelligent-requirements-analyzer/: Contains agent system with persona bundles in dist/ and workflow configuration in config.yaml.

Practical tips bound to this codebase
- Ports: Flask defaults to 5001; MidScene Node server commonly on 3001 (see dev.sh defaults). Adjust via environment if needed.
- Databases: SQLite by default if DATABASE_URL is unset; Postgres supported with pool tuning. For development, SQLite simplifies setup.
- Realtime UI: if you change execution event payloads in services, update any frontend consumers under web_gui/templates/static accordingly.
- Agent system: Both agents (Alex/Song) use the same IntelligentAssistantService but with different persona bundles. Agent sessions are managed via RequirementsSession and RequirementsMessage models.
- Agent UI access: Requirements analyzer at /requirements, config management at /config-management. See minimal-preview/ for UI design patterns.

Configuration Management (Anti-Hardcoding)
- **Environment Variables**: All configurations must be defined in .env file
  - API keys: OPENAI_API_KEY
  - Base URLs: OPENAI_BASE_URL  
  - Model names: MIDSCENE_MODEL_NAME
  - Config names: DEFAULT_AI_CONFIG_NAME
- **Database-First**: scripts/init_default_config.py reads from environment variables, never overwrites existing user configurations
- **No Hardcoded Values**: API keys, URLs, model names must never appear in source code
- **Configuration Priority**: Database config > Environment variables > Defaults (fail if missing required values)

Intelligent Agents Usage
- Requirements Analysis Agent (Alex Chen) - 4-step requirements clarification:
  - Access: http://localhost:5001/requirements
  - Commands: *start (full workflow), *elevator (step 1), *persona (step 2), *journey (step 3), *help
  - Output: Structured BRD (Business Requirements Document) with progress tracking
- Test Analysis Agent (Lisa Song) - 4-step test analysis:
  - Commands: *start (full workflow), *scope (step 1), *strategy (step 2), *cases (step 3), *help
  - Output: Comprehensive TPD (Test Plan Document) with test case generation
- Both agents maintain session state via RequirementsSession/RequirementsMessage models
- Agent personas loaded from intelligent-requirements-analyzer/dist/ bundle files

Appendix: single-command flows
- Minimal dev bring-up (two terminals):
  ```bash path=null start=null
  # Terminal A (Flask)
  python web_gui/run_enhanced.py
  # Terminal B (AI engine)
  node midscene_server.js
  ```
- Full test and quality before committing:
  ```bash path=null start=null
  pytest -v
  python scripts/quality_check.py --fix
  pytest --cov=web_gui --cov-report=term --cov-report=html
  ```

