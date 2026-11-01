"""
Characterization tests for HTTP error codes in server/api/storage.py.
These tests lock in existing error-handling behaviour before D-002 extraction (T-028).
"""
import pytest
from unittest.mock import patch


class TestListFilesErrors:
    @pytest.mark.asyncio
    async def test_file_not_found_returns_404(self, auth_client):
        with patch("server.services.files.list_directory",
                   side_effect=FileNotFoundError("no such dir")):
            r = await auth_client.get("/api/storage/files?path=/nonexistent")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_permission_error_returns_403(self, auth_client):
        with patch("server.services.files.list_directory",
                   side_effect=PermissionError("denied")):
            r = await auth_client.get("/api/storage/files?path=/root")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_generic_error_returns_500(self, auth_client):
        with patch("server.services.files.list_directory",
                   side_effect=RuntimeError("unexpected")):
            r = await auth_client.get("/api/storage/files?path=/tmp")
        assert r.status_code == 500


class TestViewFileErrors:
    @pytest.mark.asyncio
    async def test_file_not_found_returns_404(self, auth_client):
        with patch("server.services.files.read_file_preview",
                   side_effect=FileNotFoundError("gone")):
            r = await auth_client.get("/api/storage/file/view?path=/no/such/file")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_permission_error_returns_403(self, auth_client):
        with patch("server.services.files.read_file_preview",
                   side_effect=PermissionError("no read")):
            r = await auth_client.get("/api/storage/file/view?path=/root/secret")
        assert r.status_code == 403
