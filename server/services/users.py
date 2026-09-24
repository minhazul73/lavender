"""
User, session, and permission management service for Lavender.
"""
import os
import shutil
import subprocess
from typing import Optional

from server.dependencies import (
    parse_passwd_users,
    parse_all_passwd_users,
    parse_groups,
    parse_active_sessions,
    parse_login_history,
    get_current_user_info,
    read_sudoers,
    visudo_check,
    run_command,
    which,
)

# Known Linux groups and human-intelligible categorization
GROUP_METADATA = {
    # Privileged
    "wheel": ("Privileged", "Administrative / sudo / doas elevation privileges"),
    "sudo": ("Privileged", "Administrative / sudo execution privileges"),
    "docker": ("Privileged", "Control Docker containers and daemon without root"),
    "root": ("Privileged", "Superuser root account and access"),
    "adm": ("Privileged", "System monitoring and log inspection"),
    "lxd": ("Privileged", "LXD container hypervisor control"),

    # Phone & Hardware Subsystems
    "audio": ("Hardware", "Audio playback, microphone, and sound card access"),
    "video": ("Hardware", "GPU acceleration, display server, and framebuffer"),
    "netdev": ("Hardware", "Network configuration, Wi-Fi, and cellular modem"),
    "plugdev": ("Hardware", "USB OTG, portable drives, and plug-and-play devices"),
    "dialout": ("Hardware", "Serial communication, modem, and GPS devices"),
    "input": ("Hardware", "Touch screen, buttons, keyboard, and pointer devices"),
    "camera": ("Hardware", "Camera sensors and video capture (V4L2)"),
    "kvm": ("Hardware", "Kernel-based virtual machine acceleration"),
    "disk": ("Hardware", "Raw disk and block storage devices"),
    "bluetooth": ("Hardware", "Bluetooth controller and wireless audio"),
    "tty": ("Hardware", "Teletype terminals and serial consoles"),
    "cdrom": ("Hardware", "Optical drive access"),
    "dip": ("Hardware", "Dial-up IP / modem connection routing"),
    "lp": ("Hardware", "Line printer and printing subsystems"),
    "lpadmin": ("Hardware", "Configure printers and print queues"),

    # Service / Daemon Accounts
    "caddy": ("Services", "Caddy reverse proxy and web server"),
    "grafana": ("Services", "Grafana telemetry and dashboarding"),
    "netdata": ("Services", "Netdata real-time monitoring engine"),
    "messagebus": ("Services", "D-Bus system message communication bus"),
    "chrony": ("Services", "NTP time synchronization daemon"),
    "pipewire": ("Services", "PipeWire multimedia graph server"),
    "pulse": ("Services", "PulseAudio sound daemon"),
    "pulse-access": ("Services", "Direct PulseAudio daemon socket access"),
    "geoclue": ("Services", "GeoClue location provider"),
    "flatpak": ("Services", "Flatpak application sandboxing"),
    "colord": ("Services", "Color profile daemon"),
    "avahi": ("Services", "mDNS / Bonjour local network discovery"),
    "dnsmasq": ("Services", "Lightweight DHCP and DNS caching server"),
    "apache": ("Services", "Apache HTTP server daemon"),
    "nginx": ("Services", "NGINX web server and reverse proxy"),
    "postgres": ("Services", "PostgreSQL database daemon"),
    "redis": ("Services", "Redis in-memory caching engine"),
}


def get_user_ssh_path(username: str) -> str:
    """Get path to authorized_keys for a given user."""
    if username == "root":
        return "/root/.ssh/authorized_keys"
    return f"/home/{username}/.ssh/authorized_keys"


def get_user_ssh_keys(username: str) -> list[dict]:
    """Parse public keys in authorized_keys for a given user."""
    path = get_user_ssh_path(username)
    keys = []
    if not os.path.exists(path):
        return keys

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                key_type = ""
                key_data = ""
                comment = ""

                for i, p in enumerate(parts):
                    if p.startswith(("ssh-", "ecdsa-", "sk-ssh-", "sk-ecdsa-")):
                        key_type = p
                        if i + 1 < len(parts):
                            key_data = parts[i + 1]
                        if i + 2 < len(parts):
                            comment = " ".join(parts[i + 2:])
                        break

                if key_type:
                    preview = f"{key_data[:10]}...{key_data[-10:]}" if len(key_data) > 20 else key_data
                    keys.append({
                        "index": idx,
                        "type": key_type,
                        "preview": preview,
                        "comment": comment or "No comment",
                        "raw": line,
                    })
    except Exception:
        pass
    return keys


def add_user_ssh_key(username: str, key_content: str) -> bool:
    """Add a public key to the user's authorized_keys file."""
    clean_key = key_content.strip()
    if not clean_key or not any(clean_key.startswith(p) for p in ("ssh-", "ecdsa-", "sk-")):
        return False

    path = get_user_ssh_path(username)
    ssh_dir = os.path.dirname(path)

    try:
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n{clean_key}\n")
        os.chmod(path, 0o600)
        return True
    except Exception:
        return False


def delete_user_ssh_key(username: str, key_index: int) -> bool:
    """Delete a key at key_index in authorized_keys."""
    path = get_user_ssh_path(username)
    if not os.path.exists(path):
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if 0 <= key_index < len(lines):
            lines.pop(key_index)
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
    except Exception:
        pass
    return False


def get_home_storage_info(home_path: str) -> Optional[dict]:
    """Fast check of filesystem storage on the partition hosting home."""
    if not home_path or not os.path.isdir(home_path):
        return None
    try:
        total, used, free = shutil.disk_usage(home_path)
        percent = round((used / total) * 100, 1) if total > 0 else 0
        return {
            "total_gb": round(total / (1024 ** 3), 1),
            "used_gb": round(used / (1024 ** 3), 1),
            "free_gb": round(free / (1024 ** 3), 1),
            "percent_used": percent,
        }
    except Exception:
        return None


def get_human_users(current_username: Optional[str] = None) -> list[dict]:
    """Get list of enriched human interactive users."""
    raw_users = parse_passwd_users(min_uid=1000, exclude_nologin=True)
    all_groups = parse_groups()
    active_sessions = parse_active_sessions()
    active_user_names = {s["user"] for s in active_sessions}

    # Map username to groups
    user_to_groups = {}
    for g in all_groups:
        for m in g.get("members", []):
            user_to_groups.setdefault(m, []).append(g["name"])

    human_users = []
    for u in raw_users:
        uname = u["name"]
        groups = user_to_groups.get(uname, [])
        is_admin = ("wheel" in groups or "sudo" in groups or uname == "root" or u["uid"] == 0)
        is_current = (uname == current_username)
        is_active = uname in active_user_names
        home_path = u.get("home", "")
        home_exists = os.path.isdir(home_path)
        storage = get_home_storage_info(home_path) if home_exists else None
        ssh_keys = get_user_ssh_keys(uname)

        human_users.append({
            "name": uname,
            "uid": u["uid"],
            "gid": u["gid"],
            "home": home_path,
            "shell": u.get("shell", "/bin/sh"),
            "comment": u.get("comment", ""),
            "groups": groups,
            "is_admin": is_admin,
            "is_current": is_current,
            "is_active": is_active,
            "home_exists": home_exists,
            "home_storage": storage,
            "ssh_keys_count": len(ssh_keys),
        })

    return human_users


def get_system_users() -> list[dict]:
    """Get list of system / daemon users."""
    all_users = parse_all_passwd_users()
    all_groups = parse_groups()

    user_to_groups = {}
    for g in all_groups:
        for m in g.get("members", []):
            user_to_groups.setdefault(m, []).append(g["name"])

    system_users = []
    for u in all_users:
        if not u.get("is_human", False):
            uname = u["name"]
            system_users.append({
                "name": uname,
                "uid": u["uid"],
                "gid": u["gid"],
                "home": u.get("home", ""),
                "shell": u.get("shell", ""),
                "comment": u.get("comment", ""),
                "groups": user_to_groups.get(uname, []),
            })
    return system_users


def get_categorized_groups() -> list[dict]:
    """Parse /etc/group and classify groups into Privileged, Hardware, Services, System."""
    raw_groups = parse_groups()
    categorized = []

    for g in raw_groups:
        name = g["name"]
        gid = g["gid"]
        members = g.get("members", [])

        if name in GROUP_METADATA:
            cat, desc = GROUP_METADATA[name]
        elif name.startswith("systemd-") or name in ("avahi", "chrony", "caddy", "grafana", "netdata", "pulse", "pipewire"):
            cat = "Services"
            desc = f"Service daemon account for {name}"
        elif gid < 100 or name in ("bin", "daemon", "sys", "tty", "users", "nogroup", "nobody"):
            cat = "System"
            desc = "Internal Linux system group"
        else:
            cat = "General"
            desc = f"Local user / system group ({name})"

        categorized.append({
            "name": name,
            "gid": gid,
            "members": members,
            "category": cat,
            "description": desc,
            "member_count": len(members),
        })

    # Sort: Privileged first, Hardware second, Services third, then System/General
    order = {"Privileged": 0, "Hardware": 1, "Services": 2, "General": 3, "System": 4}
    categorized.sort(key=lambda x: (order.get(x["category"], 9), x["name"]))
    return categorized


def get_active_sessions() -> list[dict]:
    """Get active terminal and SSH sessions."""
    return parse_active_sessions()


def get_login_history(limit: int = 10) -> list[dict]:
    """Get recent login logs."""
    return parse_login_history(limit=limit)


def get_security_posture() -> dict:
    """Audit security and access posture."""
    has_sudo = which("sudo") is not None
    has_doas = which("doas") is not None
    visudo_ok, visudo_msg = visudo_check()

    # Check SSH daemon status
    sshd_active = False
    try:
        code, out, _ = run_command(["systemctl", "is-active", "sshd"], timeout=3)
        if code == 0 and "active" in out:
            sshd_active = True
        elif not sshd_active:
            code, out, _ = run_command(["systemctl", "is-active", "ssh"], timeout=3)
            sshd_active = (code == 0 and "active" in out)
    except Exception:
        pass

    # Inspect sshd_config
    root_ssh_login = "Unknown"
    password_auth = "Unknown"
    for cfg_path in ("/etc/ssh/sshd_config", "/etc/ssh/sshd_config.d"):
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("PermitRootLogin"):
                            parts = line.split()
                            if len(parts) >= 2:
                                root_ssh_login = parts[1]
                        elif line.startswith("PasswordAuthentication"):
                            parts = line.split()
                            if len(parts) >= 2:
                                password_auth = parts[1]
            except Exception:
                pass

    return {
        "elevation_engine": "sudo" if has_sudo else ("doas" if has_doas else "polkit/none"),
        "has_sudo": has_sudo,
        "has_doas": has_doas,
        "visudo_ok": visudo_ok,
        "visudo_msg": visudo_msg,
        "sshd_active": sshd_active,
        "root_ssh_login": root_ssh_login,
        "password_auth": password_auth,
    }


# Backwards compatibility wrappers
def get_users(min_uid: int = 1000) -> list[dict]:
    return parse_passwd_users(min_uid=min_uid, exclude_nologin=True)


def get_all_users() -> list[dict]:
    return parse_all_passwd_users()


def get_groups() -> list[dict]:
    return parse_groups()


def get_user_groups(username: str) -> list[str]:
    groups = parse_groups()
    user_groups = []
    for g in groups:
        if username in g.get("members", []):
            user_groups.append(g["name"])
    return user_groups


def get_current_user() -> dict:
    return get_current_user_info()


def get_sudoers_info() -> dict:
    sudoers_content = read_sudoers()
    visudo_ok, visudo_msg = visudo_check()
    return {
        "sudoers_available": bool(sudoers_content),
        "sudoers_content": sudoers_content,
        "visudo_ok": visudo_ok,
        "visudo_msg": visudo_msg,
    }
