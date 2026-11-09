import os
import tempfile
from unittest.mock import patch

from server.services.users import (
    _parse_ssh_key_type_and_data,
    delete_user_ssh_key,
    get_user_ssh_keys,
)


def test_parse_ssh_key_type_and_data():
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
