# Git Commit Workflow Setup Guide

This guide provides step-by-step instructions for implementing the enhanced git commit workflow in your development environment.

## Quick Start

1. **Run the pre-commit quality check:**
   ```bash
   ./scripts/pre-commit-quality-check.sh [YOUR_SONARQUBE_PROJECT_KEY]
   ```

2. **Follow the workflow steps** as outlined in the enhanced workflow documentation

3. **Commit using the generated template** or MCP tools

## Prerequisites Setup

### 1. MCP Servers Configuration

#### SonarQube MCP Server
Ensure the SonarQube MCP server is configured and accessible:

```bash
# Test SonarQube MCP server connection
mcp-tool sonarqube list_projects
```

If not configured, set up your SonarQube server connection according to your MCP server documentation.

#### Git MCP Server (Optional)
The Git MCP server provides enhanced git operations:

```bash
# Test Git MCP server connection
mcp-tool git_status --repo_path .
```

### 2. Development Tools Installation

#### For JavaScript/TypeScript Projects
```bash
# Install testing and linting tools
npm install --save-dev jest eslint prettier
npm install --save-dev @types/jest @typescript-eslint/eslint-plugin

# Add scripts to package.json
{
  "scripts": {
    "test": "jest",
    "test:coverage": "jest --coverage",
    "lint": "eslint .",
    "format:check": "prettier --check .",
    "format": "prettier --write ."
  }
}
```

#### For Python Projects
```bash
# Install testing and quality tools
pip install pytest pytest-cov flake8 black safety

# Or add to requirements-dev.txt
echo "pytest>=6.0" >> requirements-dev.txt
echo "pytest-cov>=2.0" >> requirements-dev.txt
echo "flake8>=3.8" >> requirements-dev.txt
echo "black>=21.0" >> requirements-dev.txt
echo "safety>=1.10" >> requirements-dev.txt
```

#### For Java Projects
```bash
# Ensure Maven is configured with necessary plugins
# Add to pom.xml:
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>3.0.0-M7</version>
</plugin>
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-checkstyle-plugin</artifactId>
    <version>3.1.2</version>
</plugin>
```

#### For .NET Projects
```bash
# Install necessary tools
dotnet tool install --global dotnet-reportgenerator-globaltool
```

### 3. SonarQube Project Setup

1. **Create or identify your SonarQube project key:**
   ```bash
   # List existing projects
   mcp-tool sonarqube list_projects
   ```

2. **Configure your project for SonarQube analysis:**
   ```bash
   # Create sonar-project.properties file
   cat > sonar-project.properties << EOF
   sonar.projectKey=your-project-key
   sonar.projectName=Your Project Name
   sonar.projectVersion=1.0
   sonar.sources=src
   sonar.tests=tests
   sonar.language=js,py,java,cs
   sonar.sourceEncoding=UTF-8
   EOF
   ```

## Workflow Implementation

### 1. Manual Implementation

Follow the steps in `docs/enhanced-git-commit-workflow.md` manually for each commit.

### 2. Automated Implementation (Recommended)

#### Using the Pre-Commit Script

1. **Make the script executable** (already done):
   ```bash
   chmod +x scripts/pre-commit-quality-check.sh
   ```

2. **Run the script before each commit:**
   ```bash
   # With your SonarQube project key
   ./scripts/pre-commit-quality-check.sh your-sonarqube-project-key
   
   # Or with default settings
   ./scripts/pre-commit-quality-check.sh
   ```

3. **Follow the script output** and address any issues found

4. **Use the generated commit message template:**
   ```bash
   # The script creates .commit-message-template
   git commit -F .commit-message-template
   
   # Or edit the template and commit
   git commit -t .commit-message-template
   ```

#### Git Hooks Integration

Set up the script as a pre-commit hook:

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run quality checks before commit
./scripts/pre-commit-quality-check.sh your-sonarqube-project-key
EOF

# Make hook executable
chmod +x .git/hooks/pre-commit
```

### 3. CI/CD Integration

#### GitHub Actions Example

```yaml
# .github/workflows/quality-check.yml
name: Quality Check

on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: npm ci
      
    - name: Run quality checks
      run: ./scripts/pre-commit-quality-check.sh ${{ secrets.SONARQUBE_PROJECT_KEY }}
      env:
        SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

#### GitLab CI Example

```yaml
# .gitlab-ci.yml
stages:
  - quality-check

quality-check:
  stage: quality-check
  script:
    - chmod +x scripts/pre-commit-quality-check.sh
    - ./scripts/pre-commit-quality-check.sh $SONARQUBE_PROJECT_KEY
  variables:
    SONAR_TOKEN: $SONAR_TOKEN
```

## Configuration Options

### Script Configuration

Edit the script variables at the top of `scripts/pre-commit-quality-check.sh`:

```bash
# Configuration
PROJECT_KEY="${1:-your-project-key}"        # SonarQube project key
COVERAGE_THRESHOLD=80                        # Minimum test coverage %
MIN_QUALITY_RATING="A"                      # Minimum quality rating
```

### Quality Gate Customization

Customize quality gates in SonarQube:

1. **Access SonarQube web interface**
2. **Go to Quality Gates**
3. **Create or modify conditions:**
   - Bugs: 0
   - Vulnerabilities: 0
   - Code Smells: < 50
   - Coverage: > 80%
   - Duplicated Lines: < 5%

### Project-Specific Rules

Create a `.quality-config` file in your project root:

```bash
# .quality-config
COVERAGE_THRESHOLD=85
SONARQUBE_PROJECT_KEY=my-specific-project
ENABLE_SECURITY_CHECKS=true
ENABLE_PERFORMANCE_CHECKS=true
```

## Usage Examples

### Example 1: JavaScript Project

```bash
# 1. Develop your feature
# 2. Stage your changes
git add .

# 3. Run quality checks
./scripts/pre-commit-quality-check.sh my-js-project

# 4. Review the output
# ✅ Unit tests passed
# ✅ Test coverage: 87%
# ✅ JavaScript/TypeScript linting passed
# ✅ npm security audit passed
# ✅ SonarQube quality gate passed

# 5. Commit using template
git commit -F .commit-message-template
```

### Example 2: Python Project

```bash
# 1. Develop your feature
# 2. Stage your changes
git add .

# 3. Run quality checks
./scripts/pre-commit-quality-check.sh my-python-project

# 4. Address any issues found
# ❌ Flake8 linting failed
# Fix linting issues...

# 5. Re-run checks
./scripts/pre-commit-quality-check.sh my-python-project

# 6. Commit when all checks pass
git commit -F .commit-message-template
```

### Example 3: Using MCP Git Tools

```bash
# 1. Check status using MCP
mcp-tool git_status --repo_path .

# 2. Review changes
mcp-tool git_diff_unstaged --repo_path .

# 3. Stage files
mcp-tool git_add --repo_path . --files ["src/", "tests/"]

# 4. Run quality checks
./scripts/pre-commit-quality-check.sh my-project

# 5. Commit using MCP
mcp-tool git_commit --repo_path . --message "feat: add new feature

- Implement user authentication
- Add comprehensive tests
- Update documentation
- SonarQube: 0 bugs, 0 vulnerabilities, 89% coverage

Fixes #123"
```

## Troubleshooting

### Common Issues

#### 1. MCP Tools Not Found
```bash
# Error: mcp-tool command not found
# Solution: Install and configure MCP tools
# Or use fallback commands (script handles this automatically)
```

#### 2. SonarQube Connection Issues
```bash
# Error: Unable to connect to SonarQube
# Solution: Check MCP server configuration
mcp-tool sonarqube list_projects
```

#### 3. Test Coverage Below Threshold
```bash
# Error: Coverage 75% is below threshold 80%
# Solution: Add more tests or adjust threshold
# Edit COVERAGE_THRESHOLD in the script
```

#### 4. Quality Gate Failures
```bash
# Error: SonarQube quality gate failed
# Solution: Check detailed issues
mcp-tool sonarqube get_project_issues --projectKey "your-key" --severities "BLOCKER,CRITICAL"
```

### Debug Mode

Run the script with debug output:

```bash
# Enable debug mode
set -x
./scripts/pre-commit-quality-check.sh your-project-key
set +x
```

### Skip Specific Checks

Temporarily skip checks by commenting out functions in the script:

```bash
# In main() function, comment out checks to skip:
# run_unit_tests
# check_test_coverage
# run_code_style_checks
# run_security_checks
# run_sonarqube_analysis
```

## Team Adoption

### 1. Team Setup

1. **Share the workflow documentation** with all team members
2. **Conduct a team training session** on the new workflow
3. **Set up shared SonarQube projects** for all repositories
4. **Configure CI/CD pipelines** to enforce quality checks

### 2. Gradual Implementation

1. **Week 1**: Introduce the workflow documentation
2. **Week 2**: Start using the script manually
3. **Week 3**: Set up git hooks for automated checks
4. **Week 4**: Integrate with CI/CD pipelines

### 3. Monitoring and Improvement

1. **Track quality metrics** over time
2. **Regular retrospectives** on workflow effectiveness
3. **Adjust thresholds** based on team capabilities
4. **Update tools and processes** as needed

## Best Practices

### 1. Commit Frequency
- Make small, focused commits
- Run quality checks for each commit
- Use feature branches for larger changes

### 2. Quality Metrics
- Monitor trends, not just absolute values
- Set realistic but challenging thresholds
- Regular review of technical debt

### 3. Team Collaboration
- Share quality check results in code reviews
- Discuss quality improvements in team meetings
- Celebrate quality achievements

## Support and Maintenance

### Regular Updates

1. **Update dependencies** regularly
2. **Review and adjust quality thresholds** quarterly
3. **Update SonarQube rules** as needed
4. **Keep MCP servers updated**

### Documentation Maintenance

1. **Update workflow documentation** when processes change
2. **Keep examples current** with latest tool versions
3. **Document team-specific customizations**

## Conclusion

This setup guide provides everything needed to implement the enhanced git commit workflow in your development environment. The combination of automated tools, quality checks, and clear processes ensures that every commit meets the highest quality standards.

Remember: The goal is to make quality checks seamless and automatic, so developers can focus on writing great code while maintaining high standards.
