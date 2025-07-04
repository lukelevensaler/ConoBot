# ConoBot

> Advanced AI-powered assistant with integrated machine learning capabilities and transformers support.

## Overview

ConoBot is a sophisticated AI development platform that combines cutting-edge natural language processing with robust machine learning infrastructure. Built with modern Python tooling and comprehensive CI/CD automation.

## Features

- **AI Core Architecture**: Modular agentic sequencing system
- **Transformers Integration**: Local transformers library for advanced NLP tasks  
- **Modern Frontend**: PyQt-based user interface with oceanic themes
- **Workflow Management**: Automated middleware for seamless operations
- **Development Tools**: Comprehensive testing and quality assurance

## Quick Start

### Prerequisites

- Python 3.9+
- UV package manager
- Git with LFS support

### Installation

```bash
# Clone the repository
git clone https://github.com/lukelevensaler/ConoBot.git
cd ConoBot

# Install dependencies using UV
uv venv
uv pip install -e .

# Run the application
python frontend/main.py
```

## Development

### Project Structure

```
ConoBot/
├── ai_cores/           # AI architecture and sequencing
├── frontend/           # PyQt user interface
├── middleware/         # Configuration and workflow management
├── transformers/       # Local transformers library (no .txt files)
├── assets/            # UI assets and themes
└── tests/             # Test suites
```

### Package Management

This project uses [UV](https://github.com/astral-sh/uv) for fast, reliable Python package management:

```bash
# Install dependencies
uv pip install -e .

# Add new packages
uv add package-name

# Development dependencies
uv pip install pytest pytest-xdist ruff black mypy
```

### Testing

The project includes comprehensive test suites with parallel execution:

```bash
# Run all tests
python -m pytest

# Run specific test suites
python -m pytest -m "not slow"              # Core tests
python -m pytest -m "integration"           # Integration tests  
python -m pytest -m "slow"                  # Comprehensive tests
python -m pytest -m "transformers"          # Transformers tests

# Parallel execution
python -m pytest -n 4                       # 4 parallel workers
```

### Code Quality

Automated code quality checks ensure consistent, maintainable code:

```bash
# Linting
ruff check .

# Formatting  
black .

# Type checking
mypy --ignore-missing-imports .
```

## CI/CD Pipeline

### GitHub Actions Workflow

The project uses a consolidated CI/CD pipeline that runs automatically on:

- Push to `main`, `develop`, or `release/*` branches
- Pull requests to `main` or `develop`
- Manual workflow dispatch with test suite selection

### Test Automation

**Quality Checks:**
- Code linting with ruff
- Format checking with black  
- Type checking with mypy

**Security Scanning:**
- Vulnerability scanning with Trivy
- SARIF report upload to GitHub Security

**Test Execution:**
- Core tests (fast, 4 parallel workers)
- Integration tests (with pipeline testing enabled)
- Slow tests (comprehensive coverage) 
- Transformers-specific tests (ML model testing)

**Coverage Reporting:**
- Code coverage with pytest-cov
- Upload to Codecov for tracking

### Deployment

**Publishing Pipeline:**
- Automated package building with UV
- Version management and tagging
- Distribution to package repositories

## Architecture

### AI Cores

The `ai_cores` directory contains the core AI functionality:

- **Agentic Sequencing**: Advanced AI agent coordination
- **LLM Integration**: Large language model fine-tuning capabilities

### Middleware

Configuration utilities and workflow management:

- **Configuration Utils**: Centralized settings management
- **Workflow Engine**: Process automation and orchestration

### Transformers Library

Local installation of the transformers library optimized for development:

- Cleaned of unnecessary .txt files to reduce bloat
- Integrated with local development environment
- Supports fine-tuning and model customization

## Git LFS

Large files are managed with Git LFS for efficient repository operations:

- Model files (`.bin`, `.pth`, `.h5`)
- Compiled libraries (`.so`, `.dll`)
- Archive files (`.zip`, `.tar`)
- Package lock files (`uv.lock`)

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate tests
4. Ensure all CI checks pass
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Include type hints for all functions
- Write comprehensive tests for new features
- Document public APIs with docstrings

## License

This project is licensed under the terms specified in the LICENSE file.

## Support

For questions, issues, or contributions, please use the GitHub issue tracker or submit pull requests.