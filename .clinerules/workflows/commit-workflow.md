# GIT COMMIT WORKFLOW
===================

This document describes the modernized, tiered workflow to be followed when committing new changes to the GIT repository.

## WORKFLOW TIERS
================

### LIGHT COMMITS (Documentation, Minor Fixes)
- Documentation updates
- Comment improvements
- Minor bug fixes
- Configuration changes

**Required Steps**: Code Review (1) + Git Commit (6)

### STANDARD COMMITS (Features, Enhancements)
- New features
- Code refactoring
- API changes
- Database schema updates

**Required Steps**: Code Review (1) + Testing (4) + Git Commit (6)

### CRITICAL COMMITS (Security, Breaking Changes)
- Security-sensitive changes
- Breaking changes
- Major architectural updates
- Production hotfixes

**Required Steps**: All steps (1-6)

## WORKFLOW STEPS
===============

### 1. CODE REVIEW AND COMMENTS
   -------------------------
   - Review all code changes for clarity and maintainability
   - Add or update comments where necessary to explain:
     * Complex algorithms or logic
     * Function purposes and parameters
     * Important business rules or constraints
     * Any non-obvious implementation decisions
   - Ensure docstrings are present and accurate for all functions and classes
   - Verify that variable names are descriptive and self-documenting
   - **NEW**: Include peer review for changes >100 lines or critical functionality

### 2. AUTOMATED SECURITY ASSESSMENT
   ----------------------------------
   - **AUTOMATED CHECKS** (via pre-commit hooks):
     * Static code analysis (SonarQube, CodeQL)
     * Dependency vulnerability scanning (Snyk, npm audit)
     * Secret detection (GitLeaks, TruffleHog)
     * Basic security linting rules
   
   - **MANUAL ASSESSMENT** (for critical commits only):
     * Input validation weaknesses
     * Authentication and authorization flaws
     * Insecure data handling or storage
     * Cryptographic implementation weaknesses
     * Business logic security flaws
   
   - **COMPLIANCE CHECKS**:
     * Principle of least privilege
     * Defense in depth
     * Secure coding standards
     * Data encryption requirements
   
   - Document critical security issues with severity levels and remediation recommendations

### 3. PERFORMANCE AND OPTIMIZATION ANALYSIS
   ------------------------------------------
   - **AUTOMATED PERFORMANCE CHECKS**:
     * Run performance benchmarks for critical paths
     * Memory usage analysis
     * CPU impact assessment
     * Database query performance (if applicable)
   
   - **OPTIMIZATION OPPORTUNITIES**:
     * Algorithm optimization
     * Memory usage reduction
     * Code simplification
     * Better error handling
     * Improved readability
   
   - **PERFORMANCE THRESHOLDS**:
     * No >20% performance regression without approval
     * Memory usage increases require justification
     * Database queries must meet performance SLAs
   
   - Present optimization suggestions to the developer for approval
   - Document the reasoning behind each optimization

### 4. AUTOMATED TESTING AND VALIDATION
   ------------------------------------
   - **AUTOMATED TEST EXECUTION**:
     * Run complete unit test suite
     * Execute integration tests
     * Perform code coverage analysis
     * Run end-to-end tests (if applicable)
   
   - **TEST UPDATE REQUIREMENTS**:
     * Automatic updates allowed for:
       - New test cases for new functionality
       - Test data updates
       - Non-breaking assertion updates
     * Manual approval required for:
       - Test deletion or disabling
       - Major test logic changes
       - Reducing test coverage
   
   - **COVERAGE REQUIREMENTS**:
     * Maintain minimum 80% code coverage
     * New code must have 90% coverage
     * Critical paths require 100% coverage
   
   - **CI/CD INTEGRATION**:
     * All automated checks must pass
     * Green build status required
     * No failing tests allowed

### 5. AUTOMATED RELEASE NOTES AND VERSIONING
   -------------------------------------------
   - **CONVENTIONAL COMMITS** (required format):
     * `feat:` - New features (MINOR version bump)
     * `fix:` - Bug fixes (PATCH version bump)
     * `docs:` - Documentation changes
     * `style:` - Code style changes
     * `refactor:` - Code refactoring
     * `test:` - Test additions/modifications
     * `chore:` - Build process or auxiliary tool changes
     * `BREAKING CHANGE:` - Breaking changes (MAJOR version bump)
   
   - **AUTOMATED CHANGELOG GENERATION**:
     * Maintain CHANGELOG.md file
     * Auto-generate from conventional commits
     * Include migration guides for breaking changes
   
   - **SEMANTIC VERSIONING**:
     * MAJOR: Breaking changes or significant new functionality
     * MINOR: New features that are backward compatible
     * PATCH: Bug fixes and minor improvements
   
   - **DOCUMENTATION REQUIREMENTS**:
     * API documentation updates for interface changes
     * User documentation for new features
     * Architecture Decision Records (ADRs) for significant changes

### 6. GIT COMMIT EXECUTION AND CI/CD
   -----------------------------------
   - **PRE-COMMIT VALIDATION**:
     * Run automated security checks
     * Execute linting and formatting
     * Validate commit message format
     * Check for secrets or sensitive data
   
   - **COMMIT PROCESS**:
     * Stage all modified files using `git add`
     * Create descriptive commit message following conventional commits
     * Execute the commit with: `git commit -m "type: description"`
     * Verify commit was successful and note the commit hash
   
   - **POST-COMMIT VALIDATION**:
     * CI/CD pipeline execution
     * Automated testing in clean environment
     * Security scanning in pipeline
     * Performance regression testing
   
   - **BRANCH PROTECTION**:
     * Require status checks to pass
     * Require up-to-date branches
     * Require review for protected branches

## COMMIT MESSAGE GUIDELINES
===========================
- **Format**: `type(scope): description`
- **Examples**:
  - `feat(auth): add OAuth2 integration`
  - `fix(api): resolve memory leak in user service`
  - `docs(readme): update installation instructions`
  - `refactor(database): optimize query performance`
- Use imperative mood ("Add feature" not "Added feature")
- Keep description under 50 characters
- Include body for complex changes
- Reference issues: `Closes #123`

## QUALITY CHECKLIST
===================
Before committing, ensure:

### Code Quality
□ Code has been reviewed and commented appropriately
□ Follows project coding standards and style guide
□ No debugging code or console.log statements remain
□ Variable names are descriptive and self-documenting

### Security & Performance
□ Automated security checks have passed
□ No secrets or sensitive information exposed
□ Performance benchmarks meet requirements
□ No significant performance regressions introduced

### Testing & Validation
□ All automated tests pass successfully
□ Code coverage requirements met
□ Integration tests validate changes
□ CI/CD pipeline shows green status

### Documentation & Communication
□ Documentation updated for user-facing changes
□ API documentation reflects interface changes
□ Commit message follows conventional format
□ Breaking changes properly documented

### Process Compliance
□ Appropriate workflow tier followed
□ Required approvals obtained (if applicable)
□ Branch protection rules satisfied
□ Release notes automatically generated

## AUTOMATION TOOLS INTEGRATION
==============================

### Required Tools
- **Static Analysis**: SonarQube, ESLint, Pylint
- **Security Scanning**: Snyk, CodeQL, GitLeaks
- **Testing**: Jest, PyTest, Selenium (E2E)
- **Performance**: Lighthouse, JMeter, custom benchmarks
- **CI/CD**: GitHub Actions, Jenkins, GitLab CI

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pre-commit install

# Hooks include:
# - Code formatting (Prettier, Black)
# - Linting (ESLint, Pylint)
# - Security scanning (GitLeaks)
# - Test execution (unit tests)
# - Commit message validation
```

## WORKFLOW DECISION MATRIX
==========================

| Change Type | Tier | Steps Required | Approval Needed | Automation Level |
|-------------|------|----------------|-----------------|------------------|
| Documentation | Light | 1, 6 | None | High |
| Bug Fix | Light/Standard | 1, 4, 6 | None | High |
| New Feature | Standard | 1, 4, 6 | Code Review | Medium |
| API Change | Standard | 1, 4, 5, 6 | Code Review | Medium |
| Security Fix | Critical | 1-6 | Security Review | Low |
| Breaking Change | Critical | 1-6 | Architecture Review | Low |

## EMERGENCY PROCEDURES
======================

### Hotfix Process
1. Create hotfix branch from main
2. Apply minimal fix with full workflow
3. Fast-track review process
4. Deploy with monitoring
5. Follow up with comprehensive fix

### Rollback Process
1. Identify problematic commit
2. Create revert commit
3. Follow standard workflow for revert
4. Monitor system stability
5. Plan proper fix implementation

## NOTES
========
- Workflow tier is determined by change impact and risk level
- Automation reduces manual overhead while maintaining quality
- Critical changes always require full workflow regardless of size
- Performance and security are non-negotiable requirements
- Documentation is part of the development process, not an afterthought
- CI/CD integration ensures consistent quality across all environments
- Regular workflow review and improvement based on team feedback
