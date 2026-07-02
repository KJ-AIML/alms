# Security Policy

## Reporting a Vulnerability

Please report security vulnerabilities privately using [GitHub's private vulnerability reporting](https://github.com/KJ-AIML/alms/security/advisories/new) (Security tab -> "Report a vulnerability") rather than a public issue.

Include:
- Affected version / commit
- Steps to reproduce
- Impact assessment (what an attacker could do)

## Supported Versions

Only the latest release on `main` is supported. There is no long-term-support branch.

## Known Configuration Risks

ALMS ships secure-by-default validation for production mode (`Settings.validate_production_settings()`, enforced at startup), but a few things are the deploying team's responsibility:

- `SECRET_KEY` and `ALLOWED_HOSTS` are validated at startup and will fail fast if left as unsafe defaults.
- `X_API_KEY`: if unset, `APIKeyMiddleware` enforces no authentication at all (a warning is logged in production, but startup does not fail, since some deployments intentionally handle auth upstream). Set `X_API_KEY` unless you have auth handled elsewhere.
- `DATABASE_ENABLED=True` is the default; the `/api/v1/health/ready` endpoint will report `503` until a real database is reachable.

See `.env.example` for the full set of configuration flags.
