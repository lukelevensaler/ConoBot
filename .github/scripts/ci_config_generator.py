#!/usr/bin/env python3
"""
Unified CI Configuration Generator for ConoBot
Consolidates CircleCI and GitHub Actions configurations into a single CI system.
"""

import os
import yaml
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class TestJob:
    """Unified test job configuration that can generate GitHub Actions workflows"""
    name: str
    python_version: str = "3.9"
    os_matrix: List[str] = None
    install_deps: List[str] = None
    test_markers: Optional[str] = None
    parallel_workers: int = 1
    timeout_minutes: int = 30
    environment_vars: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.os_matrix is None:
            self.os_matrix = ["ubuntu-latest"]
        if self.install_deps is None:
            self.install_deps = ["uv pip install -e .", "uv pip install pytest pytest-xdist"]
        if self.environment_vars is None:
            self.environment_vars = {}

# Define common environment variables from CircleCI config
COMMON_ENV = {
    "OMP_NUM_THREADS": "1",
    "TRANSFORMERS_IS_CI": "true", 
    "PYTEST_TIMEOUT": "120",
    "RUN_PIPELINE_TESTS": "false",
    "PYTHONUNBUFFERED": "1"
}

# Common pytest options for all test jobs
PYTEST_BASE_ARGS = [
    "--maxfail=5",
    "--tb=short", 
    "--strict-markers",
    "--disable-warnings",
    "--color=yes"
]

# Test job definitions based on CircleCI configuration
TEST_JOBS = [
    TestJob(
        name="core-tests",
        test_markers="not slow and not integration",
        parallel_workers=4,
        environment_vars={**COMMON_ENV}
    ),
    TestJob(
        name="integration-tests", 
        test_markers="integration",
        parallel_workers=2,
        timeout_minutes=60,
        environment_vars={**COMMON_ENV, "RUN_PIPELINE_TESTS": "true"}
    ),
    TestJob(
        name="slow-tests",
        test_markers="slow", 
        parallel_workers=1,
        timeout_minutes=90,
        environment_vars={**COMMON_ENV}
    ),
    TestJob(
        name="transformers-tests",
        install_deps=[
            "uv pip install -e .",
            "uv pip install torch torchvision transformers",
            "uv pip install pytest pytest-xdist pytest-timeout"
        ],
        test_markers="transformers",
        parallel_workers=2,
        timeout_minutes=45,
        environment_vars={**COMMON_ENV}
    )
]

def generate_github_actions_workflow():
    """Generate a consolidated GitHub Actions workflow file"""
    
    workflow = {
        "name": "Consolidated CI/CD Pipeline",
        "on": {
            "push": {
                "branches": ["main", "develop", "release/*"],
                "paths": [
                    "**/*.py",
                    "pyproject.toml", 
                    "requirements*.txt",
                    ".github/workflows/**"
                ]
            },
            "pull_request": {
                "branches": ["main", "develop"],
                "paths": [
                    "**/*.py",
                    "pyproject.toml",
                    "requirements*.txt"
                ]
            },
            "workflow_dispatch": {
                "inputs": {
                    "test_suite": {
                        "description": "Test suite to run",
                        "required": True,
                        "default": "all",
                        "type": "choice",
                        "options": ["all", "core", "integration", "slow", "transformers"]
                    }
                }
            }
        },
        "env": {
            "PYTHON_VERSION": "3.9",
            "UV_CACHE_DIR": "/tmp/.uv-cache"
        },
        "concurrency": {
            "group": "${{ github.workflow }}-${{ github.head_ref || github.run_id }}",
            "cancel-in-progress": True
        },
        "jobs": {}
    }
    
    # Quality checks job
    workflow["jobs"]["quality-checks"] = {
        "name": "Code Quality & Linting",
        "runs-on": "ubuntu-latest",
        "steps": [
            {"name": "Checkout code", "uses": "actions/checkout@v4"},
            {"name": "Set up Python", "uses": "actions/setup-python@v4", 
             "with": {"python-version": "${{ env.PYTHON_VERSION }}"}},
            {"name": "Install UV", "run": "curl -LsSf https://astral.sh/uv/install.sh | sh && echo '$HOME/.cargo/bin' >> $GITHUB_PATH"},
            {"name": "Create virtual environment", "run": "uv venv"},
            {"name": "Install dependencies", "run": "uv pip install -e . && uv pip install ruff black mypy"},
            {"name": "Run ruff linting", "run": "ruff check ."},
            {"name": "Run black formatting check", "run": "black --check ."},
            {"name": "Run type checking", "run": "mypy --ignore-missing-imports ."}
        ]
    }
    
    # Security checks job
    workflow["jobs"]["security-checks"] = {
        "name": "Security Scanning",
        "runs-on": "ubuntu-latest", 
        "steps": [
            {"name": "Checkout code", "uses": "actions/checkout@v4"},
            {"name": "Run Trivy vulnerability scanner", 
             "uses": "aquasecurity/trivy-action@master",
             "with": {
                 "scan-type": "fs",
                 "scan-ref": ".",
                 "format": "sarif",
                 "output": "trivy-results.sarif"
             }},
            {"name": "Upload Trivy scan results", 
             "uses": "github/codeql-action/upload-sarif@v2",
             "with": {"sarif_file": "trivy-results.sarif"}}
        ]
    }
    
    # Generate test jobs
    for job in TEST_JOBS:
        job_config = {
            "name": f"Test: {job.name}",
            "runs-on": "${{ matrix.os }}",
            "needs": ["quality-checks"],
            "if": "${{ github.event.inputs.test_suite == 'all' || github.event.inputs.test_suite == '" + job.name.split('-')[0] + "' || github.event.inputs.test_suite == '' }}",
            "strategy": {
                "fail-fast": False,
                "matrix": {
                    "os": job.os_matrix,
                    "python-version": [job.python_version]
                }
            },
            "timeout-minutes": job.timeout_minutes,
            "env": job.environment_vars,
            "steps": [
                {"name": "Checkout code", "uses": "actions/checkout@v4"},
                {"name": "Set up Python ${{ matrix.python-version }}", 
                 "uses": "actions/setup-python@v4",
                 "with": {"python-version": "${{ matrix.python-version }}"}},
                {"name": "Cache UV dependencies", 
                 "uses": "actions/cache@v3",
                 "with": {
                     "path": "${{ env.UV_CACHE_DIR }}",
                     "key": "${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml', '**/requirements*.txt') }}"
                 }},
                {"name": "Install UV", "run": "curl -LsSf https://astral.sh/uv/install.sh | sh && echo '$HOME/.cargo/bin' >> $GITHUB_PATH"},
                {"name": "Create virtual environment", "run": "uv venv"},
                {"name": "Install dependencies", "run": " && ".join(job.install_deps)},
                {"name": "Show installed packages", "run": "uv pip list"},
                {"name": "Create test results directory", "run": "mkdir -p test-results"},
                {"name": f"Run {job.name}", 
                 "run": f"python -m pytest {' '.join(PYTEST_BASE_ARGS)} -n {job.parallel_workers} --junitxml=test-results/junit.xml" + 
                        (f" -m '{job.test_markers}'" if job.test_markers else "") + " tests/"},
                {"name": "Upload test results", 
                 "uses": "actions/upload-artifact@v3",
                 "if": "always()",
                 "with": {
                     "name": f"test-results-{job.name}-${{{{ matrix.os }}}}-${{{{ matrix.python-version }}}}",
                     "path": "test-results/"
                 }}
            ]
        }
        
        workflow["jobs"][job.name.replace('-', '_')] = job_config
    
    # Coverage job
    workflow["jobs"]["coverage"] = {
        "name": "Code Coverage",
        "runs-on": "ubuntu-latest",
        "needs": [job.name.replace('-', '_') for job in TEST_JOBS],
        "if": "always()",
        "steps": [
            {"name": "Checkout code", "uses": "actions/checkout@v4"},
            {"name": "Set up Python", "uses": "actions/setup-python@v4", 
             "with": {"python-version": "${{ env.PYTHON_VERSION }}"}},
            {"name": "Install dependencies", "run": "curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH='$HOME/.cargo/bin:$PATH' && uv pip install coverage pytest-cov"},
            {"name": "Run coverage", "run": "python -m pytest --cov=. --cov-report=xml tests/"},
            {"name": "Upload coverage to Codecov", 
             "uses": "codecov/codecov-action@v3",
             "with": {"file": "./coverage.xml"}}
        ]
    }
    
    return workflow

def main():
    """Generate and save the consolidated workflow file"""
    workflow = generate_github_actions_workflow()
    
    output_file = ".github/workflows/consolidated-ci.yml"
    
    with open(output_file, 'w') as f:
        yaml.dump(workflow, f, default_flow_style=False, sort_keys=False, indent=2)
    
    print(f"✅ Generated consolidated CI workflow: {output_file}")
    print("📋 Features included:")
    print("  - Code quality checks (ruff, black, mypy)")
    print("  - Security scanning (Trivy)")
    print("  - Multiple test suites with parallel execution")
    print("  - Code coverage reporting")
    print("  - Cross-platform testing support")
    print("  - Artifact uploads for test results")

if __name__ == "__main__":
    main()
