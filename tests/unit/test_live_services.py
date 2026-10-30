import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from dashboard.services.live import (
    CPUFreqCollector,
    CPUCoreInfo,
    BatteryCollector,
    CollectorStats,
    LiveMonitor,
    MetricCollector,
    NetworkRateCollector,
    RAMCollector,
    RingBuffer,
    ThermalCollector,
    _calc_cpu_usage,
    _get_loadavg,
    _parse_proc_stat,
    _read_file,
    _read_float,
    _read_int,
    get_live_monitor,
)

# ---------------------------------------------------------------------------
# Shared file helpers
# ---------------------------------------------------------------------------


class TestFileHelpers(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data="  42  \n")
    def test_read_file_success(self, _mock_open):
        self.assertEqual(_read_file("/proc/something"), "42")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_read_file_missing_returns_none(self, _mock_open):
        self.assertIsNone(_read_file("/nonexistent/path"))

    @patch("builtins.open", side_effect=PermissionError)
    def test_read_file_permission_returns_none(self, _mock_open):
        self.assertIsNone(_read_file("/root/only"))

    @patch("dashboard.services.live._read_file", return_value="123")
    def test_read_int_success(self, _mock_rf):
        self.assertEqual(_read_int("/sys/x"), 123)

    @patch("dashboard.services.live._read_file", return_value=None)
    def test_read_int_missing_uses_default(self, _mock_rf):
        self.assertEqual(_read_int("/sys/x", default=7), 7)
        self.assertEqual(_read_int("/sys/x"), 0)

    @patch("dashboard.services.live._read_file", return_value="not-a-number")
    def test_read_int_bad_value_uses_default(self, _mock_rf):
        self.assertEqual(_read_int("/sys/x", default=9), 9)

    @patch("dashboard.services.live._read_file", return_value="3.14")
    def test_read_float_success(self, _mock_rf):
        self.assertAlmostEqual(_read_float("/sys/x"), 3.14)

    @patch("dashboard.services.live._read_file", return_value="abc")
    def test_read_float_bad_value_uses_default(self, _mock_rf):
        self.assertAlmostEqual(_read_float("/sys/x", default=1.5), 1.5)

    @patch(
        "dashboard.services.live._read_file", return_value="0.50 1.00 2.00 1/100 12345"
    )
    def test_get_loadavg_indexes(self, _mock_rf):
        self.assertAlmostEqual(_get_loadavg(0), 0.5)
        self.assertAlmostEqual(_get_loadavg(1), 1.0)
        self.assertAlmostEqual(_get_loadavg(2), 2.0)

    @patch("dashboard.services.live._read_file", return_value=None)
    def test_get_loadavg_missing_returns_zero(self, _mock_rf):
        self.assertEqual(_get_loadavg(0), 0.0)

    @patch("dashboard.services.live._read_file", return_value="0.50 1.00")
    def test_get_loadavg_out_of_range_returns_zero(self, _mock_rf):
        self.assertEqual(_get_loadavg(5), 0.0)


# ---------------------------------------------------------------------------
# RingBuffer
# ---------------------------------------------------------------------------


class TestRingBuffer(unittest.TestCase):
    def test_append_and_read(self):
        rb = RingBuffer(3)
        rb.append(1.0)
        rb.append(2.0)
        self.assertEqual(list(rb), [1.0, 2.0])
        self.assertEqual(len(rb), 2)
        self.assertEqual(rb.values(), [1.0, 2.0])

    def test_overflow_evicts_oldest(self):
        rb = RingBuffer(3)
        for v in (1.0, 2.0, 3.0, 4.0, 5.0):
            rb.append(v)
        self.assertEqual(list(rb), [3.0, 4.0, 5.0])
        self.assertEqual(len(rb), 3)

    def test_is_empty(self):
        rb = RingBuffer(3)
        self.assertTrue(rb.is_empty)
        rb.append(1.0)
        self.assertFalse(rb.is_empty)

    def test_iteration_order(self):
        rb = RingBuffer(4)
        for v in (10, 20, 30):
            rb.append(v)
        self.assertEqual([v for v in rb], [10, 20, 30])


# ---------------------------------------------------------------------------
# /proc/stat parsing + usage math
# ---------------------------------------------------------------------------


def _stat_sample(total: int, idle_total: int) -> dict:
    return {"total": total, "idle_total": idle_total}


class TestParseProcStat(unittest.TestCase):
    SAMPLE = """\
cpu  1000 20 300 8000 50 10 20 0 100 5
cpu0 500 10 150 4000 20 5 10 0 50 2
cpu1 500 10 150 4000 30 5 10 0 50 3
intr 12345
"""

    @patch("dashboard.services.live._read_file", return_value=None)
    def test_missing_file_returns_empty(self, _mock_rf):
        self.assertEqual(_parse_proc_stat(), [])

    @patch("dashboard.services.live._read_file", return_value="no cpu lines here\n")
    def test_no_cpu_lines_returns_empty(self, _mock_rf):
        self.assertEqual(_parse_proc_stat(), [])

    @patch("dashboard.services.live._read_file", return_value=SAMPLE)
    def test_parses_per_core(self, _mock_rf):
        cores = _parse_proc_stat()
        self.assertEqual(len(cores), 2)
        c0 = cores[0]
        # guest (100) subtracted from user to avoid double count
        self.assertEqual(c0["user"], 500 - 50)
        self.assertEqual(c0["nice"], 10 - 2)
        self.assertEqual(
            c0["total"], (500 - 50) + (10 - 2) + 150 + 4000 + 20 + 5 + 10 + 0 + 50 + 2
        )
        self.assertEqual(c0["idle_total"], 4000 + 20)

    @patch(
        "dashboard.services.live._read_file",
        return_value="cpu  100 0 0 900 0 0 0 0 0 0\ncpu2 100 0 0 900 0 0 0 0 0 0\n",
    )
    def test_sparse_cores_get_none_slots(self, _mock_rf):
        cores = _parse_proc_stat()
        self.assertEqual(len(cores), 3)
        self.assertIsNone(cores[0])
        self.assertIsNone(cores[1])
        self.assertIsNotNone(cores[2])

    @patch(
        "dashboard.services.live._read_file",
        return_value="cpu0 100 0 0 900\n",
    )
    def test_short_lines_are_padded(self, _mock_rf):
        cores = _parse_proc_stat()
        self.assertEqual(cores[0]["total"], 1000)
        self.assertEqual(cores[0]["idle"], 900)


class TestCalcCpuUsage(unittest.TestCase):
    def test_normal_calculation(self):
        prev = _stat_sample(total=1000, idle_total=500)
        curr = _stat_sample(total=2000, idle_total=600)
        # (1000 - 100) / 1000 * 100 = 90%
        self.assertAlmostEqual(_calc_cpu_usage(prev, curr), 90.0)

    def test_missing_sample_returns_none(self):
        self.assertIsNone(_calc_cpu_usage(None, _stat_sample(100, 50)))
        self.assertIsNone(_calc_cpu_usage(_stat_sample(100, 50), None))

    def test_zero_total_delta_returns_zero(self):
        prev = _stat_sample(1000, 500)
        curr = _stat_sample(1000, 500)
        self.assertEqual(_calc_cpu_usage(prev, curr), 0.0)

    def test_all_idle_returns_zero(self):
        prev = _stat_sample(1000, 1000)
        curr = _stat_sample(2000, 2000)
        self.assertEqual(_calc_cpu_usage(prev, curr), 0.0)


# ---------------------------------------------------------------------------
# CPUFreqCollector
# ---------------------------------------------------------------------------


class TestCPUFreqCollector(unittest.IsolatedAsyncioTestCase):
    def _make(self):
        c = CPUFreqCollector()
        c._cpu_dir = "/fake/cpu"
        return c

    def test_discover_cpus_sorted_with_capacity(self):
        c = self._make()
        with patch("os.path.isdir") as mock_isdir, patch(
            "os.listdir", return_value=["cpu2", "cpu0", "cpu1", "cpu7", "online"]
        ), patch(
            "dashboard.services.live._read_int",
            side_effect=lambda path, default=0: (
                1
                if path.endswith("/online")
                else {
                    "/fake/cpu/cpu0/cpu_capacity": 0,
                    "/fake/cpu/cpu1/cpu_capacity": 0,
                    "/fake/cpu/cpu2/cpu_capacity": 700,
                    "/fake/cpu/cpu7/cpu_capacity": 1024,
                }.get(path, 0)
            ),
        ):
            mock_isdir.side_effect = lambda p: (
                p == "/fake/cpu" or p.endswith("/cpufreq")
            )
            c._discover_cpus()

        self.assertEqual([x.core for x in c._cpus], [0, 1, 2, 7])
        self.assertEqual(c._cpus[2].capacity, 700)
        self.assertEqual(c._cpus[3].capacity, 1024)  # core 7 is 4th in list
        self.assertTrue(c._has_cpufreq)

    def test_discover_cpus_offline_core_skipped(self):
        c = self._make()
        with patch("os.path.isdir") as mock_isdir, patch(
            "os.listdir", return_value=["cpu0", "cpu1"]
        ), patch(
            "dashboard.services.live._read_int",
            side_effect=lambda path, default=0: (0 if "cpu1/online" in path else 1),
        ):
            mock_isdir.side_effect = lambda p: p == "/fake/cpu"
            c._discover_cpus()

        self.assertEqual([x.core for x in c._cpus], [0])
        self.assertFalse(c._has_cpufreq)

    def test_discover_cpus_missing_dir_noop(self):
        c = self._make()
        with patch("os.path.isdir", return_value=False):
            c._discover_cpus()
        self.assertEqual(c._cpus, [])

    async def test_collect_no_cores(self):
        c = self._make()
        c._cpus = []
        result = await c.collect()
        self.assertEqual(result["cpus"], [])
        self.assertEqual(result["count"], 0)

    async def test_collect_first_sample_and_usage(self):
        c = self._make()
        c._cpus = [CPUCoreInfo(core=0), CPUCoreInfo(core=1, capacity=100)]
        c._has_cpufreq = True
        c._cpus_last_update = time.monotonic()  # skip re-discovery

        samples_a = [_stat_sample(1000, 500), _stat_sample(1000, 1000)]
        samples_b = [_stat_sample(2000, 600), _stat_sample(2000, 2000)]
        with patch(
            "dashboard.services.live._read_int",
            side_effect=lambda path, default=0: (
                2000000 if "cpu0" in path else 1800000
            ),
        ), patch(
            "dashboard.services.live._read_file",
            side_effect=lambda path: "schedutil" if "cpu0" in path else "performance",
        ), patch(
            "dashboard.services.live._parse_proc_stat",
            side_effect=[samples_a, samples_b],
        ), patch(
            "dashboard.services.live._get_loadavg",
            side_effect=lambda i: (0.1, 0.2, 0.3)[i],
        ):
            first = await c.collect()
            second = await c.collect()
        self.assertEqual(first["count"], 2)
        self.assertEqual(first["primary_frequency_mhz"], 2000.0)
        self.assertTrue(first["cpufreq_available"])
        self.assertAlmostEqual(first["load1"], 0.1)
        self.assertAlmostEqual(first["load5"], 0.2)
        self.assertAlmostEqual(first["load15"], 0.3)
        self.assertAlmostEqual(first["per_core_usage"][0]["usage"], 0.0)
        self.assertEqual(first["cpus"][0]["frequency_khz"], 2000000)
        self.assertEqual(first["cpus"][0]["governor"], "schedutil")

        # second sample: core0 (1000-100)/1000 = 90%, core1 all-idle = 0%
        self.assertAlmostEqual(second["per_core_usage"][0]["usage"], 90.0)
        self.assertAlmostEqual(second["per_core_usage"][1]["usage"], 0.0)

    async def test_collect_missing_cpufreq_reports_none_freq(self):
        c = self._make()
        c._cpus = [CPUCoreInfo(core=0)]
        c._has_cpufreq = False
        c._cpus_last_update = time.monotonic()
        with patch("dashboard.services.live._read_int", return_value=0), patch(
            "dashboard.services.live._read_file", return_value=None
        ), patch("dashboard.services.live._parse_proc_stat", return_value=[]), patch(
            "dashboard.services.live._get_loadavg", return_value=0.0
        ):
            result = await c.collect()
        self.assertIsNone(result["cpus"][0]["frequency_mhz"])
        self.assertIsNone(result["primary_frequency_mhz"])
        self.assertFalse(result["cpufreq_available"])
        self.assertEqual(result["per_core_usage"], [])


# ---------------------------------------------------------------------------
# RAMCollector
# ---------------------------------------------------------------------------


def _meminfo_text(
    total=8000000,
    free=1000000,
    avail=2000000,
    buffers=100000,
    cached=500000,
    swap_total=2000000,
    swap_free=1500000,
):
    lines = [
        f"MemTotal:       {total} kB",
        f"MemFree:        {free} kB",
        f"MemAvailable:   {avail} kB",
        f"Buffers:        {buffers} kB",
        f"Cached:         {cached} kB",
        f"SwapTotal:      {swap_total} kB",
        f"SwapFree:       {swap_free} kB",
        "garbage line without colon",
        "HugePages_Total:  not-a-number",
    ]
    return "\n".join(lines)


class TestRAMCollector(unittest.IsolatedAsyncioTestCase):
    def test_parse_meminfo(self):
        c = RAMCollector()
        with patch("dashboard.services.live._read_file", return_value=_meminfo_text()):
            parsed = c._parse_meminfo()
        self.assertEqual(parsed["MemTotal"], 8000000)
        self.assertEqual(parsed["MemFree"], 1000000)
        self.assertEqual(parsed["SwapFree"], 1500000)

    def test_parse_meminfo_missing_file(self):
        c = RAMCollector()
        with patch("dashboard.services.live._read_file", return_value=None):
            self.assertEqual(c._parse_meminfo(), {})

    async def test_collect_metrics(self):
        c = RAMCollector()
        with patch("dashboard.services.live._read_file", return_value=_meminfo_text()):
            result = await c.collect()
        self.assertEqual(result["total"], 8000000)
        self.assertEqual(result["used"], 6000000)  # total - avail
        self.assertAlmostEqual(result["used_pct"], 75.0)
        self.assertEqual(result["swap_used"], 500000)
        self.assertEqual(result["buffers"], 100000)
        self.assertEqual(result["cached"], 500000)

    async def test_collect_falls_back_to_free_when_no_available(self):
        c = RAMCollector()
        text = "MemTotal:       1000 kB\nMemFree:        400 kB\n"
        with patch("dashboard.services.live._read_file", return_value=text):
            result = await c.collect()
        self.assertEqual(result["available"], 400)
        self.assertEqual(result["used"], 600)

    async def test_collect_zero_total_no_division_error(self):
        c = RAMCollector()
        with patch(
            "dashboard.services.live._read_file", return_value="MemTotal: 0 kB\n"
        ):
            result = await c.collect()
        self.assertEqual(result["used_pct"], 0.0)

    async def test_collect_empty_meminfo_returns_empty_dict(self):
        c = RAMCollector()
        with patch("dashboard.services.live._read_file", return_value=None):
            self.assertEqual(await c.collect(), {})


# ---------------------------------------------------------------------------
# ThermalCollector
# ---------------------------------------------------------------------------


class TestThermalCollector(unittest.IsolatedAsyncioTestCase):
    async def test_collect_no_sources(self):
        c = ThermalCollector()
        with patch("os.path.isdir", return_value=False):
            self.assertEqual(await c.collect(), [])

    async def test_collect_hwmon_zone(self):
        c = ThermalCollector()

        def fake_isdir(path):
            return path == "/sys/class/hwmon"

        def fake_read_file(path):
            if path.endswith("/name"):
                return "cpuss0-thermal"
            if path.endswith("/temp1_label"):
                return "CPU SS0"
            return None

        def fake_read_int(path, default=0):
            return 45000 if path.endswith("/temp1_input") else 0

        with patch("os.path.isdir", side_effect=fake_isdir), patch(
            "os.listdir", return_value=["hwmon2"]
        ), patch(
            "dashboard.services.live._read_file", side_effect=fake_read_file
        ), patch(
            "dashboard.services.live._read_int", side_effect=fake_read_int
        ):
            zones = await c.collect()

        self.assertEqual(len(zones), 1)
        z = zones[0]
        self.assertEqual(z["display_name"], "CPU SS0 (Gold/Big)")
        self.assertEqual(z["temp_millicelsius"], 45000)
        self.assertAlmostEqual(z["temp_celsius"], 45.0)
        self.assertFalse(z["warning"])
        self.assertFalse(z["crit"])

    async def test_collect_warning_and_crit_thresholds(self):
        c = ThermalCollector()

        def fake_read_int(path, default=0):
            return 95000 if path.endswith("/temp1_input") else 0

        with patch(
            "os.path.isdir", side_effect=lambda p: p == "/sys/class/hwmon"
        ), patch("os.listdir", return_value=["hwmon2"]), patch(
            "dashboard.services.live._read_file",
            side_effect=lambda p: "cpu0-thermal" if p.endswith("/name") else None,
        ), patch(
            "dashboard.services.live._read_int", side_effect=fake_read_int
        ):
            zones = await c.collect()

        self.assertTrue(zones[0]["warning"])
        self.assertTrue(zones[0]["crit"])

    async def test_collect_dedupes_across_sources(self):
        """Same normalized type from hwmon and legacy /sys/class/thermal is
        reported once."""
        c = ThermalCollector()

        def fake_isdir(path):
            return path in ("/sys/class/hwmon", "/sys/class/thermal")

        def fake_listdir(path):
            if path == "/sys/class/hwmon":
                return ["hwmon2"]
            return ["thermal_zone0"]

        def fake_read_file(path):
            if path.endswith("/name"):
                return "cpu0-thermal"
            if path.endswith("/type"):
                return "cpu0-thermal"
            return None

        def fake_read_int(path, default=0):
            if path.endswith("/temp1_input") or path.endswith("/temp"):
                return 40000
            return 0

        with patch("os.path.isdir", side_effect=fake_isdir), patch(
            "os.listdir", side_effect=fake_listdir
        ), patch(
            "dashboard.services.live._read_file", side_effect=fake_read_file
        ), patch(
            "dashboard.services.live._read_int", side_effect=fake_read_int
        ):
            zones = await c.collect()

        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["type"], "cpu0-thermal")


# ---------------------------------------------------------------------------
# BatteryCollector
# ---------------------------------------------------------------------------


BATT_READS = {
    "capacity": 85,
    "online": 1,
    "temp": 315,  # < 1000 -> degrees C * 10
    "voltage_now": 4000000,  # uV
    "power_now": 0,
    "current_now": 1500000,  # uA
    "energy_full": 50000000,  # uWh
    "energy_full_design": 50000000,
    "energy_now": 42500000,
    "charge_full": 0,
    "charge_full_design": 0,
    "charge_now": 0,
}
BATT_TEXTS = {
    "status": "Charging",
    "serial_number": "SN12345",
    "manufacturer": "LG Chem",
    "model_name": "BL-46",
    "uevent": "POWER_SUPPLY_FULL=100\nPOWER_SUPPLY_ICON=battery-full\n",
}


def _batt_read_int(path, default=0):
    for key, val in BATT_READS.items():
        if f"/{key}" in path:
            return val
    return default


def _batt_read_file(path):
    for key, val in BATT_TEXTS.items():
        if path.endswith(f"/{key}"):
            return val
    return None


class TestBatteryCollector(unittest.IsolatedAsyncioTestCase):
    def test_discover_batteries(self):
        c = BatteryCollector()
        with patch("os.path.isdir", return_value=False):
            self.assertEqual(c._discover_batteries(), [])
        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=["bat0", "usb", "qcom-battery", "wlan0"]
        ):
            self.assertEqual(c._discover_batteries(), ["bat0", "qcom-battery"])

    async def test_collect_sysfs_full(self):
        c = BatteryCollector()
        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=["bat0"]
        ), patch(
            "dashboard.services.live._read_int", side_effect=_batt_read_int
        ), patch(
            "dashboard.services.live._read_file", side_effect=_batt_read_file
        ):
            result = c._collect_sysfs()

        self.assertEqual(result["percentage"], 85)
        self.assertEqual(result["state"], "charging")
        self.assertTrue(result["charging"])
        self.assertFalse(result["discharging"])
        self.assertTrue(result["online"])
        self.assertAlmostEqual(result["temperature"], 31.5)
        self.assertAlmostEqual(result["voltage"], 4.0)
        # power_now=0 -> derived from current_now * voltage
        self.assertAlmostEqual(result["energy_rate"], 1500000 * 4000000 / 1e12)
        self.assertAlmostEqual(result["energy"], 42.5)
        self.assertAlmostEqual(result["energy_full"], 50.0)
        self.assertAlmostEqual(result["capacity"], 100.0)
        self.assertEqual(result["serial"], "SN12345")
        self.assertEqual(result["vendor"], "LG Chem")
        self.assertEqual(result["model"], "BL-46")
        self.assertEqual(result["icon_name"], "battery-full")
        self.assertTrue(result["has_history"])
        self.assertEqual(result["battery_level"], "85%")
        self.assertEqual(result["battery_capacity_str"], "100.0%")

    async def test_collect_sysfs_no_batteries(self):
        c = BatteryCollector()
        with patch("os.path.isdir", return_value=False):
            result = c._collect_sysfs()
        self.assertIsNone(result["percentage"])
        self.assertEqual(result["state"], "unknown")
        # No battery at all: derived strings stay at their empty defaults
        self.assertEqual(result["battery_capacity_str"], "")
        self.assertFalse(result["online"])

    async def test_collect_sysfs_millicelsius_temperature(self):
        """temp > 1000 is interpreted as millidegrees C."""
        c = BatteryCollector()
        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=["bat0"]
        ), patch(
            "dashboard.services.live._read_int",
            side_effect=lambda p, d=0: (
                31500 if p.endswith("/temp") else _batt_read_int(p, d)
            ),
        ), patch(
            "dashboard.services.live._read_file", side_effect=_batt_read_file
        ):
            result = c._collect_sysfs()
        self.assertAlmostEqual(result["temperature"], 31.5)

    async def test_collect_sysfs_merges_multiple_batteries(self):
        """Two cells: percentages averaged, max voltage/energy_full kept."""
        c = BatteryCollector()

        def fake_read_int(path, default=0):
            if "capacity" in path:
                return 80 if "bat0" in path else 90
            # remaining fields read from the bat0 templates
            return _batt_read_int(path.replace("bat1", "bat0"), default)

        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=["bat0", "bat1"]
        ), patch("dashboard.services.live._read_int", side_effect=fake_read_int), patch(
            "dashboard.services.live._read_file", side_effect=_batt_read_file
        ):
            result = c._collect_sysfs()
        self.assertEqual(result["percentage"], 85)  # (80 + 90) // 2

    async def test_collect_upower_supplements_sysfs(self):
        c = BatteryCollector()
        original = BatteryCollector._collect_sysfs
        BatteryCollector._collect_sysfs = lambda self: {
            "percentage": None,
            "state": "unknown",
            "temperature": 30.0,
            "voltage": 3.9,
            "energy_rate": None,
            "time_to_full": None,
            "time_to_empty": None,
            "battery_state": "unknown",
            "battery_level": "",
            "battery_capacity_str": "",
        }
        upower_data = {
            "percentage": 91,
            "state": "discharging",
            "time_to_empty": "3.7 hours",
            "energy_rate": 5.5,
        }
        try:
            with patch.object(
                BatteryCollector, "_collect_upower", lambda self: upower_data
            ):
                result = await c.collect()
        finally:
            BatteryCollector._collect_sysfs = original
        self.assertEqual(result["percentage"], 91)
        self.assertEqual(result["state"], "discharging")
        self.assertTrue(result["discharging"])
        self.assertFalse(result["charging"])
        self.assertEqual(result["time_to_empty"], "3.7 hours")
        self.assertAlmostEqual(result["energy_rate"], 5.5)
        self.assertEqual(result["battery_level"], "91%")
        self.assertEqual(result["battery_state"], "discharging")
        # sysfs value kept when present
        self.assertAlmostEqual(result["temperature"], 30.0)
        self.assertAlmostEqual(result["voltage"], 3.9)

    async def test_collect_upower_unavailable_keeps_sysfs(self):
        c = BatteryCollector()
        original = BatteryCollector._collect_sysfs
        BatteryCollector._collect_sysfs = lambda self: {
            "percentage": 77,
            "state": "charging",  # charging=True derived from state
            "energy_rate": 0.0,
            "time_to_empty": "1 h",
            "battery_state": "charging",
            "battery_level": "",
            "battery_capacity_str": "",
        }
        try:
            with patch.object(BatteryCollector, "_collect_upower", lambda self: {}):
                result = await c.collect()
        finally:
            BatteryCollector._collect_sysfs = original
        self.assertEqual(result["percentage"], 77)
        self.assertTrue(result["charging"])
        self.assertEqual(result["battery_level"], "77%")

    def test_collect_upower_parses_upower_output(self):
        c = BatteryCollector()
        c._upower_checked = True
        c._upower_available = True
        c._upower_device = "/org/freedesktop/UPower/devices/battery_BAT0"
        upower_out = (
            "  native-path:          BAT0\n"
            "  vendor:               LG Chem\n"
            "  model:                BL-46\n"
            "  state:                discharging\n"
            "  warning level:        none\n"
            "  energy:               42.5 Wh\n"
            "  energy-full:          50 Wh\n"
            "  energy-rate:          5.5 W\n"
            "  voltage:              3.9 V\n"
            "  time to empty:        3.7 hours\n"
            "  percentage:           85%\n"
            "  capacity:             98.5%\n"
            "  temperature:          30.1 degrees C\n"
            "  has history:          yes\n"
            "  icon-name:            battery-80\n"
        )
        with patch("subprocess.check_output", return_value=upower_out.encode()):
            result = c._collect_upower()
        self.assertEqual(result["percentage"], 85)
        self.assertEqual(result["state"], "discharging")
        self.assertAlmostEqual(result["energy"], 42.5)
        self.assertAlmostEqual(result["energy_full"], 50.0)
        self.assertAlmostEqual(result["energy_rate"], 5.5)
        self.assertAlmostEqual(result["voltage"], 3.9)
        self.assertAlmostEqual(result["capacity"], 98.5)
        self.assertAlmostEqual(result["temperature"], 30.1)
        self.assertEqual(result["time_to_empty"], "3.7 hours")
        self.assertTrue(result["has_history"])
        self.assertEqual(result["icon_name"], "battery-80")

    def test_collect_upower_unavailable_returns_empty(self):
        c = BatteryCollector()
        with patch("subprocess.run", side_effect=FileNotFoundError("no upower")):
            self.assertEqual(c._collect_upower(), {})

    def test_collect_upower_command_fails_returns_empty(self):
        c = BatteryCollector()
        c._upower_checked = True
        c._upower_available = True
        c._upower_device = "/org/freedesktop/UPower/devices/battery_BAT0"
        with patch(
            "subprocess.check_output",
            side_effect=FileNotFoundError("no upower"),
        ):
            self.assertEqual(c._collect_upower(), {})

    def test_get_upower_device_filters_line_power(self):
        c = BatteryCollector()
        with patch(
            "subprocess.check_output",
            return_value=(
                "/org/freedesktop/UPower/devices/line_power_AC\n"
                "/org/freedesktop/UPower/devices/battery_BAT0\n"
            ).encode(),
        ):
            self.assertEqual(
                c._get_upower_device(), "/org/freedesktop/UPower/devices/battery_BAT0"
            )

    def test_get_upower_device_no_battery_returns_none(self):
        c = BatteryCollector()
        with patch(
            "subprocess.check_output",
            return_value=b"/org/freedesktop/UPower/devices/line_power_AC\n",
        ):
            self.assertIsNone(c._get_upower_device())


# ---------------------------------------------------------------------------
# NetworkRateCollector
# ---------------------------------------------------------------------------


def _net_dev_line(iface: str, rx_bytes: int, tx_bytes: int) -> str:
    """Build a /proc/net/dev line: iface + 8 rx fields + 8 tx fields.
    Index 1 of the split parts is rx_bytes, index 9 is tx_bytes (matches
    NetworkRateCollector._read_network_counters)."""
    rx = [str(rx_bytes)] + ["0"] * 7
    tx = [str(tx_bytes)] + ["0"] * 7
    return f"{iface}: " + " ".join(rx + tx)


PROC_NET_DEV = "\n".join(
    [
        "Inter-|   Receive                                                |  Transmit",
        " face |bytes    packets errs drop fifo frame compressed multicast"
        "|bytes    packets errs drop fifo colls carrier compressed",
        _net_dev_line("lo", 1234567, 1234567),
        _net_dev_line("wlan0", 99999999, 88888888),
    ]
)

PROC_NET_ROUTE = """\
Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow  IRTT
wlan0\t00000000\t0102A8C0\t0003\t0\t0\t0\t00000000\t0\t0\t0
"""


class TestNetworkRateCollector(unittest.IsolatedAsyncioTestCase):
    def test_read_network_counters(self):
        c = NetworkRateCollector()
        with patch("dashboard.services.live._read_file", return_value=PROC_NET_DEV):
            counters = c._read_network_counters()
        self.assertEqual(counters["lo"], (1234567, 1234567))
        self.assertEqual(counters["wlan0"], (99999999, 88888888))

    def test_read_network_counters_missing(self):
        c = NetworkRateCollector()
        with patch("dashboard.services.live._read_file", return_value=None):
            self.assertEqual(c._read_network_counters(), {})

    def test_default_route_interface(self):
        with patch("dashboard.services.live._read_file", return_value=PROC_NET_ROUTE):
            self.assertEqual(NetworkRateCollector._default_route_interface(), "wlan0")

    def test_default_route_interface_no_file(self):
        with patch("dashboard.services.live._read_file", return_value=None):
            self.assertIsNone(NetworkRateCollector._default_route_interface())

    def test_interface_operstate(self):
        with patch("dashboard.services.live._read_file", return_value="Up"):
            self.assertEqual(NetworkRateCollector._interface_operstate("wlan0"), "up")
        with patch("dashboard.services.live._read_file", return_value=None):
            self.assertEqual(NetworkRateCollector._interface_operstate("wlan0"), "")

    @patch("os.path.exists", return_value=False)
    def test_interface_category_priority(self, _mock_exists):
        f = NetworkRateCollector._interface_category_priority
        self.assertEqual(f("wlan0"), 1)
        self.assertEqual(f("wlp1s0"), 1)
        self.assertEqual(f("eth0"), 2)
        self.assertEqual(f("ens33"), 2)
        self.assertEqual(f("usb0"), 3)
        self.assertEqual(f("rndis0"), 3)
        self.assertEqual(f("rmnet0"), 4)
        self.assertEqual(f("wwan0"), 4)
        self.assertEqual(f("wg0"), 8)
        self.assertEqual(f("tailscale0"), 8)
        self.assertEqual(f("sit0"), 5)

    @patch("os.path.exists", return_value=True)
    def test_wireless_sysfs_forces_wifi_priority(self, _mock_exists):
        self.assertEqual(NetworkRateCollector._interface_category_priority("sit0"), 1)

    async def test_collect_first_sample_zero_rates(self):
        c = NetworkRateCollector()
        with patch(
            "dashboard.services.live._read_file", return_value=PROC_NET_DEV
        ), patch.object(
            NetworkRateCollector, "_primary_interface", return_value="wlan0"
        ):
            result = await c.collect()
        self.assertEqual(result["iface"], "wlan0")
        self.assertEqual(result["rx_rate_bps"], 0.0)
        self.assertEqual(result["tx_rate_bps"], 0.0)

    async def test_collect_second_sample_computes_rate(self):
        c = NetworkRateCollector()
        counters = [
            {"wlan0": (1000, 500)},
            {"wlan0": (1100, 550)},
        ]
        with patch(
            "dashboard.services.live.NetworkRateCollector._read_network_counters",
            side_effect=counters,
        ), patch.object(
            NetworkRateCollector, "_primary_interface", return_value="wlan0"
        ):
            first = await c.collect()
            c._prev_time -= 2.0  # simulate 2 seconds elapsed between samples
            second = await c.collect()
        self.assertEqual(first["rx_rate_bps"], 0.0)
        # (1100 - 1000) / 2.0s = 50 B/s rx; (550 - 500) / 2.0s = 25 B/s tx
        self.assertAlmostEqual(second["rx_rate_bps"], 50.0, delta=1.0)
        self.assertAlmostEqual(second["tx_rate_bps"], 25.0, delta=1.0)
        self.assertEqual(second["rx_bytes"], 1100)

    async def test_collect_no_interface(self):
        c = NetworkRateCollector()
        with patch(
            "dashboard.services.live._read_file", return_value=None
        ), patch.object(NetworkRateCollector, "_primary_interface", return_value=None):
            result = await c.collect()
        self.assertEqual(result["iface"], "none")
        self.assertEqual(result["rx_rate_bps"], 0)

    def test_primary_interface_prefers_wifi_over_vpn(self):
        c = NetworkRateCollector()
        counters = {"lo": (1, 1), "wlan0": (100, 100), "tailscale0": (5000000, 5000000)}
        with patch.object(
            NetworkRateCollector, "_default_route_interface", return_value=None
        ), patch.object(
            NetworkRateCollector, "_interface_operstate", return_value="up"
        ), patch(
            "os.path.exists", return_value=False
        ):
            self.assertEqual(c._primary_interface(counters), "wlan0")

    def test_primary_interface_default_route_beats_idle_wifi(self):
        c = NetworkRateCollector()
        counters = {"lo": (1, 1), "eth0": (10, 10), "wlan0": (1000, 1000)}
        with patch.object(
            NetworkRateCollector, "_default_route_interface", return_value="eth0"
        ), patch.object(
            NetworkRateCollector, "_interface_operstate", return_value="up"
        ), patch(
            "os.path.exists", return_value=False
        ):
            self.assertEqual(c._primary_interface(counters), "eth0")

    def test_primary_interface_excludes_virtual_and_picks_fallback(self):
        c = NetworkRateCollector()
        counters = {"lo": (1, 1), "docker0": (5, 5), "veth12": (9, 9)}
        with patch("os.path.exists", return_value=False):
            # Only excluded candidates -> sorted non-lo fallback
            self.assertEqual(c._primary_interface(counters), "docker0")

    def test_primary_interface_only_loopback_returns_none(self):
        c = NetworkRateCollector()
        with patch("os.path.exists", return_value=False):
            self.assertIsNone(c._primary_interface({"lo": (1, 1)}))

    def test_primary_interface_down_interface_penalized(self):
        c = NetworkRateCollector()
        counters = {"eth0": (1000, 1000), "eth1": (10, 10)}
        with patch.object(
            NetworkRateCollector, "_default_route_interface", return_value=None
        ), patch.object(
            NetworkRateCollector,
            "_interface_operstate",
            side_effect=lambda i: "down" if i == "eth0" else "up",
        ), patch(
            "os.path.exists", return_value=False
        ):
            # eth0 has more traffic but is down; eth1 is up
            self.assertEqual(c._primary_interface(counters), "eth1")


# ---------------------------------------------------------------------------
# MetricCollector base class
# ---------------------------------------------------------------------------


class _FakeCollector(MetricCollector):
    def __init__(self, exc=None, samples=None):
        super().__init__(10, 5, "fake")
        self._exc = exc
        self._samples = list(samples or [])
        self.collect_calls = 0

    async def collect(self):
        self.collect_calls += 1
        if self._exc is not None:
            raise self._exc
        if self._samples:
            return self._samples.pop(0)
        return {"v": 1}


class TestMetricCollectorBase(unittest.IsolatedAsyncioTestCase):
    async def test_base_collect_raises_not_implemented(self):
        c = MetricCollector(10, 5, "x")
        with self.assertRaises(NotImplementedError):
            await c.collect()

    async def test_run_loop_collects_and_clears_errors(self):
        c = _FakeCollector(samples=[{"v": 1}, {"v": 2}, {"v": 3}])
        loop = asyncio.get_running_loop()
        c.start(loop)
        await asyncio.sleep(0.06)
        c.stop()
        self.assertGreaterEqual(c.collect_calls, 2)
        self.assertEqual(c.stats.errors_in_row, 0)
        self.assertIsNone(c.stats.last_error)

    async def test_run_loop_survives_repeated_errors(self):
        c = _FakeCollector(exc=ValueError("boom"))
        loop = asyncio.get_running_loop()
        c.start(loop)
        await asyncio.sleep(0.06)
        c.stop()
        self.assertGreaterEqual(c.stats.errors_in_row, 2)
        self.assertEqual(c.stats.last_error, "boom")
        self.assertGreaterEqual(c.collect_calls, 2)

    async def test_start_is_idempotent(self):
        c = _FakeCollector()
        loop = asyncio.get_running_loop()
        c.start(loop)
        first_task = c._task
        self.assertIsNotNone(first_task)
        c.start(loop)  # no-op while running
        self.assertIs(c._task, first_task)
        c.stop()

    async def test_stop_cancels_and_resets(self):
        c = _FakeCollector()
        loop = asyncio.get_running_loop()
        c.start(loop)
        task = c._task
        c.stop()
        self.assertIsNone(c._task)
        self.assertTrue(c._stop_event.is_set())
        await asyncio.sleep(0.02)  # let the cancellation propagate
        self.assertTrue(task.done())

    def test_stats_dataclass_defaults(self):
        s = CollectorStats()
        self.assertEqual(s.sample_count, 0)
        self.assertIsNone(s.last_error)
        self.assertEqual(s.errors_in_row, 0)


# ---------------------------------------------------------------------------
# LiveMonitor
# ---------------------------------------------------------------------------


class TestLiveMonitor(unittest.IsolatedAsyncioTestCase):
    @patch("dashboard.services.live.NetworkRateCollector")
    @patch("dashboard.services.live.BatteryCollector")
    @patch("dashboard.services.live.ThermalCollector")
    @patch("dashboard.services.live.RAMCollector")
    @patch("dashboard.services.live.CPUFreqCollector")
    def _make_monitor(self, cpu_cls, ram_cls, therm_cls, batt_cls, net_cls):
        m = LiveMonitor()
        m.cpu.start = MagicMock()
        m.ram.start = MagicMock()
        m.thermal.start = MagicMock()
        m.battery.start = MagicMock()
        m.network.start = MagicMock()
        m.cpu.stop = MagicMock()
        m.ram.stop = MagicMock()
        m.thermal.stop = MagicMock()
        m.battery.stop = MagicMock()
        m.network.stop = MagicMock()
        return m

    async def test_add_client_starts_all_collectors(self, *mocks):
        m = self._make_monitor(*mocks)
        await m.add_client()
        self.assertTrue(m._started)
        m.cpu.start.assert_called_once()
        m.ram.start.assert_called_once()
        m.thermal.start.assert_called_once()
        m.battery.start.assert_called_once()
        m.network.start.assert_called_once()

    async def test_remove_client_stops_when_last_leaves(self, *mocks):
        m = self._make_monitor(*mocks)
        await m.add_client()
        await m.remove_client()
        self.assertFalse(m._started)
        m.cpu.stop.assert_called_once()
        m.ram.stop.assert_called_once()
        m.thermal.stop.assert_called_once()
        m.battery.stop.assert_called_once()
        m.network.stop.assert_called_once()

    async def test_multiple_clients_keep_collectors_running(self, *mocks):
        m = self._make_monitor(*mocks)
        await m.add_client()
        await m.add_client()
        await m.remove_client()
        self.assertTrue(m._started)
        m.cpu.stop.assert_not_called()
        await m.remove_client()
        self.assertFalse(m._started)
        m.cpu.stop.assert_called_once()

    async def test_remove_without_clients_is_safe(self, *mocks):
        m = self._make_monitor(*mocks)
        await m.remove_client()  # no clients yet
        self.assertEqual(m._client_count, 0)
        self.assertFalse(m._started)
        m.cpu.stop.assert_not_called()

    async def test_getters_delegate_to_collectors(self, *mocks):
        m = self._make_monitor(*mocks)
        m.cpu.collect = AsyncMock(return_value={"cpu": 1})
        m.ram.collect = AsyncMock(return_value={"ram": 2})
        m.thermal.collect = AsyncMock(return_value=[{"z": 1}])
        m.battery.collect = AsyncMock(return_value={"bat": 3})
        m.network.collect = AsyncMock(return_value={"net": 4})

        self.assertEqual(await m.get_cpu(), {"cpu": 1})
        self.assertEqual(await m.get_ram(), {"ram": 2})
        self.assertEqual(await m.get_thermal(), [{"z": 1}])
        self.assertEqual(await m.get_battery(), {"bat": 3})
        self.assertEqual(await m.get_network(), {"net": 4})

        allm = await m.get_all_metrics()
        self.assertEqual(
            set(allm.keys()), {"cpu", "ram", "thermal", "battery", "network"}
        )
        self.assertEqual(allm["cpu"], {"cpu": 1})

    async def test_ensure_started_is_idempotent(self, *mocks):
        m = self._make_monitor(*mocks)
        await m.add_client()
        await m._ensure_started()
        self.assertEqual(m.cpu.start.call_count, 1)


class TestGetLiveMonitor(unittest.TestCase):
    def test_singleton(self):
        import dashboard.services.live as live_mod

        original = live_mod._live_monitor
        try:
            live_mod._live_monitor = None
            a = get_live_monitor()
            b = get_live_monitor()
            self.assertIs(a, b)
        finally:
            live_mod._live_monitor = original


if __name__ == "__main__":
    unittest.main()
