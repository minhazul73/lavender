import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import type {
  NetworkSummaryResponse,
  WifiNetworkItem,
  PingResponse,
  DnsQueryResponse,
} from '../../api/types';
import type { HealthCheckState } from './ConnectivityTab';

export interface NetworkDataState {
  data: NetworkSummaryResponse | null;
  loading: boolean;
  refreshing: boolean;
  loadNetwork: (isRefresh?: boolean) => Promise<void>;
  refresh: (isRefresh?: boolean) => Promise<void>;

  // WiFi
  wifiScanning: boolean;
  scannedNetworks: WifiNetworkItem[];
  handleScanWifi: () => Promise<void>;
  handleWifiScan: () => Promise<void>;

  // Ping
  pingTarget: string;
  setPingTarget: (v: string) => void;
  pingCount: number;
  setPingCount: (v: number) => void;
  pingLoading: boolean;
  pingResult: PingResponse | null;
  handleRunPing: (e?: React.FormEvent) => void;
  handlePing: (e?: React.FormEvent) => void;
  handleSetPingPreset: (preset: string) => void;

  // DNS
  dnsDomain: string;
  setDnsDomain: (v: string) => void;
  dnsQuery: string;
  setDnsQuery: (v: string) => void;
  dnsLoading: boolean;
  dnsResult: DnsQueryResponse | null;
  handleRunDns: (e?: React.FormEvent) => void;
  handleDnsQuery: (e?: React.FormEvent) => void;
  handleQuickDns: (domain: string) => void;

  // Health Checks
  healthChecks: {
    gateway: HealthCheckState;
    dns: HealthCheckState;
    internet: HealthCheckState;
  };
  healthResults: {
    gateway: HealthCheckState;
    dns: HealthCheckState;
    internet: HealthCheckState;
  };
  healthTestingAll: boolean;
  runGatewayProbe: () => Promise<void>;
  runDnsProbe: () => Promise<void>;
  runInternetProbe: () => Promise<void>;
  runAllHealthChecks: () => Promise<void>;
  handleTestAll: () => Promise<void>;
}

export function useNetworkData(): NetworkDataState {
  const { addToast } = useToast();

  // Main data state
  const [data, setData] = useState<NetworkSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // WiFi scanning state
  const [wifiScanning, setWifiScanning] = useState(false);
  const [scannedNetworks, setScannedNetworks] = useState<WifiNetworkItem[]>([]);

  // Ping tool state
  const [pingTarget, setPingTarget] = useState('8.8.8.8');
  const [pingCount, setPingCount] = useState<number>(3);
  const [pingLoading, setPingLoading] = useState(false);
  const [pingResult, setPingResult] = useState<PingResponse | null>(null);

  // DNS query tool state
  const [dnsDomain, setDnsDomain] = useState('google.com');
  const [dnsLoading, setDnsLoading] = useState(false);
  const [dnsResult, setDnsResult] = useState<DnsQueryResponse | null>(null);

  // Connectivity Health Checks state
  const [healthChecks, setHealthChecks] = useState<{
    gateway: HealthCheckState;
    dns: HealthCheckState;
    internet: HealthCheckState;
  }>({
    gateway: { status: 'untested', badge: 'UNTESTED', message: 'Click Test to check latency' },
    dns: { status: 'untested', badge: 'UNTESTED', message: 'Click Test to check resolution' },
    internet: { status: 'untested', badge: 'UNTESTED', message: 'Click Test to ping public server' },
  });
  const [healthTestingAll, setHealthTestingAll] = useState(false);

  // Load all network data
  const loadNetwork = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<NetworkSummaryResponse>('/api/network');
      setData(res);

      // Pre-populate scanned networks if wifi info has nearby or networks
      const nearbyNets = res.wifi?.nearby || res.wifi?.networks || [];
      if (nearbyNets.length > 0) {
        setScannedNetworks(nearbyNets);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load network info';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadNetwork();
  }, [loadNetwork]);

  // WiFi Scan
  const handleScanWifi = async () => {
    setWifiScanning(true);
    try {
      const res = await api.post<{ networks: WifiNetworkItem[] }>('/api/network/wifi-scan');
      const list = res.networks || [];
      setScannedNetworks(list);
      addToast(`Found ${list.length} wireless networks`, 'info');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'WiFi scan failed';
      addToast(msg, 'error');
    } finally {
      setWifiScanning(false);
    }
  };

  // Ping execution
  const executePing = async (targetToPing: string, countToUse: number) => {
    const cleanTarget = targetToPing.trim();
    if (!cleanTarget) return;

    setPingLoading(true);
    setPingResult(null);

    try {
      const res = await api.get<PingResponse>(
        `/api/network/ping?target=${encodeURIComponent(cleanTarget)}&count=${countToUse}`
      );
      setPingResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Ping execution failed';
      addToast(msg, 'error');
    } finally {
      setPingLoading(false);
    }
  };

  const handleRunPing = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    executePing(pingTarget, pingCount);
  };

  const handleSetPingPreset = (preset: string) => {
    let resolvedTarget = preset;
    if (preset === 'gateway') {
      resolvedTarget = data?.summary?.default_gateway || '192.168.1.1';
    }
    setPingTarget(resolvedTarget);
    executePing(resolvedTarget, pingCount);
  };

  // DNS Query execution
  const executeDns = async (domainToQuery: string) => {
    const cleanDomain = domainToQuery.trim().toLowerCase();
    if (!cleanDomain) return;

    setDnsLoading(true);
    setDnsResult(null);

    try {
      const res = await api.get<DnsQueryResponse>(
        `/api/network/dns-query?domain=${encodeURIComponent(cleanDomain)}`
      );
      setDnsResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'DNS lookup failed';
      addToast(msg, 'error');
    } finally {
      setDnsLoading(false);
    }
  };

  const handleRunDns = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    executeDns(dnsDomain);
  };

  const handleQuickDns = (domain: string) => {
    setDnsDomain(domain);
    executeDns(domain);
  };

  // Connectivity Health Check Probes
  const runGatewayProbe = async (): Promise<void> => {
    const gw = data?.summary?.default_gateway || '192.168.1.1';
    setHealthChecks((prev) => ({
      ...prev,
      gateway: { status: 'testing', badge: 'TESTING...', message: 'Pinging gateway…' },
    }));

    try {
      const res = await api.get<PingResponse>(
        `/api/network/ping?target=${encodeURIComponent(gw)}&count=2`
      );
      if (res.success) {
        const avg = res.avg_latency ?? res.avg_latency_ms;
        setHealthChecks((prev) => ({
          ...prev,
          gateway: {
            status: 'success',
            badge: 'REACHABLE',
            message: `Avg Latency: ${avg !== undefined && avg !== null ? avg.toFixed(1) + ' ms' : 'OK'}`,
          },
        }));
      } else {
        setHealthChecks((prev) => ({
          ...prev,
          gateway: { status: 'error', badge: 'FAILED', message: 'No reply from gateway' },
        }));
      }
    } catch {
      setHealthChecks((prev) => ({
        ...prev,
        gateway: { status: 'error', badge: 'FAILED', message: 'Gateway ping request error' },
      }));
    }
  };

  const runDnsProbe = async (): Promise<void> => {
    setHealthChecks((prev) => ({
      ...prev,
      dns: { status: 'testing', badge: 'TESTING...', message: 'Resolving google.com…' },
    }));

    try {
      const res = await api.get<DnsQueryResponse>('/api/network/dns-query?domain=google.com');
      if (res.success) {
        const timeMs = res.time_ms ?? res.latency_ms ?? 0;
        const count = res.count ?? (res.ipv4?.length || 0) + (res.ipv6?.length || 0);
        setHealthChecks((prev) => ({
          ...prev,
          dns: {
            status: 'success',
            badge: 'WORKING',
            message: `Resolved in ${timeMs} ms (${count} answers)`,
          },
        }));
      } else {
        setHealthChecks((prev) => ({
          ...prev,
          dns: { status: 'error', badge: 'FAILED', message: res.error || 'DNS query failed' },
        }));
      }
    } catch {
      setHealthChecks((prev) => ({
        ...prev,
        dns: { status: 'error', badge: 'FAILED', message: 'DNS resolution request error' },
      }));
    }
  };

  const runInternetProbe = async (): Promise<void> => {
    setHealthChecks((prev) => ({
      ...prev,
      internet: { status: 'testing', badge: 'TESTING...', message: 'Pinging 1.1.1.1…' },
    }));

    try {
      const res = await api.get<PingResponse>('/api/network/ping?target=1.1.1.1&count=2');
      if (res.success) {
        const avg = res.avg_latency ?? res.avg_latency_ms;
        setHealthChecks((prev) => ({
          ...prev,
          internet: {
            status: 'success',
            badge: 'ONLINE',
            message: `Latency: ${avg !== undefined && avg !== null ? avg.toFixed(1) + ' ms' : 'OK'}`,
          },
        }));
      } else {
        setHealthChecks((prev) => ({
          ...prev,
          internet: { status: 'error', badge: 'OFFLINE', message: 'Could not reach internet' },
        }));
      }
    } catch {
      setHealthChecks((prev) => ({
        ...prev,
        internet: { status: 'error', badge: 'OFFLINE', message: 'Internet ping request error' },
      }));
    }
  };

  const runAllHealthChecks = async () => {
    setHealthTestingAll(true);
    await Promise.allSettled([runGatewayProbe(), runDnsProbe(), runInternetProbe()]);
    setHealthTestingAll(false);
  };

  return {
    data,
    loading,
    refreshing,
    loadNetwork,
    refresh: loadNetwork,
    wifiScanning,
    scannedNetworks,
    handleScanWifi,
    handleWifiScan: handleScanWifi,
    pingTarget,
    setPingTarget,
    pingCount,
    setPingCount,
    pingLoading,
    pingResult,
    handleRunPing,
    handlePing: handleRunPing,
    handleSetPingPreset,
    dnsDomain,
    setDnsDomain,
    dnsQuery: dnsDomain,
    setDnsQuery: setDnsDomain,
    dnsLoading,
    dnsResult,
    handleRunDns,
    handleDnsQuery: handleRunDns,
    handleQuickDns,
    healthChecks,
    healthResults: healthChecks,
    healthTestingAll,
    runGatewayProbe,
    runDnsProbe,
    runInternetProbe,
    runAllHealthChecks,
    handleTestAll: runAllHealthChecks,
  };
}
