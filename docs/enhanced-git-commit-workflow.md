# Enhanced Git Commit Workflow for High-Quality Software Development

This document defines a comprehensive, tool-integrated workflow that developers must follow when committing changes to ensure the highest quality standards are maintained throughout the development process.

## Overview

This enhanced workflow integrates multiple quality assurance steps including automated code review, optimization, testing, and static analysis using MCP (Model Context Protocol) servers before allowing any code to be committed to the repository.

## Prerequisites

- Git repository properly configured
- SonarQube server accessible via MCP server
- Unit testing framework set up
- Code review tools/process established
- MCP servers configured:
  - `sonarqube-server` for static code analysis
  - `github.com/modelcontextprotocol/servers/tree/main/src/git` for Git operations (optional)

## Workflow Steps

### 1. Pre-Commit Preparation

#### 1.1 Code Development Completion
- [ ] Ensure all intended functionality is implemented
- [ ] Verify code compiles/runs without errors
- [ ] Remove any debug code, console logs, or temporary comments
- [ ] Update relevant documentation if features were added/modified

#### 1.2 Self-Review
- [ ] Review your own code for obvious issues
- [ ] Check for proper error handling
- [ ] Verify variable naming follows project conventions
- [ ] Ensure code follows DRY (Don't Repeat Yourself) principles

### 2. Code Review Process

#### 2.1 Peer Code Review
- [ ] Create a pull/merge request or share code diff with team members
- [ ] Request review from at least one senior developer
- [ ] Address all reviewer comments and suggestions
- [ ] Document any architectural decisions or trade-offs made

#### 2.2 Automated Code Bug Identification

Use MCP tools to identify potential issues:

**Check Git Status:**
```bash
# Using MCP Git server (if available)
mcp-tool git_status --repo_path .

# Or standard Git command
git status
```

**Review Changes:**
```bash
# Using MCP Git server
mcp-tool git_diff_unstaged --repo_path . --context_lines 5

# Or standard Git command
git diff
```

#### 2.3 Code Bug Categories to Review

- [ ] **Logic Errors**: Review algorithm implementations and business logic
- [ ] **Memory Leaks**: Check for proper resource management (especially in C/C++, Java)
- [ ] **Null Pointer/Reference Issues**: Verify null checks are in place
- [ ] **Concurrency Issues**: Review thread safety and race conditions
- [ ] **Security Vulnerabilities**: Check for SQL injection, XSS, authentication issues
- [ ] **Performance Bottlenecks**: Identify inefficient loops, database queries, or API calls

#### 2.4 Proposed Solutions Documentation
For each identified issue, document:
- **Problem Description**: Clear explanation of the issue
- **Impact Assessment**: Severity and potential consequences
- **Proposed Solution**: Detailed fix with code examples if applicable
- **Alternative Approaches**: Other possible solutions considered
- **Testing Strategy**: How the fix will be validated

### 3. Code Optimization

#### 3.1 Coding Standards Alignment
- [ ] **Python Projects**: Follow PEP 8, use type hints, proper docstrings
- [ ] **JavaScript/TypeScript**: Follow ESLint rules, use proper async/await patterns
- [ ] **Java**: Follow Oracle coding conventions, use proper exception handling
- [ ] **C#**: Follow Microsoft coding conventions, use proper LINQ patterns
- [ ] **General**: Ensure consistent indentation, naming conventions, and file organization

#### 3.2 Project-Level Rules Compliance
- [ ] Verify adherence to project-specific architectural patterns
- [ ] Check dependency injection usage (if applicable)
- [ ] Validate API design consistency
- [ ] Ensure proper logging and monitoring integration
- [ ] Verify configuration management practices

### 4. Unit Testing

#### 4.1 Test Coverage Requirements
- [ ] Achieve minimum 80% code coverage for new code
- [ ] Ensure all public methods have corresponding tests
- [ ] Test both positive and negative scenarios
- [ ] Include edge cases and boundary conditions

#### 4.2 Test Execution
```bash
# Example commands for different frameworks
npm test                    # Node.js/JavaScript
python -m pytest --cov     # Python
mvn test                    # Java Maven
dotnet test --collect:"XPlat Code Coverage"  # .NET
```

#### 4.3 Test Results Analysis
- [ ] All tests must pass (0 failures)
- [ ] Review test coverage report
- [ ] Identify and address any coverage gaps
- [ ] Ensure test execution time is reasonable
- [ ] Document any skipped tests with justification

### 5. Static Code Analysis with SonarQube MCP Server

#### 5.1 Project Analysis Using MCP Tools

**List Available Projects:**
```bash
mcp-tool sonarqube list_projects --search "your-project-name"
```

**Get Project Metrics:**
```bash
mcp-tool sonarqube get_project_metrics \
  --projectKey "your-project-key" \
  --metricKeys "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc,sqale_index"
```

**Check Quality Gate Status:**
```bash
mcp-tool sonarqube get_quality_gate_status --projectKey "your-project-key"
```

**Get Detailed Issues:**
```bash
mcp-tool sonarqube get_project_issues \
  --projectKey "your-project-key" \
  --types "BUG,VULNERABILITY,CODE_SMELL" \
  --severities "BLOCKER,CRITICAL,MAJOR" \
  --pageSize 100
```

#### 5.2 Quality Gate Validation

Based on SonarQube metrics, ensure:

- [ ] **Bugs**: Zero new bugs introduced (target: 0)
- [ ] **Vulnerabilities**: Zero new security vulnerabilities (target: 0)
- [ ] **Code Smells**: Address critical and major code smells
- [ ] **Coverage**: Maintain or improve test coverage percentage (target: >80%)
- [ ] **Duplications**: Keep code duplication below project threshold (target: <5%)
- [ ] **Maintainability Rating**: Achieve A or B rating
- [ ] **Reliability Rating**: Achieve A rating
- [ ] **Security Rating**: Achieve A rating

#### 5.3 SonarQube Issues Resolution

**Example Quality Metrics Interpretation:**
```
Project: your-project
- Bugs: 0 (✅ PASS)
- Vulnerabilities: 0 (✅ PASS)
- Code Smells: 25 (⚠️ REVIEW NEEDED)
- Coverage: 85.2% (✅ PASS)
- Duplicated Lines: 3.2% (✅ PASS)
- Technical Debt: 2h 30min (⚠️ ACCEPTABLE)
```

For each identified issue:
- [ ] **Critical Issues**: Must be fixed before commit
- [ ] **Major Issues**: Should be fixed or documented as technical debt
- [ ] **Minor Issues**: Address if time permits or create backlog items
- [ ] **Info Issues**: Review and consider for future improvements

#### 5.4 Automated Quality Check Script

Create a script to automate SonarQube checks:

```bash
#!/bin/bash
# quality-check.sh

PROJECT_KEY="your-project-key"

echo "🔍 Running SonarQube Quality Analysis..."

# Get quality gate status
QUALITY_GATE=$(mcp-tool sonarqube get_quality_gate_status --projectKey "$PROJECT_KEY")

# Get project metrics
METRICS=$(mcp-tool sonarqube get_project_metrics \
  --projectKey "$PROJECT_KEY" \
  --metricKeys "bugs,vulnerabilities,code_smells,coverage")

# Get critical issues
ISSUES=$(mcp-tool sonarqube get_project_issues \
  --projectKey "$PROJECT_KEY" \
  --types "BUG,VULNERABILITY" \
  --severities "BLOCKER,CRITICAL")

echo "📊 Quality Gate Status: $QUALITY_GATE"
echo "📈 Project Metrics: $METRICS"
echo "🚨 Critical Issues: $ISSUES"

# Exit with error if quality gate fails
if [[ "$QUALITY_GATE" == *"ERROR"* ]]; then
  echo "❌ Quality gate failed. Please fix issues before committing."
  exit 1
fi

echo "✅ Quality checks passed!"
```

### 6. Integration Testing (Optional but Recommended)

#### 6.1 API Integration Tests
- [ ] Test all API endpoints with various input scenarios
- [ ] Verify proper HTTP status codes and response formats
- [ ] Test authentication and authorization mechanisms
- [ ] Validate error handling and edge cases

#### 6.2 Database Integration Tests
- [ ] Test database migrations and rollbacks
- [ ] Verify data integrity constraints
- [ ] Test transaction handling
- [ ] Validate query performance

### 7. Documentation Updates

#### 7.1 Code Documentation
- [ ] Update inline code comments for complex logic
- [ ] Ensure API documentation is current (Swagger/OpenAPI)
- [ ] Update README.md if new features or setup steps are added
- [ ] Document any breaking changes

#### 7.2 Project Documentation
- [ ] Update CHANGELOG.md with new features, fixes, and breaking changes
- [ ] Update architecture documentation if applicable
- [ ] Create or update user guides for new features
- [ ] Update deployment documentation if needed

### 8. Final Pre-Commit Checklist

#### 8.1 Environment Verification
- [ ] Code works in development environment
- [ ] Code works in staging environment (if available)
- [ ] All environment-specific configurations are properly handled
- [ ] Database migrations run successfully

#### 8.2 Security Review
- [ ] No sensitive data (passwords, API keys) in code
- [ ] Proper input validation and sanitization
- [ ] Authentication and authorization properly implemented
- [ ] HTTPS/TLS properly configured where applicable

### 9. Git Commit Process

#### 9.1 Using MCP Git Server (Recommended)

**Check Repository Status:**
```bash
mcp-tool git_status --repo_path .
```

**Review Staged Changes:**
```bash
mcp-tool git_diff_staged --repo_path . --context_lines 3
```

**Add Files to Staging:**
```bash
mcp-tool git_add --repo_path . --files ["src/", "tests/", "docs/"]
```

**Create Commit with Detailed Message:**
```bash
mcp-tool git_commit --repo_path . --message "feat: add user authentication with JWT tokens

- Implement JWT-based authentication system
- Add user registration and login endpoints  
- Include password hashing with bcrypt
- Add middleware for protected routes
- Update API documentation
- SonarQube: 0 bugs, 0 vulnerabilities, 85% coverage

Fixes #123
Closes #124"
```

#### 9.2 Using Standard Git Commands (Fallback)

```bash
# Stage your changes
git add .

# Create a meaningful commit message
git commit -m "feat: add user authentication with JWT tokens

- Implement JWT-based authentication system
- Add user registration and login endpoints
- Include password hashing with bcrypt
- Add middleware for protected routes
- Update API documentation
- SonarQube: 0 bugs, 0 vulnerabilities, 85% coverage

Fixes #123
Closes #124"
```

#### 9.3 Commit Message Standards

Follow conventional commit format with quality metrics:
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

**Enhanced Commit Message Template:**
```
<type>(<scope>): <subject>

<body>

Quality Metrics:
- SonarQube: X bugs, Y vulnerabilities, Z% coverage
- Tests: All passing (X tests, Y% coverage)
- Code Review: Approved by <reviewer>

<footer>
```

### 10. Post-Commit Actions

#### 10.1 Continuous Integration
- [ ] Monitor CI/CD pipeline execution
- [ ] Verify all automated tests pass
- [ ] Check deployment to staging environment
- [ ] Monitor application metrics and logs

#### 10.2 Team Communication
- [ ] Notify team of significant changes
- [ ] Update project management tools (Jira, Trello, etc.)
- [ ] Schedule code walkthrough if needed
- [ ] Document lessons learned

## Automated Workflow Script

Create a comprehensive pre-commit script that integrates all quality checks:

```bash
#!/bin/bash
# pre-commit-quality-check.sh

set -e

PROJECT_KEY="your-project-key"
COVERAGE_THRESHOLD=80

echo "🚀 Starting Pre-Commit Quality Workflow..."

# Step 1: Run unit tests
echo "🧪 Running unit tests..."
npm test || { echo "❌ Unit tests failed"; exit 1; }

# Step 2: Check test coverage
echo "📊 Checking test coverage..."
COVERAGE=$(npm run test:coverage | grep -o '[0-9]*%' | head -1 | sed 's/%//')
if [ "$COVERAGE" -lt "$COVERAGE_THRESHOLD" ]; then
    echo "❌ Coverage $COVERAGE% is below threshold $COVERAGE_THRESHOLD%"
    exit 1
fi

# Step 3: SonarQube analysis
echo "🔍 Running SonarQube analysis..."
QUALITY_GATE=$(mcp-tool sonarqube get_quality_gate_status --projectKey "$PROJECT_KEY")
if [[ "$QUALITY_GATE" == *"ERROR"* ]]; then
    echo "❌ SonarQube quality gate failed"
    mcp-tool sonarqube get_project_issues --projectKey "$PROJECT_KEY" --severities "BLOCKER,CRITICAL"
    exit 1
fi

# Step 4: Check for critical issues
CRITICAL_ISSUES=$(mcp-tool sonarqube get_project_issues \
    --projectKey "$PROJECT_KEY" \
    --types "BUG,VULNERABILITY" \
    --severities "BLOCKER,CRITICAL" \
    --pageSize 1)

if [[ "$CRITICAL_ISSUES" != *"\"total\":0"* ]]; then
    echo "❌ Critical issues found in SonarQube"
    echo "$CRITICAL_ISSUES"
    exit 1
fi

# Step 5: Git operations
echo "📝 Preparing Git commit..."
mcp-tool git_status --repo_path .

# Get metrics for commit message
METRICS=$(mcp-tool sonarqube get_project_metrics \
    --projectKey "$PROJECT_KEY" \
    --metricKeys "bugs,vulnerabilities,coverage")

echo "✅ All quality checks passed!"
echo "📈 Current metrics: $METRICS"
echo "🎯 Ready for commit!"
```

## Quality Gates Summary

Before any commit is allowed, ensure:

1. ✅ **Code Review**: At least one peer approval
2. ✅ **Unit Tests**: All tests pass with adequate coverage (>80%)
3. ✅ **Static Analysis**: SonarQube quality gate passed
4. ✅ **Standards Compliance**: Code follows project conventions
5. ✅ **Documentation**: All relevant docs updated
6. ✅ **Security**: No vulnerabilities introduced (SonarQube: 0 vulnerabilities)
7. ✅ **Performance**: No significant performance degradation
8. ✅ **Technical Debt**: Acceptable levels (SonarQube maintainability rating A/B)

## MCP Tools Reference

### SonarQube Server Tools
- `list_projects`: List all available projects
- `get_project_metrics`: Get specific metrics for a project
- `get_quality_gate_status`: Check if project passes quality gate
- `get_project_issues`: Get detailed list of issues
- `get_project_analysis`: Get latest analysis results
- `get_project_branches`: Get project branches information

### Git Server Tools (if available)
- `git_status`: Show working tree status
- `git_add`: Add files to staging area
- `git_commit`: Create commit with message
- `git_diff_staged`: Show staged changes
- `git_diff_unstaged`: Show unstaged changes
- `git_log`: Show commit history

## Troubleshooting

### Common Issues and Solutions

1. **SonarQube Quality Gate Fails**
   ```bash
   # Get detailed issues
   mcp-tool sonarqube get_project_issues --projectKey "your-key" --severities "BLOCKER,CRITICAL"
   
   # Check specific metrics
   mcp-tool sonarqube get_project_metrics --projectKey "your-key" --metricKeys "bugs,vulnerabilities"
   ```

2. **MCP Server Connection Issues**
   - Verify MCP server is running and accessible
   - Check server configuration and authentication
   - Test connection with simple commands first

3. **Unit Tests Fail**
   - Run tests locally to reproduce issues
   - Check test data dependencies
   - Verify environment configuration

4. **Code Review Feedback**
   - Address all comments before proceeding
   - Ask for clarification if feedback is unclear
   - Document decisions for future reference

## Best Practices

### Commit Frequency
- Commit early and often with small, focused changes
- Each commit should represent a single logical change
- Use feature branches for larger changes

### Quality Metrics Tracking
- Monitor trends in SonarQube metrics over time
- Set up alerts for quality gate failures
- Regular review of technical debt accumulation

### Team Collaboration
- Share quality check scripts across the team
- Establish team-wide quality standards
- Regular retrospectives on workflow effectiveness

## Conclusion

This enhanced workflow leverages MCP servers to provide automated, consistent quality checks throughout the development process. By integrating SonarQube analysis and Git operations through MCP tools, teams can maintain high code quality standards while streamlining the commit process.

The workflow ensures that every commit meets rigorous quality standards through:
- Automated static code analysis
- Comprehensive testing requirements
- Peer review processes
- Documentation standards
- Security validation

Remember: Quality is not negotiable. The automated tools and processes defined in this workflow help maintain consistency and catch issues early, but human judgment and expertise remain essential for delivering high-quality software.
