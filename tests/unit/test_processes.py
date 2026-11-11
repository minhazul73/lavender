from unittest.mock import patch

from server.services.processes import _parse_time_str, get_top_processes


def test_parse_time_str():
    assert _parse_time_str("0:05") == 5
    assert _parse_time_str("12:34") == 754
    assert _parse_time_str("1:10:05") == 4205
    assert _parse_time_str("1h00") == 3600
    assert _parse_time_str("2h30") == 9000
    assert _parse_time_str("1d02") == 93600
    assert _parse_time_str("1d") == 86400
    assert _parse_time_str("invalid") == 0


def test_get_top_processes_busybox_time_units():
    mock_busybox_output = (
        "PID USER TIME COMMAND\n"
        "10 root 1h00 init\n"
        "20 user 1d02 long_running_daemon\n"
        "30 user 0:45 short_task\n"
    )
    with patch("server.services.processes.run_command", return_value=(0, mock_busybox_output, "")):
        procs = get_top_processes(sort_by="pid")
        assert len(procs) == 3
        proc_map = {p["pid"]: p for p in procs}
        assert proc_map[10]["cpu_time"] == 3600
        assert proc_map[10]["time"] == "1h00"
        assert proc_map[20]["cpu_time"] == 93600
        assert proc_map[20]["time"] == "1d02"
        assert proc_map[30]["cpu_time"] == 45
        assert proc_map[30]["time"] == "0:45"



def test_get_top_processes_limit_and_sort():
    mock_ps_output = (
        "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
        "root         1  0.1  0.2  20000  4000 ?        Ss   10:00   0:05 /sbin/init\n"
        "user      1000 15.5  5.0 100000 50000 pts/1    R+   10:05   1:30 python main.py\n"
        "user      1001  2.0 12.0 200000 120000 pts/2   S    10:06   0:15 node server.js\n"
        "user      1002 45.0  1.0  50000 10000 pts/3    R    10:07   3:00 heavy_task\n"
    )

    with patch("server.services.processes.run_command", return_value=(0, mock_ps_output, "")):
        # Sort by CPU top 2
        top_cpu = get_top_processes(sort_by="cpu", limit=2)
        assert len(top_cpu) == 2
        assert top_cpu[0]["pid"] == 1002
        assert top_cpu[1]["pid"] == 1000

        # Sort by MEM top 2
        top_mem = get_top_processes(sort_by="mem", limit=2)
        assert len(top_mem) == 2
        assert top_mem[0]["pid"] == 1001
        assert top_mem[1]["pid"] == 1000

        # Sort by PID top 2
        top_pid = get_top_processes(sort_by="pid", limit=2)
        assert len(top_pid) == 2
        assert top_pid[0]["pid"] == 1
        assert top_pid[1]["pid"] == 1000
