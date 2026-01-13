# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in UES, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Email security concerns to boggsj52@gmail.com
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## What to Expect

- **Acknowledgment**: We'll acknowledge your report within 48 hours
- **Assessment**: We'll assess the vulnerability and determine its impact
- **Fix Timeline**: For confirmed vulnerabilities, we aim to release a fix within 30 days
- **Credit**: We'll credit you in the release notes (unless you prefer to remain anonymous)

## Scope

This security policy applies to:
- The UES Python package (API server and client library)
- The UES Web UI

## Out of Scope

- Vulnerabilities in dependencies (please report these to the respective projects)
- Issues in development/test environments only
- Social engineering attacks

## Security Best Practices

When deploying UES:
- Use HTTPS in production
- Configure CORS appropriately (`CORS_ORIGINS` environment variable)
- Keep dependencies updated
- Run the server behind a reverse proxy in production
