# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.x     | ✅ active development |

Until v1.0, only the latest minor receives security fixes.

## Reporting a vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Use one of these private channels:

- **GitHub private vulnerability reporting:** https://github.com/sssurendra99/weekplan/security/advisories/new
- **Email:** sumalsurendra1999@gmail.com with subject line starting `WeekPlan security:`

Expected response times:

- **Acknowledgment:** within 7 days
- **Triage and severity assessment:** within 30 days
- **Fix or mitigation timeline:** communicated in triage response

Please include:

- Affected version (commit hash if from `main`)
- Reproduction steps
- Impact assessment (what an attacker could achieve)
- Suggested fix, if any
- Whether you'd like public credit

## Scope

**In scope:**

- Code in this repository
- Default Flatpak build configuration
- Google OAuth credential and token handling
- SQLite database access patterns

**Out of scope:**

- Vulnerabilities in upstream dependencies (please report to the upstream project; we'll bump versions when patches are available)
- Issues in the user's local environment unless WeekPlan misuses it
- Social engineering attacks
- Issues requiring local access AND admin/root privileges

## Disclosure policy

We follow coordinated disclosure:

- Once a fix is released, we'll publicly credit the reporter (unless anonymity is preferred)
- 90-day default disclosure window from initial report
- Critical issues affecting credential handling are prioritized

## Hall of fame

Researchers who have helped secure WeekPlan will be credited here.

*(No reports yet — be the first!)*
