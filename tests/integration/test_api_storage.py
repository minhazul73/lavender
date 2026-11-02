import pytest
import os
import tempfile


@pytest.mark.asyncio
async def test_get_storage_disks(auth_client):
    res = await auth_client.get("/api/storage")
    assert res.status_code == 200
    data = res.json()
    assert "disks" in data
    assert isinstance(data["disks"], list)


@pytest.mark.asyncio
async def test_get_storage_bookmarks(auth_client):
    res = await auth_client.get("/api/storage/bookmarks")
    assert res.status_code == 200
    data = res.json()
    assert "bookmarks" in data
    assert "disks" in data
    assert len(data["bookmarks"]) > 0


@pytest.mark.asyncio
async def test_list_files_and_crud(auth_client):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file
        test_file = os.path.join(tmpdir, "hello.txt")
        with open(test_file, "w") as f:
            f.write("Hello, Lavender!")

        # List files
        res = await auth_client.get(f"/api/storage/files?path={tmpdir}")
        assert res.status_code == 200
        data = res.json()
        assert data["current_path"] == os.path.realpath(tmpdir)
        assert data["total_files"] == 1
        assert data["items"][0]["name"] == "hello.txt"

        # View file
        view_res = await auth_client.get(f"/api/storage/file/view?path={test_file}")
        assert view_res.status_code == 200
        vdata = view_res.json()
        assert vdata["is_text"] is True
        assert vdata["content"] == "Hello, Lavender!"

        # Save edit
        save_res = await auth_client.post(
            "/api/storage/file/save",
            json={"path": test_file, "content": "Updated content"}
        )
        assert save_res.status_code == 200

        with open(test_file, "r") as f:
            assert f.read() == "Updated content"

        # Create folder
        mkdir_res = await auth_client.post(
            "/api/storage/mkdir",
            json={"path": tmpdir, "name": "subfolder"}
        )
        assert mkdir_res.status_code == 200

        # Create file
        create_res = await auth_client.post(
            "/api/storage/file/create",
            json={"path": tmpdir, "name": "new.py", "content": "print('ok')"}
        )
        assert create_res.status_code == 200

        # Rename
        rename_res = await auth_client.post(
            "/api/storage/rename",
            json={"old_path": os.path.join(tmpdir, "new.py"), "new_name": "renamed.py"}
        )
        assert rename_res.status_code == 200
        assert os.path.exists(os.path.join(tmpdir, "renamed.py"))

        # Delete
        del_res = await auth_client.post(
            "/api/storage/delete",
            json={"paths": [os.path.join(tmpdir, "renamed.py"), os.path.join(tmpdir, "subfolder")]}
        )
        assert del_res.status_code == 200
        assert not os.path.exists(os.path.join(tmpdir, "renamed.py"))


@pytest.mark.asyncio
async def test_text_file_preview_various_extensions(auth_client):
    """Ensure non-.txt text files (source code, configs, yaml, extensionless) are previewable and editable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            "server.conf": "port = 8080\nworkers = 4",
            "script.sh": "#!/bin/bash\necho 'hello'",
            "config.yaml": "version: '3.8'\nservices:\n  app:\n    image: node",
            "data.json": '{"name": "Lavender", "active": true}',
            "hosts": "127.0.0.1 localhost\n::1 localhost",
        }
        for name, content in files.items():
            fpath = os.path.join(tmpdir, name)
            with open(fpath, "w") as f:
                f.write(content)

            # View file
            res = await auth_client.get(f"/api/storage/file/view?path={fpath}")
            assert res.status_code == 200
            data = res.json()
            assert data["is_text"] is True, f"{name} should be recognized as text"
            assert data["content"] == content

            # Save file edit
            save_res = await auth_client.post(
                "/api/storage/file/save",
                json={"path": fpath, "content": content + "\n# modified"}
            )
            assert save_res.status_code == 200
            with open(fpath, "r") as f:
                assert f.read() == content + "\n# modified"


@pytest.mark.asyncio
async def test_root_path_permissions_and_is_writable(auth_client):
    """Test listing / and reading /etc/hosts or /etc/fstab."""
    res = await auth_client.get("/api/storage/files?path=/")
    assert res.status_code == 200
    data = res.json()
    assert data["current_path"] == "/"
    assert len(data["items"]) > 0

    # View /etc/hosts (standard system file)
    if os.path.exists("/etc/hosts"):
        view_res = await auth_client.get("/api/storage/file/view?path=/etc/hosts")
        assert view_res.status_code == 200
        vdata = view_res.json()
        assert vdata["is_text"] is True
        assert vdata["content"] is not None

