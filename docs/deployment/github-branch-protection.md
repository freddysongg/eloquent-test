# GitHub Branch Protection Configuration - Solo Developer

## Overview

This document provides simplified GitHub branch protection rules optimized for solo development workflow while maintaining essential code quality and security standards. Team-based restrictions and collaborative features have been streamlined.

## Branch Structure

```
main (production)
├── dev (development/staging)
├── feature/* (feature branches)
├── hotfix/* (emergency fixes)
└── release/* (release candidates)
```

## Branch Protection Rules

### 🔒 Main Branch (Production) - Solo Developer

Navigate to: Settings → Branches → Add rule → Branch name pattern: `main`

#### Simplified Settings for Solo Development

**✅ Require a pull request before merging** (Optional)
- [ ] Require approvals: **0** (solo developer, no reviewers needed)
- [x] Dismiss stale pull request approvals when new commits are pushed
- [ ] Require review from CODEOWNERS (disabled for solo work)
- [ ] Restrict who can dismiss pull request reviews (not applicable)

**✅ Require status checks to pass before merging**
- [x] Require branches to be up to date before merging
- Essential status checks (simplified):
  - `backend-ci / backend-ci-summary`
  - `frontend-ci / frontend-ci-summary`
  - `integration-tests / integration-summary`
  - `security / security-summary`

**✅ Require conversation resolution before merging**
- [x] All conversations must be resolved

**✅ Require signed commits** (Optional)
- [ ] Disabled for easier solo development workflow

**✅ Require linear history** (Optional)
- [ ] Allow merge commits for simpler workflow

**✅ Include administrators**
- [ ] Allow administrators to bypass (solo developer flexibility)

**✅ Restrict who can push to matching branches**
- [ ] No restrictions (solo developer has full access)

**✅ Allow force pushes** (Solo Developer)
- [x] Enabled for administrators only (for emergency fixes)

**✅ Allow deletions**
- [ ] Disabled (protect against accidental deletion)

### 🚀 Dev Branch (Development) - Solo Developer

Navigate to: Settings → Branches → Add rule → Branch name pattern: `dev`

#### Simplified Settings for Solo Development

**✅ Require a pull request before merging** (Optional)
- [ ] Require approvals: **0** (solo developer convenience)
- [x] Dismiss stale pull request approvals when new commits are pushed
- [ ] Require review from CODEOWNERS (not applicable)

**✅ Require status checks to pass before merging**
- [x] Require branches to be up to date before merging
- Essential status checks (minimal for dev):
  - `backend-ci / test`
  - `frontend-ci / test`

**✅ Require conversation resolution before merging**
- [x] All conversations must be resolved

**✅ Require signed commits**
- [ ] Optional for dev branch

**✅ Require linear history**
- [ ] Allow merge commits for easier feature integration

**✅ Include administrators**
- [ ] Administrators can bypass for emergency fixes

**✅ Allow force pushes**
- [ ] Disabled

**✅ Allow deletions**
- [ ] Disabled

### 🔧 Feature Branches

Pattern: `feature/*`

- No protection rules (developers have full control)
- Must create PR to merge into `dev`
- Automatic deletion after merge

### 🚨 Hotfix Branches

Pattern: `hotfix/*`

**✅ Require a pull request before merging**
- [x] Require approvals: **1** (expedited for emergencies)
- Required status checks (minimal for speed):
  - `backend-ci / test (3.11)`
  - `frontend-ci / test (20.x)`
  - `security / secret-scanning`

## Automated Merge Rules

### Dependabot Auto-merge

Create `.github/auto-merge.yml`:

```yaml
# Auto-merge rules for Dependabot PRs
rules:
  - match:
      dependency_type: "development"
      update_type: "semver:patch"
    actions:
      merge:
        method: squash
        
  - match:
      dependency_type: "production"
      update_type: "security:patch"
    actions:
      merge:
        method: squash
        required_approvals: 1
```

## GitHub Settings Configuration

### General Repository Settings

**Settings → General:**
- [x] Allow squash merging
  - Default message: "Pull request title and description"
- [x] Allow rebase merging
- [ ] Allow merge commits (disabled for clean history)
- [x] Automatically delete head branches
- [x] Allow auto-merge
- [x] Suggest updating pull request branches

### Security Settings

**Settings → Security & analysis:**
- [x] Dependency graph
- [x] Dependabot alerts
- [x] Dependabot security updates
- [x] Code scanning alerts
- [x] Secret scanning
- [x] Secret scanning push protection

### Actions Settings

**Settings → Actions → General:**
- [x] Allow all actions and reusable workflows
- [x] Require approval for first-time contributors
- Workflow permissions: Read repository contents and packages

## Solo Developer Permissions

### Repository Access
- **Solo Developer**: Full admin access to repository
- **Collaborators** (if any): Write access for pair programming or consultations
- **Dependabot**: Automated dependency updates

### Permission Levels

| User Type | Repository | Actions | Packages | Security |
|-----------|------------|---------|----------|----------|
| Owner/Solo Dev | Admin | Write | Write | Admin |
| Occasional Collaborator | Write | Read | Read | Read |
| Dependabot | Write | Write | Write | Read |

## Deployment Protection Rules

### Production Environment

**Settings → Environments → production:**
- Required reviewers: Solo developer (self-approval)
- Deployment branches: Only `main`
- Environment secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `PRODUCTION_API_ENDPOINT`
  - `VERCEL_TOKEN`
  - `CLAUDE_API_KEY`
  - `PINECONE_API_KEY`

### Staging Environment

**Settings → Environments → staging:**
- Required reviewers: None (auto-deploy)
- Deployment branches: `dev`
- Auto-deploy on successful merge

## Enforcement Timeline

### Phase 1: Initial Setup (Week 1)
- Create branch structure
- Configure basic protection rules
- Set up team permissions

### Phase 2: Testing Period (Week 2)
- Enable all rules in "warning" mode
- Test workflow with sample PRs
- Adjust rules based on solo development needs

### Phase 3: Full Activation (Week 3+)
- Enable essential protection rules
- Optional: Signed commits (as needed)
- Flexible: Linear history (based on preference)

## Manual Configuration Steps

Since GitHub branch protection cannot be fully automated via API without proper authentication, follow these steps:

1. **Navigate to Repository Settings**
   ```
   https://github.com/[your-username]/eloquentai/settings
   ```

2. **Go to Branches Section**
   ```
   Settings → Branches
   ```

3. **Add Protection Rules**
   - Click "Add rule"
   - Enter branch name pattern
   - Configure settings as specified above
   - Click "Create" or "Save changes"

4. **Configure Collaborators (optional)**
   ```
   Settings → Manage access → Invite collaborators
   ```

5. **Set Up Environments**
   ```
   Settings → Environments → New environment
   ```

## CLI Commands for Setup

```bash
# Push dev branch to remote
git push -u origin dev

# Set default branch (optional, can do in GitHub UI)
gh repo edit --default-branch main

# Create branch protection (requires GitHub CLI with appropriate permissions)
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["continuous-integration/travis-ci"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true}' \
  --field restrictions='{"users":[],"teams":["release-managers"]}'
```

## Monitoring and Compliance

### Weekly Review Checklist
- [ ] Review bypass events in audit log
- [ ] Check for stale PRs requiring attention
- [ ] Verify all status checks are functioning
- [ ] Check Dependabot PR queue
- [ ] Review security alerts and vulnerabilities

### Monthly Security Audit
- [ ] Review branch protection settings
- [ ] Rotate API keys and secrets
- [ ] Check for unused deploy keys
- [ ] Review webhook configurations
- [ ] Update dependencies and security patches

## Emergency Procedures

### Hotfix Process
1. Create `hotfix/*` branch from `main`
2. Apply fix with minimal changes
3. Create PR (self-approval for emergencies)
4. Deploy to staging for validation
5. Fast-track to production after testing

### Break-Glass Procedure
For critical production issues:
1. Solo developer bypasses protection (logged in audit)
2. Direct push to main with immediate documentation
3. Deploy hotfix immediately
4. Post-incident review within 24 hours (self-review)

## Support and Documentation

- **GitHub Docs**: [Protected Branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- **Solo Developer**: Maintain personal incident log
- **Backup Contact**: Technical mentor or consultant (if applicable)

---

*Last Updated: 2025-08-24*
*Version: 1.0*
*Next Review: Monthly*
