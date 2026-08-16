"""
Hermes status and info helpers.
"""
from dashboard.dependencies import get_hermes_version, get_hermes_skills


def get_hermes_status() -> dict:
    """Get comprehensive Hermes status."""
    return {
        "version": get_hermes_version(),
        "skills": get_hermes_skills(),
        "skills_count": len(get_hermes_skills()),
    }
