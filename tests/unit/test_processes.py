"""
Unit tests for dashboard.services.processes.
"""

from unittest.mock import patch, mock_open

from dashboard.services import processes as procs


class TestTopProcesses:
    @patch("dashboard.services.processes.run_command")
    def test_procps_format_sorted_by_mem(self, mock_run):
        ps_out = (
            "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
            "root           1  0.0  0.1  16764  2048 ?        Ss   12:00   0:01 /sbin/init\n"
            "rahat       1234 10.0  5.0 100000 20480 ?        S    12:01   0:10 python3 app.py\n"
        )
        mock_run.return_value = (0, ps_out, "")
        with patch(
            "builtins.open", mock_open(read_data="MemTotal:        3500000 kB\n")
        ):
            result = procs.get_top_processes(sort_by="mem", limit=0)
        assert result[0]["pid"] == 1234
        assert result[0]["mem"] == 20480
        assert result[1]["pid"] == 1

    @patch("dashboard.services.processes.run_command")
    def test_limit_truncates(self, mock_run):
        ps_out = (
            "USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND\n"
            "root 1 0.0 0.1 16764 2048 ? Ss 12:00 0:01 init\n"
            "rahat 2 0.0 0.1 16764 2048 ? Ss 12:00 0:01 bash\n"
        )
        mock_run.return_value = (0, ps_out, "")
        with patch("builtins.open", mock_open(read_data="MemTotal: 3500000 kB\n")):
            result = procs.get_top_processes(limit=1)
        assert len(result) == 1

    @patch("dashboard.services.processes.run_command")
    def test_ps_failure_returns_error(self, mock_run):
        mock_run.return_value = (1, "", "ps: command not found")
        result = procs.get_top_processes()
        assert len(result) == 1
        assert "error" in result[0]


class TestSystemLoad:
    def test_parses_loadavg_and_uptime(self):
        loadavg_fh = mock_open(read_data="0.50 0.40 0.30 2/450 12345\n").return_value
        uptime_fh = mock_open(read_data="86400.0 172800.0\n").return_value
        with patch("builtins.open", side_effect=[loadavg_fh, uptime_fh]):
            load = procs.get_system_load()
        assert load["1min"] == 0.50
        assert load["5min"] == 0.40
        assert load["15min"] == 0.30
        assert load["uptime_seconds"] == 86400.0
        assert load["uptime_formatted"] == "1d 0h 0m"


class TestKillProcess:
    @patch("dashboard.services.processes.run_sudo_command")
    def test_kill_success(self, mock_sudo):
        mock_sudo.return_value = (0, "", "")
        res = procs.kill_process(1234, signal=9)
        assert res["success"] is True
        assert res["pid"] == 1234
        assert res["signal"] == 9

    @patch("dashboard.services.processes.run_sudo_command")
    def test_kill_failure(self, mock_sudo):
        mock_sudo.return_value = (1, "", "No such process")
        res = procs.kill_process(99999)
        assert res["success"] is False
        assert res["error"] == "No such process"


class TestMemoryInfo:
    def test_parses_meminfo(self):
        meminfo = "MemTotal:   3500000 kB\nMemFree:   1000000 kB\n"
        with patch("builtins.open", mock_open(read_data=meminfo)):
            info = procs.get_memory_info()
        assert info["MemTotal"] == "3500000"
        assert info["MemFree"] == "1000000"

    def test_missing_meminfo(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            info = procs.get_memory_info()
        assert "error" in info


class TestMemoryHuman:
    @patch("dashboard.services.processes.run_command")
    def test_parses_free_and_percent(self, mock_run):
        free_out = (
            "              total        used        free\n"
            "Mem:          3.4G        2.0G        1.4G\n"
            "Swap:         0B          0B          0B\n"
        )
        mock_run.return_value = (0, free_out, "")
        meminfo = "MemTotal:   3500000 kB\nMemAvailable:   1500000 kB\n"
        with patch("builtins.open", mock_open(read_data=meminfo)):
            res = procs.get_memory_human()
        assert res["parsed"]["total"] == "3.4G"
        assert res["parsed"]["used"] == "2.0G"
        assert res["parsed"]["free"] == "1.4G"
        assert "percent" in res["parsed"]
