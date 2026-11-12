"""
Parser for /etc/passwd and /etc/group files.
"""
import grp

NON_LOGIN_SHELLS = {
    "/sbin/nologin",
    "/usr/sbin/nologin",
    "/bin/false",
    "/usr/bin/false",
    "/bin/sync",
    "/dev/null",
}


def parse_passwd_users(
    min_uid: int = 1000,
    exclude_nologin: bool = True,
    path: str = "/etc/passwd",
) -> list[dict]:
    """Parse /etc/passwd and return human users (uid >= min_uid)."""
    users = []
    try:
        with open(path, errors="replace") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 7:
                    try:
                        uid = int(parts[2])
                        gid = int(parts[3])
                    except ValueError:
                        continue
                    shell = parts[6]
                    if uid >= min_uid:
                        if exclude_nologin:
                            if uid == 65534 or shell in NON_LOGIN_SHELLS:
                                continue
                        users.append({
                            "name": parts[0],
                            "uid": uid,
                            "gid": gid,
                            "home": parts[5],
                            "shell": shell,
                            "comment": parts[4],
                        })
    except Exception:
        pass
    return users


def parse_all_passwd_users(path: str = "/etc/passwd") -> list[dict]:
    """Parse /etc/passwd and return all users with is_human flag."""
    users = []
    try:
        with open(path, errors="replace") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 7:
                    try:
                        uid = int(parts[2])
                        gid = int(parts[3])
                    except ValueError:
                        continue
                    shell = parts[6]
                    is_human = (uid >= 1000 and uid != 65534 and shell not in NON_LOGIN_SHELLS) or uid == 0
                    users.append({
                        "name": parts[0],
                        "uid": uid,
                        "gid": gid,
                        "home": parts[5],
                        "shell": shell,
                        "comment": parts[4],
                        "is_human": is_human,
                    })
    except Exception:
        pass
    return users


def parse_groups(path: str = "/etc/group") -> list[dict]:
    """Parse /etc/group and return all groups."""
    groups = []
    try:
        with open(path, errors="replace") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 4:
                    try:
                        gid = int(parts[2])
                    except ValueError:
                        continue
                    members = [m.strip() for m in parts[3].split(",") if m.strip()] if parts[3] else []
                    groups.append({
                        "name": parts[0],
                        "gid": gid,
                        "members": members,
                    })
    except Exception:
        pass
    return groups


def get_user_groups(username: str, primary_gid: int | None = None) -> list[str]:
    """Single-pass lookup for primary and secondary groups of a user."""
    groups: list[str] = []
    primary_group: str | None = None
    try:
        for g in grp.getgrall():
            if primary_gid is not None and g.gr_gid == primary_gid:
                primary_group = g.gr_name
            if username in g.gr_mem:
                groups.append(g.gr_name)
    except Exception:
        pass

    if primary_gid is not None and primary_group is None:
        try:
            primary_group = grp.getgrgid(primary_gid).gr_name
        except Exception:
            pass

    if primary_group and primary_group not in groups:
        groups.insert(0, primary_group)

    return groups

