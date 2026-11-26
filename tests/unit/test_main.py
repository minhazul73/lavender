from unittest.mock import patch

from server.main import run


def test_run_default():
    with patch("uvicorn.run") as mock_run:
        run()
        mock_run.assert_called_once_with(
            "server.main:app",
            host="127.0.0.1",
            port=8080,
            reload=False,
        )


def test_run_custom_arguments():
    with patch("uvicorn.run") as mock_run:
        run(host="0.0.0.0", port=9090)
        mock_run.assert_called_once_with(
            "server.main:app",
            host="0.0.0.0",
            port=9090,
            reload=False,
        )
