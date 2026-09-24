import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_network_info_and_legacy_alias(auth_client):
    # Modern clean route
    res_modern = await auth_client.get("/api/network")
    assert res_modern.status_code == 200
    data_modern = res_modern.json()
    assert "summary" in data_modern
    assert "interfaces" in data_modern

    # Backward-compatible legacy route used by Jinja2 templates
    res_legacy = await auth_client.get("/api/device/network")
    assert res_legacy.status_code == 200
    data_legacy = res_legacy.json()
    assert "summary" in data_legacy
    assert "interfaces" in data_legacy


@pytest.mark.asyncio
async def test_network_ping_and_legacy_alias(auth_client):
    mock_ping_result = {
        "target": "127.0.0.1",
        "transmitted": 1,
        "received": 1,
        "packet_loss": 0.0,
        "avg_latency_ms": 0.1,
        "output": "1 packets transmitted, 1 received",
        "success": True,
    }
    with patch("server.api.network.ping_test", return_value=mock_ping_result):
        # Modern route
        res1 = await auth_client.get("/api/network/ping?target=127.0.0.1&count=1")
        assert res1.status_code == 200
        assert res1.json()["success"] is True

        # Legacy route
        res2 = await auth_client.get("/api/device/network/ping?target=127.0.0.1&count=1")
        assert res2.status_code == 200
        assert res2.json()["success"] is True


@pytest.mark.asyncio
async def test_network_dns_query_and_legacy_alias(auth_client):
    mock_dns = {"domain": "localhost", "resolved_ip": "127.0.0.1", "latency_ms": 1.2, "success": True}
    with patch("server.api.network.dns_lookup", return_value=mock_dns):
        res1 = await auth_client.get("/api/network/dns-query?domain=localhost")
        assert res1.status_code == 200
        assert res1.json()["resolved_ip"] == "127.0.0.1"

        res2 = await auth_client.get("/api/device/network/dns-query?domain=localhost")
        assert res2.status_code == 200
        assert res2.json()["resolved_ip"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_wifi_scan_and_legacy_alias(auth_client):
    mock_scan = [{"ssid": "LavenderWiFi", "signal": -45, "security": "WPA2"}]
    with patch("server.api.network.scan_wifi_networks", return_value=mock_scan):
        res1 = await auth_client.post("/api/network/wifi-scan")
        assert res1.status_code == 200
        assert len(res1.json()["networks"]) == 1

        res2 = await auth_client.post("/api/device/network/wifi-scan")
        assert res2.status_code == 200
        assert len(res2.json()["networks"]) == 1
