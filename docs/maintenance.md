# Lavender Kanban Maintenance Cronjob

This document outlines the `lavender-kanban-maintenance` cronjob, its local execution, verification, and troubleshooting steps.

## Runbook: Local Execution & Verification

### Environment Variables

The cronjob relies on certain environment variables to function correctly, particularly for `pytest` execution. Ensure the following are set when running locally:

- `PYTHONPATH`: Should include the root of the `lavender` project (e.g., `/home/rahat/lavender`) so Python can find the `dashboard` and `tests` modules.

### Test Command

To verify the cronjob's functionality and `pytest` collection locally, use the following command from the `lavender` project root:

```bash
PYTHONPATH=$(pwd) pytest
```

This command ensures that `pytest` can discover and run all tests, simulating the cronjob's environment.

## Dependency Changes (pytest collection)

In a previous task (t_aef1d9b8), it was identified that `pytest` collection was failing due to missing runtime dependencies in the cron environment. Specifically, libraries like `httpx`, `itsdangerous`, and various components of the `FastAPI` stack were not available during the test run.

To resolve this, all project dependencies listed in `requirements.txt` were installed into the cronjob's execution environment. This ensures that `pytest` can import all necessary modules when collecting and running tests, preventing `ModuleNotFoundError` and similar import-related issues.

## Troubleshooting Pytest Collection Errors

If `pytest` collection or test execution fails within the cronjob or during local verification, consider the following common issues and checks:

### ModuleNotFoundError

This error indicates that Python cannot find a required module. Common causes include:

- **Incorrect `PYTHONPATH`**: Ensure `PYTHONPATH` is correctly set to include the root directory of the `lavender` project.
- **Missing Dependencies**: Verify that all dependencies listed in `requirements.txt` are installed in the environment where `pytest` is being run. You can reinstall them using `pip install -r requirements.txt`.
- **Virtual Environment Issues**: If using a virtual environment, ensure it's activated correctly or that the `python` executable within the cronjob's context points to the correct virtual environment's Python interpreter.

### Files to Check:

- `requirements.txt`: Contains the list of all project dependencies.
- `maintenance/daily.sh` (or equivalent cronjob script): Review how the Python environment is set up and how `pytest` is invoked.
- Cronjob logs: Check the output of the cronjob for specific error messages or stack traces.
