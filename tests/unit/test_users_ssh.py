import os
import tempfile
from unittest.mock import patch

from server.services.users import (
    _parse_ssh_key_type_and_data,
    build_user_to_groups_map,
    delete_user_ssh_key,
    get_human_users,
    get_system_users,
    get_user_ssh_keys,
)


def test_parse_ssh_key_type_and_data():
    """Verify parsing key type and public key data from standard and option-prefixed keys."""
    # Standard key
    t, d = _parse_ssh_key_type_and_data("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 user@host")
    assert t == "ssh-ed25519"
    assert d == "AAAAC3NzaC1lZDI1NTE5"

    # Option-prefixed key
    t, d = _parse_ssh_key_type_and_data('no-pty,from="10.0.0.1" ecdsa-sha2-nistp256 AAAAE2VjZHNh test@host')
    assert t == "ecdsa-sha2-nistp256"
    assert d == "AAAAE2VjZHNh"

    # Bare token has no key_data
    t, d = _parse_ssh_key_type_and_data("ssh-ed25519")
    assert t == "ssh-ed25519"
    assert d == ""

    # Invalid / comment line
    t, d = _parse_ssh_key_type_and_data("# comment line")
    assert t == ""
    assert d == ""


def test_delete_duplicate_keys_by_integer_index():
    """Verify deleting duplicate SSH keys targets the exact selected line index."""
    # Two identical keys on lines 0 and 2
    key_line = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG mock@test"
    content = f"{key_line}\n# middle comment\n{key_line}\n"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        with patch("server.services.users.get_user_ssh_path", return_value=temp_path):
            keys = get_user_ssh_keys("testuser")
            assert len(keys) == 2
            assert keys[0]["index"] == 0
            assert keys[1]["index"] == 2

            # Delete the second duplicate (index 2)
            assert delete_user_ssh_key("testuser", 2) is True

            # Verify line 0 is still present and line 2 was deleted
            with open(temp_path) as f:
                lines = f.readlines()
            assert len(lines) == 2
            assert lines[0].strip() == key_line
            assert lines[1].strip() == "# middle comment"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_option_prefixed_key_by_index_and_string():
    """Verify option-prefixed SSH keys can be matched by parsed key data and deleted."""
    opt_key = 'command="/usr/bin/backup",no-port-forwarding ssh-ed25519 AAAAC3backupKey backup@server'
    std_key = "ssh-rsa AAAAB3NzaC1yc2E standard@server"
    content = f"{opt_key}\n{std_key}\n"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        with patch("server.services.users.get_user_ssh_path", return_value=temp_path):
            # Test deleting by string match (without options, matching key_type and key_data)
            assert delete_user_ssh_key("testuser", "ssh-ed25519 AAAAC3backupKey") is True

            with open(temp_path) as f:
                remaining = f.readlines()
            assert len(remaining) == 1
            assert remaining[0].strip() == std_key
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_bare_token_rejected():
    """Verify passing a bare key-type token without key data does not delete anything."""
    content = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIG mock@test\n"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        with patch("server.services.users.get_user_ssh_path", return_value=temp_path):
            # Bare token must be rejected and not delete anything
            assert delete_user_ssh_key("testuser", "ssh-ed25519") is False

            with open(temp_path) as f:
                lines = f.readlines()
            assert len(lines) == 1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_exact_trimmed_string_match():
    """Verify exact trimmed-line matching removes the intended SSH key."""
    key1 = "ssh-ed25519 AAAAC3Key1 mock1@test"
    key2 = "ssh-ed25519 AAAAC3Key2 mock2@test"
    content = f"  {key1}  \n{key2}\n"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        with patch("server.services.users.get_user_ssh_path", return_value=temp_path):
            assert delete_user_ssh_key("testuser", key1) is True

            with open(temp_path) as f:
                remaining = f.readlines()
            assert len(remaining) == 1
            assert remaining[0].strip() == key2
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_comment_or_non_key_exact_match_rejected():
    """Verify comments and non-key lines are not deleted even on exact text match."""
    comment_line = "# Just an administrative comment"
    key1 = "ssh-ed25519 AAAAC3Key1 mock1@test"
    content = f"{comment_line}\n{key1}\n"

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(content)
        temp_path = tf.name

    try:
        with patch("server.services.users.get_user_ssh_path", return_value=temp_path):
            # Attempting to delete a comment line must be rejected
            assert delete_user_ssh_key("testuser", comment_line) is False

            with open(temp_path) as f:
                remaining = f.readlines()
            assert len(remaining) == 2
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_surrogateescape_and_atomic_replace():
    """Verify undecodable surrogate bytes on unchanged lines are preserved during key deletion."""
    raw_content = (
        b"# comment with invalid \xe9 byte\n"
        b"ssh-ed25519 AAAAC3Key1 mock1@test\n"
        b"ssh-ed25519 AAAAC3Key2 mock2@test\n"
    )
    with tempfile.NamedTemporaryFile("wb", delete=False) as tf:
        tf.write(raw_content)
        temp_path = tf.name

    try:
        with patch("server.services.users.get_user_ssh_path", return_value=temp_path):
            assert delete_user_ssh_key("testuser", "ssh-ed25519 AAAAC3Key1 mock1@test") is True

            with open(temp_path, "rb") as f:
                remaining_bytes = f.read()
            assert b"\xe9" in remaining_bytes
            assert b"AAAAC3Key1" not in remaining_bytes
            assert b"AAAAC3Key2" in remaining_bytes
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_build_user_to_groups_map_and_precomputed_group_map():
    mock_groups = [
        {"name": "sudo", "gid": 27, "members": ["alice", "bob"]},
        {"name": "docker", "gid": 999, "members": ["alice"]},
    ]
    group_map = build_user_to_groups_map(mock_groups)
    assert group_map == {
        "alice": ["sudo", "docker"],
        "bob": ["sudo"],
    }

    mock_human_passwd = [
        {"name": "alice", "uid": 1000, "gid": 1000, "home": "/home/alice", "shell": "/bin/bash", "comment": ""},
    ]
    with patch("server.services.users.parse_passwd_users", return_value=mock_human_passwd), \
         patch("server.services.users.parse_groups") as mock_parse_groups, \
         patch("server.services.users.parse_active_sessions", return_value=[]), \
         patch("server.services.users.get_user_ssh_keys", return_value=[]):
        users = get_human_users(group_map=group_map)
        assert len(users) == 1
        assert users[0]["name"] == "alice"
        assert users[0]["groups"] == ["sudo", "docker"]
        assert users[0]["is_admin"] is True
        mock_parse_groups.assert_not_called()

    mock_all_passwd = [
        {"name": "daemon", "uid": 1, "gid": 1, "home": "/usr/sbin", "shell": "/usr/sbin/nologin", "comment": "", "is_human": False},
    ]
    with patch("server.services.users.parse_all_passwd_users", return_value=mock_all_passwd), \
         patch("server.services.users.parse_groups") as mock_parse_groups:
        sys_users = get_system_users(group_map={"daemon": ["daemon_group"]})
        assert len(sys_users) == 1
        assert sys_users[0]["name"] == "daemon"
        assert sys_users[0]["groups"] == ["daemon_group"]
        mock_parse_groups.assert_not_called()

