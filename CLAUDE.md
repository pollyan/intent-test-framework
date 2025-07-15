# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the Intent Test Framework - an AI-driven web automation testing platform that provides complete WebUI interface for test case management, execution monitoring, and result analysis. The system uses MidSceneJS for AI-powered visual testing and supports natural language test descriptions.

## Development Commands

### Setup and Installation
```bash
# Setup development environment
python scripts/setup_dev_env.py

# Install Python dependencies
pip install -r requirements.txt
pip install -r web_gui/requirements.txt

# Install Node.js dependencies  
npm install

# Setup environment variables
cp .env.example .env
# Edit .env with your AI API keys
```

### Running the Application
```bash
# Start MidScene server (AI engine)
node midscene_server.js

# Start Web GUI application
python web_gui/run_enhanced.py

# Alternative: Start enhanced web app
python web_gui/app_enhanced.py
```

### Development Tools
```bash
# Run code quality check
python scripts/quality_check.py

# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_models.py -v

# Run Node.js related tests
npm test
```

### Local Proxy Server
```bash
# Start local proxy server for AI testing
python start_midscene_server.py
```

## Architecture

### Core Components

1. **Web GUI Layer** (`web_gui/`)
   - `app.py` / `app_enhanced.py`: Main Flask application
   - `api_routes.py`: API endpoints
   - `models.py`: SQLAlchemy database models
   - `templates/`: HTML templates
   - `services/ai_enhanced_parser.py`: Natural language parsing

2. **AI Engine Layer**
   - `midscene_python.py`: Python wrapper for MidSceneJS
   - `midscene_server.js`: Node.js server for AI operations
   - Integrates with MidSceneJS library for visual AI testing

3. **Database Layer**
   - PostgreSQL for production (Supabase)
   - SQLite for development
   - Models: TestCase, ExecutionHistory, Template, StepExecution

4. **Cloud Deployment**
   - `api/index.py`: Vercel serverless entry point
   - `vercel.json`: Vercel deployment configuration
   - Generates downloadable local proxy packages

### Data Flow

1. **Test Creation**: User creates test cases via WebUI → Stored in database
2. **Natural Language Processing**: AI parses natural language descriptions into structured steps
3. **Test Execution**: MidSceneJS AI engine executes tests in browser
4. **Real-time Updates**: WebSocket connections provide live execution status
5. **Results Storage**: Execution results, screenshots, and logs stored in database

### Key Architectural Patterns

- **Microservices**: Flask web app + Node.js AI server
- **Event-driven**: WebSocket for real-time communication
- **AI-first**: All element interactions use AI vision models
- **Hybrid deployment**: Local development + cloud distribution

## Test Structure

Test cases are structured as JSON with steps containing:
- `action`: Type of action (navigate, ai_input, ai_tap, ai_assert, etc.)
- `params`: Action-specific parameters
- `description`: Human-readable step description

Example test case:
```json
{
  "name": "Search Test",
  "steps": [
    {
      "action": "navigate",
      "params": {"url": "https://example.com"},
      "description": "Navigate to example.com"
    },
    {
      "action": "ai_input", 
      "params": {"text": "search query", "locate": "search box"},
      "description": "Enter search query"
    },
    {
      "action": "ai_tap",
      "params": {"locate": "search button"},
      "description": "Click search button"
    },
    {
      "action": "ai_assert",
      "params": {"condition": "search results are displayed"},
      "description": "Verify search results appear"
    }
  ]
}
```

## Database Schema

### Core Tables
- `test_cases`: Test case definitions and metadata
- `execution_history`: Test execution records
- `step_executions`: Individual step execution details
- `templates`: Reusable test templates

### Key Relationships
- TestCase → ExecutionHistory (1:N)
- ExecutionHistory → StepExecution (1:N)
- Template → TestCase (1:N)

## Environment Configuration

### Required Environment Variables
```env
# AI Service Configuration
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# Database Configuration  
DATABASE_URL=postgresql://user:pass@host:port/db

# Application Settings
DEBUG=false
SECRET_KEY=your_secret_key
```

### AI Model Support
- Primary: Qwen VL (Alibaba Cloud DashScope)
- Alternative: GPT-4V (OpenAI)
- Configured via `MIDSCENE_MODEL_NAME` and `OPENAI_BASE_URL`

## Cloud Deployment

### Vercel Deployment
- Entry point: `api/index.py`
- Serverless function generates local proxy packages
- Automatic deployment from GitHub pushes

### Local Proxy Distribution
- Users download proxy packages from cloud interface
- Packages include MidSceneJS server + dependencies
- Self-contained for local AI testing execution

## Development Guidelines

### Code Quality
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Comprehensive docstrings for all public functions
- Error handling with custom exception classes

### Testing
- Unit tests in `tests/` directory
- Integration tests for API endpoints
- AI functionality tests with mock responses

### Commit Standards
```
<type>(<scope>): <subject>

Examples:
feat(webui): add screenshot history feature
fix(api): resolve test case deletion error
docs(readme): update installation instructions
```

### File Organization
- Python files: `snake_case`
- JavaScript files: `camelCase`
- HTML templates: `template_name.html`
- Configuration: Environment variables over hardcoded values

## Local Proxy Package Management

The system generates downloadable local proxy packages containing:
- `midscene_server.js`: AI testing server
- `package.json`: Dependencies including @playwright/test, axios
- `start.sh/.bat`: Smart startup scripts with dependency checking
- Enhanced error handling and auto-repair functionality

Users download from https://intent-test-framework.vercel.app/local-proxy for the latest version.