from unittest.mock import patch

from server.main import run


def test_run_default():
    with patch("server.core.config.HOST", "127.0.0.1"), patch("server.core.config.PORT", 8080), patch("uvicorn.run") as mock_run:
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


def test_run_explicit_zero_port():
    with patch("server.core.config.PORT", 8080), patch("uvicorn.run") as mock_run:
        run(port=0)
        mock_run.assert_called_once_with(
            "server.main:app",
            host="127.0.0.1",
            port=0,
            reload=False,
        )
