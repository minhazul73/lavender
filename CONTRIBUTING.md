# Contributing to Lavender

Thank you for your interest in contributing! This document outlines how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/lavender.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Test locally
6. Push and open a Pull Request

## Development Setup

```bash
cd lavender
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn dashboard.main:app --host 0.0.0.0 --port 8080 --reload
```

## Code Style

- **Python:** Follow PEP 8, use type hints where possible
- **JavaScript:** Vanilla JS, no frameworks — keep it lightweight
- **CSS:** Minimal, dark theme, no frameworks
- **Templates:** Jinja2, keep logic minimal in templates

## What to Contribute

- Bug fixes
- New features (system monitoring, service management)
- Documentation improvements
- UI/UX enhancements
- ARM64 / mobile SoC compatibility fixes

## Pull Request Guidelines

1. Keep changes focused and small
2. Test on actual hardware if possible
3. Update README if adding new features
4. Document new API endpoints
5. Don't break existing functionality

## Code of Conduct

Be respectful. This is a community project built for learning and practical use.

## Questions?

Open an issue for discussion before major changes.
