"""
Network interface rate collector from /proc/net/dev and sysfs.
"""

from __future__ import annotations

import os
import time
from typing import Dict, Optional, Tuple

from server.core.config import SSE_NETWORK_INTERVAL_MS
from server.services.live_buffer import MetricCollector


def _read_file(path: str) -> Optional[str]:
    import server.services.live as live
    return live._read_file(path)


class NetworkRateCollector(MetricCollector):
    """Collects network interface counters from /proc/net/dev and computes
    rates (bytes/sec) by comparing consecutive samples.

    Uses a rolling delta: each sample stores current counters, next sample
    computes (new - old) / elapsed.
    """

    __slots__ = ("_interval_ms", "_buffer", "_stats", "_stop_event",
                 "_task", "_prev_counters", "_prev_time")

    def __init__(self, interval_ms: int = SSE_NETWORK_INTERVAL_MS,
                 history_size: int = 30) -> None:
        super().__init__(interval_ms, history_size, "network")
        self._prev_counters: Dict[str, Tuple[int, int]] = {}
        self._prev_time: float = 0.0

    async def collect(self) -> dict:
        """Return network rate for the primary non-loopback interface."""
        now = time.monotonic()
        counters = self._read_network_counters()

        iface = self._primary_interface(counters)
        if iface is None or iface not in counters:
            return {
                "iface": iface or "none",
                "rx_rate_bps": 0,
                "tx_rate_bps": 0,
            }

        rx_bytes, tx_bytes = counters[iface]
        rx_rate = 0.0
        tx_rate = 0.0

        if self._prev_time > 0 and iface in self._prev_counters:
            prev_rx, prev_tx = self._prev_counters[iface]
            elapsed = now - self._prev_time
            if elapsed > 0:
                rx_rate = (rx_bytes - prev_rx) / elapsed
                tx_rate = (tx_bytes - prev_tx) / elapsed

        self._prev_counters[iface] = (rx_bytes, tx_bytes)
        self._prev_time = now

        return {
            "iface": iface,
            "rx_bytes": rx_bytes,
            "tx_bytes": tx_bytes,
            "rx_rate_bps": rx_rate,
            "tx_rate_bps": tx_rate,
        }

    def _read_network_counters(self) -> Dict[str, Tuple[int, int]]:
        """Read /proc/net/dev, return {iface: (rx_bytes, tx_bytes)}."""
        counters: Dict[str, Tuple[int, int]] = {}
        text = _read_file("/proc/net/dev")
        if text is None:
            return counters
        lines = text.splitlines()
        # Skip header lines
        for line in lines[2:]:
            parts = line.split()
            if len(parts) < 10:
                continue
            iface = parts[0].rstrip(":")
            rx_bytes = int(parts[1])
            tx_bytes = int(parts[9])
            counters[iface] = (rx_bytes, tx_bytes)
        return counters

    @staticmethod
    def _default_route_interface() -> Optional[str]:
        """Find the interface with default gateway (Destination == 00000000) from /proc/net/route."""
        text = _read_file("/proc/net/route")
        if not text:
            return None
        for line in text.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "00000000":
                return parts[0]
        return None

    @staticmethod
    def _interface_operstate(iface: str) -> str:
        state = _read_file(f"/sys/class/net/{iface}/operstate")
        return state.lower() if state else ""

    @staticmethod
    def _interface_category_priority(iface: str) -> int:
        """Categorize interface into priority bucket (lower number = higher priority):
        1: WiFi (wlan, wlp, wlo, ra, or wireless sysfs)
        2: Ethernet (eth, enp, eno, ens, end, enx)
        3: USB (usb, rndis)
        4: Cellular (rmnet, wwan, cdc-wdm)
        5: Other physical or unknown interface
        8: VPN / Overlay (Tailscale, WireGuard)
        """
        if (
            iface.startswith(("wlan", "wlp", "wlo", "ra"))
            or _read_file(f"/sys/class/net/{iface}/wireless") is not None
            or _read_file(f"/sys/class/net/{iface}/phy80211") is not None
            or os.path.exists(f"/sys/class/net/{iface}/wireless")
            or os.path.exists(f"/sys/class/net/{iface}/phy80211")
        ):
            return 1
        if iface.startswith(("eth", "enp", "eno", "ens", "end", "enx")):
            return 2
        if iface.startswith(("usb", "rndis")):
            return 3
        if iface.startswith(("rmnet", "wwan", "cdc-wdm")):
            return 4
        if iface.startswith(("tailscale", "wg")):
            return 8
        return 5

    def _primary_interface(self, counters: Dict[str, Tuple[int, int]]) -> Optional[str]:
        """Pick the best interface to report on the overview dashboard.

        Prioritizes WiFi, Ethernet, and USB interfaces over virtual / VPN interfaces
        like Tailscale.
        """
        exclude = {"lo", "docker", "br-", "veth", "tun", "tap", "virbr", "bond", "dummy"}
        candidates = [
            iface for iface in counters.keys()
            if not any(iface.startswith(p) for p in exclude)
        ]
        if not candidates:
            # Fallback to any non-loopback interface
            for iface in sorted(counters.keys()):
                if iface != "lo":
                    return iface
            return None

        default_route = self._default_route_interface()

        def sort_key(iface: str):
            rx_bytes, tx_bytes = counters.get(iface, (0, 0))
            total_bytes = rx_bytes + tx_bytes
            cat_prio = self._interface_category_priority(iface)
            is_virtual = (cat_prio >= 8)

            operstate = self._interface_operstate(iface)
            is_down = (operstate == "down")

            # Only physical / cellular interfaces qualify for default route bonus
            is_default = (iface == default_route) and not is_virtual

            down_penalty = 1 if is_down else 0
            virtual_penalty = 1 if is_virtual else 0
            default_score = 0 if is_default else 1
            traffic_score = 0 if total_bytes > 0 else 1

            return (
                down_penalty,      # 0 for up/unknown, 1 for down
                virtual_penalty,   # 0 for physical/cellular/usb/wifi, 1 for Tailscale/VPN
                default_score,     # 0 if physical default route, 1 otherwise
                traffic_score,     # 0 if interface has recorded traffic, 1 if 0 bytes
                cat_prio,          # 1: WiFi, 2: Ethernet, 3: USB, 4: Cellular, 5: Other
                -total_bytes,      # higher total traffic first
                iface              # deterministic fallback
            )

        candidates.sort(key=sort_key)
        return candidates[0]


NetworkCollector = NetworkRateCollector
