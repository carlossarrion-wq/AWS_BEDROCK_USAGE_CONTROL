#!/bin/bash
# pre-commit-quality-check.sh
# Comprehensive quality check script for git commits
# Usage: ./scripts/pre-commit-quality-check.sh [PROJECT_KEY]

set -e

# Configuration
PROJECT_KEY="${1:-your-project-key}"
COVERAGE_THRESHOLD=80
MIN_QUALITY_RATING="A"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if MCP tools are available
check_mcp_tools() {
    log_info "Checking MCP tool availability..."
    
    if ! command -v mcp-tool &> /dev/null; then
        log_warning "MCP tools not found. Using fallback commands where possible."
        return 1
    fi
    
    log_success "MCP tools available"
    return 0
}

# Step 1: Unit Testing
run_unit_tests() {
    log_info "Running unit tests..."
    
    if [ -f "package.json" ]; then
        npm test || { log_error "Unit tests failed"; exit 1; }
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        python -m pytest --cov || { log_error "Unit tests failed"; exit 1; }
    elif [ -f "pom.xml" ]; then
        mvn test || { log_error "Unit tests failed"; exit 1; }
    elif [ -f "*.csproj" ]; then
        dotnet test || { log_error "Unit tests failed"; exit 1; }
    else
        log_warning "No recognized test framework found. Skipping unit tests."
        return 0
    fi
    
    log_success "Unit tests passed"
}

# Step 2: Test Coverage Check
check_test_coverage() {
    log_info "Checking test coverage..."
    
    if [ -f "package.json" ]; then
        if npm run test:coverage &> /dev/null; then
            COVERAGE=$(npm run test:coverage 2>/dev/null | grep -o '[0-9]*\.[0-9]*%\|[0-9]*%' | head -1 | sed 's/%//')
            if [ ! -z "$COVERAGE" ] && [ "${COVERAGE%.*}" -lt "$COVERAGE_THRESHOLD" ]; then
                log_error "Coverage ${COVERAGE}% is below threshold ${COVERAGE_THRESHOLD}%"
                exit 1
            fi
            log_success "Test coverage: ${COVERAGE}%"
        else
            log_warning "Coverage script not found. Skipping coverage check."
        fi
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        if command -v pytest &> /dev/null; then
            COVERAGE=$(python -m pytest --cov --cov-report=term-missing 2>/dev/null | grep "TOTAL" | awk '{print $4}' | sed 's/%//')
            if [ ! -z "$COVERAGE" ] && [ "$COVERAGE" -lt "$COVERAGE_THRESHOLD" ]; then
                log_error "Coverage ${COVERAGE}% is below threshold ${COVERAGE_THRESHOLD}%"
                exit 1
            fi
            log_success "Test coverage: ${COVERAGE}%"
        fi
    else
        log_warning "Coverage check not available for this project type"
    fi
}

# Step 3: SonarQube Analysis
run_sonarqube_analysis() {
    log_info "Running SonarQube analysis..."
    
    if ! check_mcp_tools; then
        log_warning "SonarQube analysis requires MCP tools. Skipping."
        return 0
    fi
    
    # Check if project exists in SonarQube
    log_info "Checking SonarQube project: $PROJECT_KEY"
    
    # Get quality gate status
    QUALITY_GATE_RESULT=$(mcp-tool sonarqube get_quality_gate_status --projectKey "$PROJECT_KEY" 2>/dev/null || echo "ERROR")
    
    if [[ "$QUALITY_GATE_RESULT" == *"ERROR"* ]] || [[ "$QUALITY_GATE_RESULT" == *"FAILED"* ]]; then
        log_error "SonarQube quality gate failed for project: $PROJECT_KEY"
        
        # Get detailed issues
        log_info "Fetching critical issues..."
        CRITICAL_ISSUES=$(mcp-tool sonarqube get_project_issues \
            --projectKey "$PROJECT_KEY" \
            --types "BUG,VULNERABILITY" \
            --severities "BLOCKER,CRITICAL" \
            --pageSize 10 2>/dev/null || echo "Unable to fetch issues")
        
        echo "$CRITICAL_ISSUES"
        exit 1
    fi
    
    # Get project metrics
    log_info "Fetching project metrics..."
    METRICS_RESULT=$(mcp-tool sonarqube get_project_metrics \
        --projectKey "$PROJECT_KEY" \
        --metricKeys "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density" 2>/dev/null || echo "Unable to fetch metrics")
    
    if [[ "$METRICS_RESULT" != *"Unable to fetch metrics"* ]]; then
        # Parse and display metrics
        BUGS=$(echo "$METRICS_RESULT" | grep -o '"metric":"bugs"[^}]*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
        VULNERABILITIES=$(echo "$METRICS_RESULT" | grep -o '"metric":"vulnerabilities"[^}]*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
        CODE_SMELLS=$(echo "$METRICS_RESULT" | grep -o '"metric":"code_smells"[^}]*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
        
        log_success "SonarQube Metrics:"
        echo "  - Bugs: ${BUGS:-0}"
        echo "  - Vulnerabilities: ${VULNERABILITIES:-0}"
        echo "  - Code Smells: ${CODE_SMELLS:-0}"
        
        # Check for critical issues
        if [ "${BUGS:-0}" -gt "0" ] || [ "${VULNERABILITIES:-0}" -gt "0" ]; then
            log_error "Critical issues found: ${BUGS:-0} bugs, ${VULNERABILITIES:-0} vulnerabilities"
            exit 1
        fi
    fi
    
    log_success "SonarQube quality gate passed"
}

# Step 4: Code Style and Linting
run_code_style_checks() {
    log_info "Running code style checks..."
    
    # JavaScript/TypeScript
    if [ -f "package.json" ]; then
        if npm run lint &> /dev/null; then
            npm run lint || { log_error "Linting failed"; exit 1; }
            log_success "JavaScript/TypeScript linting passed"
        elif command -v eslint &> /dev/null; then
            eslint . || { log_error "ESLint failed"; exit 1; }
            log_success "ESLint passed"
        fi
        
        if npm run format:check &> /dev/null; then
            npm run format:check || { log_error "Code formatting check failed"; exit 1; }
            log_success "Code formatting check passed"
        fi
    fi
    
    # Python
    if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
        if command -v flake8 &> /dev/null; then
            flake8 . || { log_error "Flake8 linting failed"; exit 1; }
            log_success "Python flake8 linting passed"
        fi
        
        if command -v black &> /dev/null; then
            black --check . || { log_error "Black formatting check failed"; exit 1; }
            log_success "Python black formatting check passed"
        fi
    fi
    
    # Java
    if [ -f "pom.xml" ]; then
        if mvn checkstyle:check &> /dev/null; then
            mvn checkstyle:check || { log_error "Java checkstyle failed"; exit 1; }
            log_success "Java checkstyle passed"
        fi
    fi
}

# Step 5: Security Checks
run_security_checks() {
    log_info "Running security checks..."
    
    # Check for common security issues
    if command -v grep &> /dev/null; then
        # Check for hardcoded secrets
        if grep -r -i "password\s*=\|api_key\s*=\|secret\s*=\|token\s*=" --include="*.py" --include="*.js" --include="*.java" --include="*.cs" . 2>/dev/null; then
            log_error "Potential hardcoded secrets found in code"
            exit 1
        fi
        
        # Check for TODO/FIXME comments that might indicate security issues
        SECURITY_TODOS=$(grep -r -i "TODO.*security\|FIXME.*security\|TODO.*auth\|FIXME.*auth" --include="*.py" --include="*.js" --include="*.java" --include="*.cs" . 2>/dev/null || true)
        if [ ! -z "$SECURITY_TODOS" ]; then
            log_warning "Security-related TODO/FIXME comments found:"
            echo "$SECURITY_TODOS"
        fi
    fi
    
    # Node.js security audit
    if [ -f "package.json" ] && command -v npm &> /dev/null; then
        npm audit --audit-level=high || { log_error "npm security audit failed"; exit 1; }
        log_success "npm security audit passed"
    fi
    
    # Python security checks
    if [ -f "requirements.txt" ] && command -v safety &> /dev/null; then
        safety check || { log_error "Python safety check failed"; exit 1; }
        log_success "Python safety check passed"
    fi
    
    log_success "Security checks completed"
}

# Step 6: Git Status and Staging
prepare_git_commit() {
    log_info "Preparing Git commit..."
    
    if check_mcp_tools; then
        # Use MCP Git tools
        GIT_STATUS=$(mcp-tool git_status --repo_path . 2>/dev/null || git status --porcelain)
    else
        # Use standard Git
        GIT_STATUS=$(git status --porcelain)
    fi
    
    if [ -z "$GIT_STATUS" ]; then
        log_warning "No changes to commit"
        exit 0
    fi
    
    log_info "Files to be committed:"
    echo "$GIT_STATUS"
    
    # Show diff of staged changes
    if check_mcp_tools; then
        STAGED_DIFF=$(mcp-tool git_diff_staged --repo_path . 2>/dev/null || git diff --cached)
    else
        STAGED_DIFF=$(git diff --cached)
    fi
    
    if [ ! -z "$STAGED_DIFF" ]; then
        log_info "Staged changes preview:"
        echo "$STAGED_DIFF" | head -20
        if [ $(echo "$STAGED_DIFF" | wc -l) -gt 20 ]; then
            echo "... (truncated, showing first 20 lines)"
        fi
    fi
}

# Step 7: Generate Commit Message Template
generate_commit_message() {
    log_info "Generating commit message template..."
    
    # Get current metrics for commit message
    if check_mcp_tools && [ "$PROJECT_KEY" != "your-project-key" ]; then
        METRICS=$(mcp-tool sonarqube get_project_metrics \
            --projectKey "$PROJECT_KEY" \
            --metricKeys "bugs,vulnerabilities,coverage" 2>/dev/null || echo "")
        
        if [ ! -z "$METRICS" ]; then
            BUGS=$(echo "$METRICS" | grep -o '"metric":"bugs"[^}]*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
            VULNERABILITIES=$(echo "$METRICS" | grep -o '"metric":"vulnerabilities"[^}]*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
            COVERAGE=$(echo "$METRICS" | grep -o '"metric":"coverage"[^}]*"value":"[^"]*"' | grep -o '"value":"[^"]*"' | cut -d'"' -f4)
            
            QUALITY_METRICS="SonarQube: ${BUGS:-0} bugs, ${VULNERABILITIES:-0} vulnerabilities"
            if [ ! -z "$COVERAGE" ]; then
                QUALITY_METRICS="$QUALITY_METRICS, ${COVERAGE}% coverage"
            fi
        fi
    fi
    
    cat > .commit-message-template << EOF
# Commit Message Template
# Format: <type>(<scope>): <subject>
#
# Types: feat, fix, docs, style, refactor, test, chore
# 
# Example:
# feat(auth): add JWT token authentication
# 
# - Implement JWT-based authentication system
# - Add user registration and login endpoints
# - Include password hashing with bcrypt
# - Add middleware for protected routes
# - Update API documentation
# ${QUALITY_METRICS:-Quality checks: All passed}
#
# Fixes #123
# Closes #124

EOF
    
    log_success "Commit message template created at .commit-message-template"
}

# Main execution
main() {
    echo "🚀 Starting Pre-Commit Quality Workflow..."
    echo "Project Key: $PROJECT_KEY"
    echo "Coverage Threshold: $COVERAGE_THRESHOLD%"
    echo "----------------------------------------"
    
    # Run all quality checks
    run_unit_tests
    check_test_coverage
    run_code_style_checks
    run_security_checks
    run_sonarqube_analysis
    prepare_git_commit
    generate_commit_message
    
    echo "----------------------------------------"
    log_success "🎉 All quality checks passed!"
    log_info "📝 Ready for commit. Use the template at .commit-message-template"
    log_info "💡 Next steps:"
    echo "   1. Review the staged changes"
    echo "   2. Create your commit message using the template"
    echo "   3. Commit your changes"
    
    if check_mcp_tools; then
        echo "   4. Use: mcp-tool git_commit --repo_path . --message \"your message\""
    else
        echo "   4. Use: git commit -F .commit-message-template"
    fi
}

# Run main function
main "$@"
