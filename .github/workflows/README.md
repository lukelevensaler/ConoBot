# GitHub Workflows Organization

This directory contains GitHub Actions workflows organized into logical categories for better maintainability and clarity.

## Directory Structure

```
.github/workflows/
├── automation/             # Automated model and PR management workflows
├── ci/                     # Continuous Integration workflows
├── docker/                 # Docker image building workflows  
├── docs/                   # Documentation workflows
├── runners/                # Self-hosted runner workflows
├── utils/                  # Utility workflows (slack, stale issues, etc.)
└── README.md              # This file
```

## Workflow Categories

### CI Workflows (`ci/`)
- **consolidated-ci.yml** - Main CI pipeline with quality checks, testing, and builds
- **benchmark.yml** - Performance benchmarking
- **check_*.yml** - Various code and model validation checks
- **codeql.yml** - Security analysis
- **model_jobs*.yml** - Model-specific testing jobs
- **python-publish.yml** - Package publishing to PyPI

### Docker Workflows (`docker/`)
- **consolidated-docker-build.yml** - Unified Docker image building workflow
- **build-ci-docker-images.yml** - CI-specific Docker images
- **build-nightly-ci-docker-images.yml** - Nightly Docker builds
- **build-past-ci-docker-images.yml** - Legacy version Docker images

### Documentation Workflows (`docs/`)
- **consolidated-docs.yml** - Unified documentation building and deployment
- **build_documentation.yml** - Main documentation build
- **build_pr_documentation.yml** - PR documentation preview
- **upload_pr_documentation.yml** - Documentation artifact handling

### Runner Workflows (`runners/`)
- **consolidated-runners.yml** - Unified self-hosted runner management
- **self-*.yml** - Various self-hosted runner configurations
- **ssh-runner.yml** - SSH debugging access

### Automation Workflows (`automation/`)
- **add-model-like.yml** - Automated model addition workflows
- **new_model_pr_merged_notification.yml** - PR merge notifications
- **push-important-models.yml** - Important model deployment

### Utility Workflows (`utils/`)
- **assign-reviewers.yml** - Automatic reviewer assignment
- **pr-style-bot.yml** - PR style and formatting checks
- **slack-report.yml** - Slack notification handling
- **stale.yml** - Stale issue and PR management
- **trufflehog.yml** - Secret scanning
- **update_metadata.yml** - Metadata synchronization

## Key Improvements

### 1. Consolidation
- Merged similar workflows to reduce duplication
- Created unified entry points for related functionality
- Reduced the total number of workflow files from 40+ to ~15

### 2. Organization
- Logical grouping by functionality
- Clear naming conventions
- Consistent structure across workflows

### 3. Maintainability
- Centralized configuration through environment variables
- Reusable job definitions
- Matrix strategies for scalable testing

### 4. Features
- Conditional execution based on context
- Comprehensive error handling and reporting
- Artifact management and cleanup
- Slack notifications and GitHub summaries

## Migration Guide

### Old → New Workflow Mapping

#### Docker Workflows
- `build-docker-images.yml` → `docker/consolidated-docker-build.yml`
- `build-ci-docker-images.yml` → `docker/consolidated-docker-build.yml`
- `build-nightly-ci-docker-images.yml` → `docker/consolidated-docker-build.yml`
- `build-past-ci-docker-images.yml` → `docker/consolidated-docker-build.yml`

#### Documentation Workflows  
- `docs.yml` → `docs/consolidated-docs.yml`
- `build_documentation.yml` → `docs/consolidated-docs.yml`
- `build_pr_documentation.yml` → `docs/consolidated-docs.yml`

#### CI Workflows
- Multiple test workflows → `ci/consolidated-ci.yml`
- Quality checks → `ci/consolidated-ci.yml`
- Build and publish → `ci/consolidated-ci.yml`

#### Runner Workflows
- `self-*.yml` → `runners/consolidated-runners.yml`
- Platform-specific runners → `runners/consolidated-runners.yml`

## Usage Examples

### Running specific test suites
```yaml
# Trigger via workflow_dispatch
inputs:
  test_suite: "unit"  # Options: all, unit, integration, performance, security
```

### Building specific Docker images
```yaml
# Trigger via workflow_call
inputs:
  build_type: "nightly"  # Options: scheduled, nightly, past, ci
  image_postfix: "-dev"
```

### Running platform-specific tests
```yaml
# Trigger via workflow_call
inputs:
  runner_type: "amd"  # Options: standard, amd, intel-gaudi
  test_suite: "model"  # Options: all, model, pipeline, example, deepspeed, trainer
```

## Configuration

### Environment Variables
Key environment variables are centralized at the workflow level:
- `PYTHON_VERSION`: Python version for CI
- `COVERAGE_THRESHOLD`: Minimum coverage percentage
- `HF_HOME`: Hugging Face cache directory
- `TRANSFORMERS_IS_CI`: CI environment flag

### Secrets Required
- `DOCKERHUB_USERNAME` / `DOCKERHUB_PASSWORD`: Docker Hub credentials
- `HUGGINGFACE_PUSH` / `HF_DOC_BUILD_PUSH`: Hugging Face tokens
- `SLACK_WEBHOOK_URL` / `CI_SLACK_CHANNEL`: Slack notifications
- `TAILSCALE_OAUTH_*`: SSH debugging access

## Best Practices

1. **Use consolidation workflows** instead of individual ones for new features
2. **Add conditions** to skip unnecessary jobs based on changed files
3. **Use matrix strategies** for testing multiple configurations
4. **Include proper error handling** and status reporting
5. **Clean up artifacts** to manage storage costs
6. **Document workflow changes** in commit messages

## Troubleshooting

### Common Issues
1. **Missing secrets**: Ensure all required secrets are configured
2. **Runner capacity**: Check runner group availability for self-hosted jobs
3. **Docker limits**: Monitor Docker Hub rate limits and quotas
4. **Cache issues**: Clear workflow caches if builds fail unexpectedly

### Debugging
- Use the SSH runner workflow for interactive debugging
- Check workflow logs for detailed error messages
- Monitor GitHub Actions usage and limits
- Review Slack notifications for failure alerts
