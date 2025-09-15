# Git Commit Quality Workflow

A comprehensive guide for developers to ensure high-quality code commits that meet enterprise standards for security, maintainability, and reliability.

## Overview

This workflow ensures that every commit to the repository meets the highest quality standards through automated checks, code review processes, and static analysis. The workflow integrates seamlessly with existing CI/CD pipelines and provides clear guidance for developers at every step.

## Prerequisites

- Git repository with proper access permissions
- Development environment with required tools installed
- Access to SonarQube server (via MCP tools)
- Understanding of project coding standards and conventions

## Workflow Steps

### Phase 1: Pre-Development Setup

#### 1.1 Environment Preparation
```bash
# Ensure you have the latest code
git pull origin main

# Create a feature branch
git checkout -b feature/your-feature-name

# Verify development environment
./scripts/pre-commit-quality-check.sh --help
```

#### 1.2 Review Project Standards
- Check `README.md` for project-specific guidelines
- Review coding standards in `/docs` directory
- Understand the project's architecture and patterns
- Familiarize yourself with existing test coverage requirements

### Phase 2: Development and Local Testing

#### 2.1 Code Development
- Follow established coding patterns and conventions
- Write self-documenting code with clear variable and function names
- Add appropriate comments for complex business logic
- Ensure proper error handling and logging

#### 2.2 Unit Test Development
- Write unit tests for all new functionality
- Maintain minimum 80% code coverage threshold
- Follow the testing patterns established in the project
- Test edge cases and error conditions

**Testing Commands by Technology:**
```bash
# Python projects
python -m pytest --cov --cov-report=term-missing

# Node.js projects
npm test
npm run test:coverage

# Java projects
mvn test

# .NET projects
dotnet test
```

#### 2.3 Local Code Quality Checks
Run the comprehensive quality check script before committing:
```bash
./scripts/pre-commit-quality-check.sh [PROJECT_KEY]
```

This script performs:
- Unit test execution
- Code coverage verification
- Code style and linting checks
- Security vulnerability scanning
- SonarQube static analysis integration

### Phase 3: Code Review Process

#### 3.1 Self-Review Checklist
Before requesting peer review, ensure:

**Code Quality:**
- [ ] Code follows project conventions and style guides
- [ ] No hardcoded secrets, passwords, or API keys
- [ ] Proper error handling and logging implemented
- [ ] Code is readable and well-documented
- [ ] No debugging code or console.log statements left behind

**Testing:**
- [ ] All new code has corresponding unit tests
- [ ] Tests cover happy path, edge cases, and error conditions
- [ ] All tests pass locally
- [ ] Code coverage meets or exceeds project threshold (80%)

**Security:**
- [ ] No sensitive information exposed in code or logs
- [ ] Input validation implemented where necessary
- [ ] Authentication and authorization properly handled
- [ ] Dependencies are up-to-date and secure

**Performance:**
- [ ] Code is optimized for performance
- [ ] No obvious performance bottlenecks
- [ ] Database queries are efficient
- [ ] Memory usage is reasonable

#### 3.2 Peer Review Process

**For Reviewers:**
1. **Functional Review:**
   - Verify the code solves the intended problem
   - Check that requirements are fully implemented
   - Test the functionality locally if possible

2. **Code Quality Review:**
   - Assess code readability and maintainability
   - Verify adherence to coding standards
   - Check for potential bugs or logic errors
   - Suggest improvements for better design patterns

3. **Security Review:**
   - Look for security vulnerabilities
   - Verify proper input validation
   - Check for potential injection attacks
   - Ensure sensitive data is properly handled

4. **Performance Review:**
   - Identify potential performance issues
   - Review database queries and API calls
   - Check for memory leaks or inefficient algorithms

**Review Guidelines:**
- Provide constructive feedback with specific suggestions
- Focus on code quality, not personal preferences
- Ask questions to understand the developer's approach
- Suggest alternative solutions when appropriate
- Approve only when all concerns are addressed

### Phase 4: Static Code Analysis with SonarQube

#### 4.1 SonarQube Integration
The quality check script automatically integrates with SonarQube via MCP tools:

```bash
# Manual SonarQube analysis (if needed)
./scripts/pre-commit-quality-check.sh your-project-key
```

#### 4.2 SonarQube Quality Gates
Ensure your code passes all quality gates:

**Reliability:**
- Zero bugs in new code
- Zero vulnerabilities in new code
- Technical debt ratio < 5%

**Security:**
- Zero security hotspots in new code
- All security issues resolved or marked as false positive

**Maintainability:**
- Code smells density < 10 per 1000 lines
- Duplicated lines < 3%
- Cyclomatic complexity within acceptable limits

**Coverage:**
- Line coverage ≥ 80% on new code
- Branch coverage ≥ 70% on new code

#### 4.3 Addressing SonarQube Issues
When SonarQube identifies issues:

1. **Critical Issues (Bugs/Vulnerabilities):**
   - Must be fixed before commit
   - Cannot be marked as false positive without team lead approval

2. **Major Issues (Code Smells):**
   - Should be addressed in the current commit
   - Can be deferred only with proper justification and tracking

3. **Minor Issues:**
   - Address when possible
   - Can be deferred to future refactoring efforts

### Phase 5: Code Optimization and Standards Compliance

#### 5.1 Language-Specific Optimization

**Python:**
```bash
# Code formatting
black .
isort .

# Linting
flake8 .
pylint src/

# Type checking
mypy src/
```

**JavaScript/TypeScript:**
```bash
# Code formatting
npm run format
# or
prettier --write .

# Linting
npm run lint
# or
eslint . --fix
```

**Java:**
```bash
# Code formatting
mvn spotless:apply

# Static analysis
mvn checkstyle:check
mvn pmd:check
```

#### 5.2 Performance Optimization
- Profile code for performance bottlenecks
- Optimize database queries and API calls
- Implement caching where appropriate
- Use efficient algorithms and data structures

#### 5.3 Documentation Updates
- Update API documentation for new endpoints
- Add or update inline code comments
- Update README.md if functionality changes
- Maintain CHANGELOG.md with new features

### Phase 6: Final Quality Verification

#### 6.1 Comprehensive Quality Check
Run the complete quality verification:
```bash
./scripts/pre-commit-quality-check.sh your-project-key
```

This final check ensures:
- All unit tests pass
- Code coverage meets requirements
- Static analysis passes
- Security checks pass
- Code style is consistent

#### 6.2 Integration Testing
If applicable, run integration tests:
```bash
# Example commands
npm run test:integration
python -m pytest tests/integration/
mvn verify
```

### Phase 7: Git Commit Best Practices

#### 7.1 Staging Changes
```bash
# Review changes before staging
git diff

# Stage specific files
git add src/specific-file.py

# Or stage all changes (use carefully)
git add .

# Review staged changes
git diff --cached
```

#### 7.2 Commit Message Standards
Follow the conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(auth): implement JWT token authentication

- Add JWT-based authentication system
- Implement user registration and login endpoints
- Include password hashing with bcrypt
- Add middleware for protected routes
- Update API documentation

SonarQube: 0 bugs, 0 vulnerabilities, 85% coverage
Closes #123
```

#### 7.3 Commit Execution
```bash
# Using the generated template
git commit -F .commit-message-template

# Or commit with inline message
git commit -m "feat(auth): implement JWT authentication

- Add JWT-based authentication system
- Include password hashing with bcrypt
- Add middleware for protected routes

SonarQube: 0 bugs, 0 vulnerabilities, 85% coverage
Closes #123"
```

### Phase 8: Post-Commit Verification

#### 8.1 Push and CI/CD Pipeline
```bash
# Push to remote repository
git push origin feature/your-feature-name

# Monitor CI/CD pipeline
# Ensure all automated tests pass
# Verify deployment to staging environment
```

#### 8.2 Pull Request Creation
Create a pull request with:
- Clear description of changes
- Link to related issues
- Screenshots or demos if applicable
- Checklist of completed tasks

#### 8.3 Continuous Monitoring
After merge:
- Monitor application metrics
- Watch for any production issues
- Be prepared to hotfix if necessary

## Quality Metrics and Reporting

### Key Performance Indicators (KPIs)
- Code coverage percentage
- Number of bugs found in production
- Time to resolve security vulnerabilities
- Code review turnaround time
- SonarQube quality gate pass rate

### Regular Quality Reviews
- Weekly team code quality reviews
- Monthly SonarQube metrics analysis
- Quarterly process improvement sessions

## Troubleshooting Common Issues

### Test Failures
```bash
# Run specific test
python -m pytest tests/test_specific.py -v

# Debug test with pdb
python -m pytest tests/test_specific.py --pdb
```

### SonarQube Issues
```bash
# Get detailed SonarQube report
./scripts/pre-commit-quality-check.sh your-project-key

# View specific issues
# Check SonarQube web interface for detailed analysis
```

### Code Style Issues
```bash
# Auto-fix common style issues
black . --diff  # Preview changes
black .          # Apply changes

# Fix linting issues
eslint . --fix   # JavaScript/TypeScript
autopep8 -i .    # Python
```

## Tools and Resources

### Required Tools
- Git
- Language-specific testing frameworks
- Code formatters (Black, Prettier, etc.)
- Linters (ESLint, Flake8, etc.)
- SonarQube scanner
- Security scanners (Safety, npm audit, etc.)

### Recommended IDE Extensions
- SonarLint
- GitLens
- Language-specific linters
- Code formatters
- Test runners

### Documentation Links
- [Project Coding Standards](./coding-standards.md)
- [Testing Guidelines](./testing-guidelines.md)
- [Security Best Practices](./security-guidelines.md)
- [CI/CD Pipeline Documentation](./cicd-pipeline.md)

## Conclusion

Following this comprehensive workflow ensures that every commit meets enterprise-grade quality standards. The combination of automated checks, peer review, and static analysis creates multiple layers of quality assurance, resulting in more reliable, secure, and maintainable code.

Remember: Quality is not just about passing tests—it's about creating code that is readable, maintainable, secure, and performs well in production environments.
