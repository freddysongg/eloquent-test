# Repository Configuration Guide - Solo Developer

This document provides simplified configuration instructions for the EloquentAI repository optimized for solo development workflow while maintaining essential security and quality standards.

## Table of Contents

1. [Branch Protection Rules](#branch-protection-rules)
2. [Required Status Checks](#required-status-checks)
3. [Dependabot Configuration](#dependabot-configuration)
4. [GitHub Secrets Management](#github-secrets-management)
5. [Repository Settings](#repository-settings)
6. [Security Configuration](#security-configuration)
7. [Solo Developer Access Management](#solo-developer-access-management)

## Branch Protection Rules

### Main Branch Protection

Configure the `main` branch with the following protection rules:

#### Required Reviews (Solo Developer - Simplified)
- **Require pull request reviews before merging**: ❌ Disabled (solo developer)
- **Required number of reviews**: `0`
- **Dismiss stale reviews when new commits are pushed**: ✅ Enabled
- **Require review from code owners**: ❌ Disabled
- **Restrict reviews to users with read access or higher**: ❌ Not applicable

#### Status Check Requirements
- **Require status checks to pass before merging**: ✅ Enabled
- **Require branches to be up to date before merging**: ✅ Enabled

**Essential Status Checks (Simplified):**
```
backend-ci / backend-ci-summary
frontend-ci / frontend-ci-summary
security / security-summary
```

#### Additional Restrictions (Solo Developer - Relaxed)
- **Restrict pushes that create files larger than 100 MB**: ✅ Enabled
- **Require signed commits**: ❌ Disabled (optional for solo work)
- **Require linear history**: ❌ Disabled (allow merge commits)
- **Include administrators**: ❌ Allow admin bypass (solo flexibility)

#### Admin Override Settings (Solo Developer)
- **Allow force pushes**: ✅ Enabled for administrators (emergency fixes)
- **Allow deletions**: ❌ Disabled (safety)

### Development Branch Protection

Configure the `dev` branch with relaxed but secure protection rules:

#### Required Reviews (Solo Developer - Optional)
- **Require pull request reviews before merging**: ❌ Optional (solo developer)
- **Required number of reviews**: `0`
- **Dismiss stale reviews when new commits are pushed**: ✅ Enabled

#### Status Check Requirements
**Essential Status Checks (Minimal for Dev):**
```
backend-ci / test
frontend-ci / test
```

#### Additional Restrictions
- **Allow force pushes**: ✅ Enabled (for admins only)
- **Allow deletions**: ❌ Disabled

## Required Status Checks

### Backend CI/CD Checks
All backend-related status checks must pass before merging to `main`:

```yaml
required_status_checks:
  - "Backend CI/CD / Code Quality & Type Safety"
  - "Backend CI/CD / Security Scanning"
  - "Backend CI/CD / Unit & Integration Tests"
  - "Backend CI/CD / API Endpoint Tests"
  - "Backend CI/CD / Docker Build & Security Scan"
  - "Backend CI/CD / Environment Variables Validation"
```

### Frontend CI/CD Checks
All frontend-related status checks must pass before merging to `main`:

```yaml
required_status_checks:
  - "Frontend CI/CD / Code Quality & Type Safety"
  - "Frontend CI/CD / Unit Tests"
  - "Frontend CI/CD / Build & Bundle Analysis"
  - "Frontend CI/CD / Docker Build & Security Scan"
  - "Frontend CI/CD / Environment & Config Validation"
```

### Integration and Security Checks
System-wide checks that must pass:

```yaml
required_status_checks:
  - "Integration Tests / Full Stack Integration"
  - "Integration Tests / Docker Compose Full Stack Test"
  - "Security Scanning / Static Application Security Testing"
  - "Security Scanning / Dependency Vulnerability Scanning"
  - "Security Scanning / Secret Scanning"
  - "Security Scanning / Container Security Scanning"
```

## Dependabot Configuration

The repository includes a comprehensive Dependabot configuration that automatically:

### Update Schedules
- **Backend Dependencies (Python)**: Weekly on Mondays at 9:00 AM EST
- **Frontend Dependencies (Node.js)**: Weekly on Mondays at 9:00 AM EST
- **GitHub Actions**: Weekly on Mondays at 10:00 AM EST
- **Docker Base Images**: Weekly on Tuesdays at 9:00 AM EST

### Dependency Grouping
Dependencies are grouped by ecosystem and type:

#### Backend Groups
- **Production Dependencies**: FastAPI, Uvicorn, Pydantic, SQLAlchemy, etc.
- **Development Dependencies**: pytest, mypy, black, isort, etc.

#### Frontend Groups
- **Next.js Ecosystem**: Next.js and related packages
- **React Ecosystem**: React, React DOM, and type definitions
- **UI Dependencies**: Radix UI components, Tailwind CSS, etc.
- **Testing Dependencies**: Testing Library, Jest, Playwright

### Auto-merge Configuration
Configure auto-merge for patch updates on low-risk dependencies:

1. Go to **Settings** → **General** → **Pull Requests**
2. Enable **Allow auto-merge**
3. Set up auto-merge rules in `.github/workflows/dependabot-auto-merge.yml` (optional)

## GitHub Secrets Management

### Required Secrets for CI/CD

#### Development Environment
```
AWS_ACCESS_KEY_ID              # AWS credentials for App Runner
AWS_SECRET_ACCESS_KEY          # AWS secret key
DATABASE_URL_DEV               # Development database connection
REDIS_URL_DEV                  # Development Redis connection
ANTHROPIC_API_KEY_DEV          # Development Claude API key
PINECONE_API_KEY_DEV           # Development Pinecone API key
CLERK_SECRET_KEY_DEV           # Development Clerk secret
CLERK_PUBLISHABLE_KEY_DEV      # Development Clerk public key
JWT_SECRET_KEY_DEV             # Development JWT secret
VERCEL_TOKEN                   # Vercel deployment token
VERCEL_ORG_ID                  # Vercel organization ID
VERCEL_PROJECT_ID              # Vercel project ID
```

#### Production Environment
```
DATABASE_URL_PROD              # Production database connection
REDIS_URL_PROD                 # Production Redis connection
ANTHROPIC_API_KEY_PROD         # Production Claude API key
PINECONE_API_KEY_PROD          # Production Pinecone API key
CLERK_SECRET_KEY_PROD          # Production Clerk secret
CLERK_PUBLISHABLE_KEY_PROD     # Production Clerk public key
JWT_SECRET_KEY_PROD            # Production JWT secret
```

#### Optional Monitoring & Notifications
```
CODECOV_TOKEN                  # Code coverage reporting
LHCI_GITHUB_APP_TOKEN         # Lighthouse CI integration
SLACK_WEBHOOK_URL             # Deployment notifications
SENTRY_DSN                    # Error tracking
```

### Secret Security Best Practices

1. **Rotation Schedule**: Rotate all API keys every 90 days
2. **Environment Separation**: Use completely different keys for dev/prod
3. **Least Privilege**: Each key should have minimal required permissions
4. **Audit Trail**: Regularly review secret access and usage

## Repository Settings

### General Settings

Navigate to **Settings** → **General** and configure:

#### Features
- ✅ **Wikis**: Enabled for documentation
- ✅ **Issues**: Enabled for bug tracking
- ✅ **Sponsorship**: Disabled (unless fundraising)
- ✅ **Preserve this repository**: Enabled
- ✅ **Discussions**: Enabled for community

#### Pull Requests
- ✅ **Allow merge commits**: Enabled
- ✅ **Allow squash merging**: Enabled (default)
- ✅ **Allow rebase merging**: Disabled
- ✅ **Always suggest updating pull request branches**: Enabled
- ✅ **Allow auto-merge**: Enabled
- ✅ **Automatically delete head branches**: Enabled

#### Archives
- ✅ **Include Git LFS objects in archives**: Enabled

### Pages Settings

If using GitHub Pages for documentation:

1. Go to **Settings** → **Pages**
2. **Source**: Deploy from a branch
3. **Branch**: `gh-pages` or `docs/`
4. **Custom domain**: `docs.eloquentai.com` (optional)

## Security Configuration

### Code Scanning (Advanced Security)

Enable GitHub Advanced Security features:

1. Go to **Settings** → **Security & analysis**
2. Enable the following:

#### Dependency Review
- ✅ **Dependency graph**: Enabled
- ✅ **Dependabot alerts**: Enabled
- ✅ **Dependabot security updates**: Enabled

#### Code Scanning
- ✅ **Code scanning**: Enabled
- ✅ **CodeQL analysis**: Enabled (via workflow)

#### Secret Scanning
- ✅ **Secret scanning**: Enabled
- ✅ **Secret scanning for partner patterns**: Enabled
- ✅ **Secret scanning for users**: Enabled

### Security Policies

Create and maintain security documentation:

1. **SECURITY.md**: Security policy and vulnerability reporting
2. **Code of Conduct**: Community guidelines
3. **Contributing Guidelines**: Security-focused contribution rules

### Vulnerability Management

#### Security Advisories
- Monitor **Security** tab for advisories
- Set up notifications for critical vulnerabilities
- Establish response times: Critical (24h), High (72h), Medium (1 week)

#### Security Updates
- Enable automatic security updates via Dependabot
- Configure security-only update schedules
- Monitor security update notifications

## Solo Developer Access Management

### Simplified Access Structure

For solo development, team-based access control is eliminated:

#### Repository Access
```yaml
solo-developer:
  permission: admin
  access: full repository control
  bypass: all protection rules when needed
```

### Code Owners (Optional)

For solo development, CODEOWNERS file is optional but can be useful for documentation:

```gitattributes
# Solo developer owns all code
* @[your-username]

# Optional: Specific ownership for documentation
/docs/ @[your-username]
README.md @[your-username]
SECURITY.md @[your-username]
```

### Access Control (Solo Developer)

#### Simplified Permissions
- **Full admin access**: Complete control over repository
- **Branch protection bypass**: Ability to override rules when necessary
- **Direct push capability**: Can push directly to any branch if needed
- **Emergency procedures**: No approval required for hotfixes

#### Security Considerations for Solo Development
- **Enable 2FA**: Protect your GitHub account with two-factor authentication
- **Regular key rotation**: Rotate API keys and secrets regularly
- **Backup repository**: Maintain offsite backups of critical code
- **Document decisions**: Keep records of important architectural choices

## Environment Configuration

### GitHub Environments (Solo Developer - Simplified)

Configure deployment environments without team-based restrictions:

#### Development Environment
- **Required reviewers**: 0
- **Wait timer**: 0 minutes
- **Allowed branches**: `dev`
- **Protection**: Minimal (fast iteration)

#### Production Environment (Simplified)
- **Required reviewers**: 0 (solo developer decision)
- **Wait timer**: 0 minutes (can add manual delay if desired)
- **Allowed branches**: `main` only
- **Protection**: Status checks only

**Note**: Environment protection rules have been disabled in workflows for solo development. You can re-enable them by uncommenting the `environment:` sections in deployment workflows.

## Monitoring and Alerting

### GitHub Notifications

Configure notification settings for:

#### Repository Activity
- New pull requests
- Failed CI/CD runs
- Security alerts
- Dependabot updates

#### Security Notifications
- New vulnerabilities
- Secret scanning alerts
- Code scanning findings

### External Integrations

Consider integrating with:
- **Slack**: For team notifications
- **PagerDuty**: For production alerts
- **Sentry**: For error monitoring
- **DataDog**: For performance monitoring

## Maintenance and Updates

### Monthly Tasks
- [ ] Review and update branch protection rules
- [ ] Audit repository access permissions
- [ ] Review security scan results
- [ ] Update team assignments and code owners

### Quarterly Tasks
- [ ] Rotate API keys and secrets
- [ ] Review and update security policies
- [ ] Audit dependency update patterns
- [ ] Performance review of CI/CD pipelines

### Annual Tasks
- [ ] Comprehensive security audit
- [ ] Review and update access control policies
- [ ] Evaluate new GitHub features and security tools
- [ ] Update team structure and permissions

## Troubleshooting

### Common Issues

#### Branch Protection Not Working
1. Check admin override settings
2. Verify required status checks are spelled correctly
3. Ensure status checks are actually running

#### Dependabot PRs Not Created
1. Check Dependabot configuration syntax
2. Verify repository permissions for Dependabot
3. Check if manual dependency updates are blocking

#### CI/CD Failures
1. Check required secrets are configured
2. Verify branch names match workflow triggers
3. Check for resource limits or rate limiting

#### Security Scan False Positives
1. Review and configure scan sensitivity
2. Use allowlists for known safe dependencies
3. Add suppressions for false positives with justification

For additional support, create an issue in the repository or contact the DevOps team.
