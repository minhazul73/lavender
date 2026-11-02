import { useState, useEffect, useCallback } from 'react';
import { useSSE } from '../../hooks/useSSE';
import { api } from '../../api/client';
import type {
  ServiceItem,
  ServicesListResponse,
  StorageDiskItem,
  StorageOverviewResponse,
  ProcessItem,
  ProcessesOverviewResponse,
  LiveTelemetryData,
  SystemLogItem,
  BatteryTelemetry,
  ThermalZone,
} from '../../api/types';

export interface OverviewData {
  services: ServiceItem[];
  disks: StorageDiskItem[];
  processes: ProcessItem[];
  sseData: LiveTelemetryData | null;
  connected: boolean;
  loading: boolean;
  refreshing: boolean;
  refresh: () => void;
  recentLogs: SystemLogItem[];
  restBattery: BatteryTelemetry | null;
  restThermal: ThermalZone[] | null;
}

export interface UseOverviewDataOptions {
  onMetric?: (metric: string, data: any) => void;
}

export function useOverviewData(options: UseOverviewDataOptions = {}): OverviewData {
  const { data: sseData, status } = useSSE({ onMetric: options.onMetric });
  const connected = status === 'connected';

  const [storageData, setStorageData] = useState<StorageOverviewResponse | null>(null);
  const [servicesData, setServicesData] = useState<ServicesListResponse | null>(null);
  const [topProcesses, setTopProcesses] = useState<ProcessesOverviewResponse | null>(null);
  const [recentLogs, setRecentLogs] = useState<SystemLogItem[]>([]);
  const [restBattery, setRestBattery] = useState<BatteryTelemetry | null>(null);
  const [restThermal, setRestThermal] = useState<ThermalZone[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchOverviewData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const [storage, services, logs, procs, batt] = await Promise.allSettled([
        api.get<StorageOverviewResponse>('/api/system/storage'),
        api.get<ServicesListResponse>('/api/system/services'),
        api.get<{ logs: SystemLogItem[] }>('/api/system/logs?limit=30'),
        api.get<ProcessesOverviewResponse>('/api/system/processes?sort_by=mem&limit=10'),
        api.get<{ battery?: BatteryTelemetry; thermal?: ThermalZone[] }>('/api/device/battery'),
      ]);

      if (storage.status === 'fulfilled' && storage.value) setStorageData(storage.value);
      if (services.status === 'fulfilled' && services.value) setServicesData(services.value);
      if (logs.status === 'fulfilled' && logs.value?.logs) setRecentLogs(logs.value.logs);
      if (procs.status === 'fulfilled' && procs.value) setTopProcesses(procs.value);
      if (batt.status === 'fulfilled' && batt.value) {
        if (batt.value.battery) setRestBattery(batt.value.battery);
        if (batt.value.thermal) setRestThermal(batt.value.thermal);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    fetchOverviewData();

    // Top processes refreshes periodically (every 5s, matching main branch)
    const procInterval = setInterval(() => {
      if (!document.hidden && isMounted) {
        api.get<ProcessesOverviewResponse>('/api/system/processes?sort_by=mem&limit=10')
          .then((res) => {
            if (isMounted && res) setTopProcesses(res);
          })
          .catch(() => {});
      }
    }, 5000);

    return () => {
      isMounted = false;
      clearInterval(procInterval);
    };
  }, [fetchOverviewData]);

  const refresh = useCallback(() => {
    fetchOverviewData(true);
  }, [fetchOverviewData]);

  const services = servicesData?.services ?? [];
  const disks = storageData?.disks ?? [];
  const processes = topProcesses?.processes ?? [];

  return {
    services,
    disks,
    processes,
    sseData,
    connected,
    loading,
    refreshing,
    refresh,
    recentLogs,
    restBattery,
    restThermal,
  };
}
