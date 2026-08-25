/* ===== Live Monitoring JS — SSE-driven overview ===== */
(function() {
    'use strict';

    var SSE_URL = '/api/device/live?metrics=cpu,ram,thermal,battery,network';
    var evtSource = new EventSource(SSE_URL);

    var latest = { cpu: null, ram: null, thermal: null, battery: null, network: null };
    var buffers = { cpu: [], ram: [], batt: [], net: [] };
    var MAX_BUF = 30;

    /* ---- Buffer + sparkline ---- */
    function pushBuf(key, val) {
        var buf = buffers[key];
        buf.push(val);
        if (buf.length > MAX_BUF) buf.shift();
    }

    function sparkPath(buf) {
        if (buf.length < 2) return '';
        var min = Math.min.apply(null, buf);
        var max = Math.max.apply(null, buf);
        var range = max - min || 1;
        var w = 100, h = 18;
        var d = '';
        buf.forEach(function(v, i) {
            var x = (i / (buf.length - 1)) * w;
            var y = h - ((v - min) / range) * h;
            y = Math.max(0, Math.min(h, y));
            d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1) + ' ';
        });
        return d;
    }

    function updateSpark(id, bufKey) {
        if (buffers[bufKey].length < 2) return;
        document.getElementById(id).setAttribute('d', sparkPath(buffers[bufKey]));
    }

    /* ---- Format helpers ---- */
    function fmtRate(bps) {
        if (bps < 1024) return bps.toFixed(0) + ' B/s';
        if (bps < 1024 * 1024) return (bps / 1024).toFixed(1) + ' KB/s';
        return (bps / (1024 * 1024)).toFixed(1) + ' MB/s';
    }

    function fmtMem(kb) {
        if (kb < 1024) return kb + ' kB';
        if (kb < 1024 * 1024) return (kb / 1024).toFixed(1) + ' MB';
        return (kb / (1024 * 1024)).toFixed(1) + ' GB';
    }

    /* ---- SSE metric handlers ---- */

    function updateCpu(data) {
        latest.cpu = data;
        var cpus = data.cpus || [];
        var load5 = data.load5 || 0;
        var tempC = null;
        var zones = (latest.thermal || []);
        for (var i = 0; i < zones.length; i++) {
            if (zones[i].name && zones[i].name.indexOf('cpu') === 0) {
                tempC = zones[i].temp_celsius;
                break;
            }
        }

        var el = document.getElementById('cpu-load');
        el.textContent = load5.toFixed(2);
        el.className = 'stat-main';
        if (load5 > 7) el.style.color = '#ef4444';
        else if (load5 > 3) el.style.color = '#f59e0b';
        else el.style.color = 'inherit';

        document.getElementById('cpu-cores').textContent = cpus.length + ' Cores';
        if (cpus.length > 0 && cpus[0].frequency_mhz !== null) {
            var freqs = cpus.map(function(c) {
                return c.frequency_mhz !== null ? c.frequency_mhz.toFixed(0) + ' MHz' : '—';
            });
            document.getElementById('cpu-freq').textContent = freqs.join(', ');
        } else {
            document.getElementById('cpu-freq').textContent = 'N/A';
        }
        pushBuf('cpu', load5);
        updateSpark('sparkpath-cpu', 'cpu');
    }

    function updateRam(data) {
        latest.ram = data;
        var total = data.total || 0;
        var used = data.used || 0;
        var avail = data.available || 0;
        var pct = data.used_pct || 0;

        document.getElementById('ram-used').textContent = fmtMem(used);
        document.getElementById('ram-pct').textContent = pct.toFixed(0) + '%';
        document.getElementById('ram-detail').textContent = fmtMem(avail) + ' free';

        var bar = document.getElementById('ram-bar');
        bar.style.width = Math.min(100, pct) + '%';
        bar.className = 'progress-bar-inner' + (pct > 85 ? ' crit' : (pct > 70 ? ' warn' : ''));

        pushBuf('ram', pct);
        updateSpark('sparkpath-ram', 'ram');
    }

    function updateBattery(data) {
        latest.battery = data;
        var pct = data.percentage;
        var state = data.state || 'Unknown';
        var temp = data.temperature;
        var volt = data.voltage;

        var pctEl = document.getElementById('batt-pct');
        if (pct !== null) {
            pctEl.textContent = pct + '%';
            pctEl.style.color = pct < 20 ? '#ef4444' : (pct < 50 ? '#f59e0b' : '#10b981');
        } else {
            pctEl.textContent = '—';
        }
        document.getElementById('batt-state').textContent = state;
        document.getElementById('batt-temp').textContent = temp !== null ? temp.toFixed(1) + '°C' : '—°C';
        document.getElementById('batt-volt').textContent = volt !== null ? volt.toFixed(2) + ' V' : '— V';

        if (pct !== null) {
            pushBuf('batt', pct);
            updateSpark('sparkpath-batt', 'batt');
        }
    }

    function updateNetwork(data) {
        latest.network = data;
        var iface = data.iface || '—';
        var rx = data.rx_rate_bps || 0;
        var tx = data.tx_rate_bps || 0;

        // Top card
        document.getElementById('net-iface').textContent = iface;
        document.getElementById('net-up').textContent = '↑ ' + fmtRate(tx);
        document.getElementById('net-down').textContent = '↓ ' + fmtRate(rx);

        // Bottom network card
        var detEl = document.getElementById('net-iface-detail');
        var upEl = document.getElementById('net-up-speed');
        var downEl = document.getElementById('net-down-speed');
        if (detEl) detEl.textContent = iface;
        if (upEl) upEl.textContent = fmtRate(tx);
        if (downEl) downEl.textContent = fmtRate(rx);

        // Network health pill
        var netEl = document.getElementById('health-network');
        netEl.className = 'health-pill' + (rx > 0 || tx > 0 ? ' good' : ' warn');
        netEl.querySelector('span:last-child').textContent = (rx > 0 || tx > 0) ? 'Active' : 'Idle';

        pushBuf('net', Math.max(rx, tx));
        updateSpark('sparkpath-net', 'net');
    }

    /* ---- Network details (IPs, interface) ---- */
    function updateNetworkDetails(data) {
        var ifaces = data.interfaces || [];
        var localIp = '—', primaryIface = '—';
        ifaces.forEach(function(iface) {
            if (iface.state === 'UP' && iface.name !== 'lo') {
                if (iface.name.indexOf('usb') === 0 || iface.name.indexOf('eth') === 0 || iface.name.indexOf('rmnet') === 0) {
                    if (primaryIface === '—') primaryIface = iface.name;
                }
                iface.addresses.forEach(function(addr) {
                    if (addr.indexOf('127.') === 0) return;
                    if (addr.indexOf('169.254.') === 0) return;
                    if (localIp === '—') localIp = addr;
                });
            }
        });
        var detEl = document.getElementById('net-iface-detail');
        var locEl = document.getElementById('net-local-ip');
        if (detEl) detEl.textContent = primaryIface !== '—' ? primaryIface : '—';
        if (locEl) locEl.textContent = localIp;
    }

    function updateThermal(data) {
        latest.thermal = data;
        var zones = data || [];
        var avgTemp = 0, cpuTemp = null;
        zones.forEach(function(z) {
            avgTemp += z.temp_celsius;
            if (z.name && z.name.indexOf('cpu') === 0) cpuTemp = z.temp_celsius;
        });
        if (zones.length > 0) avgTemp = avgTemp / zones.length;

        var thEl = document.getElementById('health-thermal');
        thEl.className = 'health-pill' + (avgTemp > 70 ? ' crit' : (avgTemp > 50 ? ' warn' : ' good'));
        thEl.querySelector('span:last-child').textContent = avgTemp.toFixed(0) + '°C';
    }

    /* ---- Battery health pill ---- */
    function updateBatteryPill() {
        if (!latest.battery) return;
        var pct = latest.battery.percentage;
        if (pct !== null) {
            var bEl = document.getElementById('health-battery');
            bEl.className = 'health-pill' + (pct < 20 ? ' crit' : (pct < 50 ? ' warn' : ' good'));
            bEl.querySelector('span:last-child').textContent = pct + '%';
        }
    }

    /* ---- Memory health pill ---- */
    function updateMemoryPill() {
        if (!latest.ram) return;
        var pct = latest.ram.used_pct || 0;
        var mEl = document.getElementById('health-memory');
        mEl.className = 'health-pill' + (pct > 85 ? ' crit' : (pct > 70 ? ' warn' : ' good'));
        mEl.querySelector('span:last-child').textContent = pct.toFixed(0) + '%';
    }

    /* ---- Storage ---- */
    function updateStorage(data) {
        var disks = data.disks || [];
        var root = null;
        for (var i = 0; i < disks.length; i++) {
            if (disks[i].mount === '/') { root = disks[i]; break; }
        }
        if (!root && disks.length > 0) root = disks[0];
        if (!root) return;

        var pct = root.use_pct !== null && root.use_pct !== undefined ? root.use_pct : 0;
        document.getElementById('store-used').textContent = root.used || 'N/A';
        document.getElementById('store-free').textContent = root.avail || 'N/A';
        document.getElementById('store-pct').textContent = pct + '%';
        document.getElementById('store-total').textContent = root.size || 'N/A';
        document.getElementById('store-detail').textContent = (root.used || '?') + ' / ' + (root.size || '?');
        document.getElementById('store-bar').style.width = pct + '%';
        document.getElementById('store-bar').className = 'progress-bar-inner' + (pct > 90 ? ' crit' : (pct > 80 ? ' warn' : ''));

        var dEl = document.getElementById('health-disk');
        dEl.className = 'health-pill' + (pct > 90 ? ' crit' : (pct > 80 ? ' warn' : ' good'));
        dEl.querySelector('span:last-child').textContent = pct + '%';
    }

    /* ---- Services ---- */
    function updateServices(data) {
        var services = data.services || [];
        var active = 0, failed = 0, inactive = 0;
        services.forEach(function(s) {
            if (s.active_state === 'active') active++;
            else if (s.active_state === 'failed') failed++;
            else inactive++;
        });

        document.getElementById('svc-active-count').textContent = active;
        document.getElementById('svc-inactive-count').textContent = inactive;
        document.getElementById('svc-failed-count').textContent = failed;
        document.getElementById('svc-total-donut').textContent = services.length;

        // Update donut chart angles
        var total = services.length;
        if (total > 0) {
            var activePct = active / total;
            var inactivePct = inactive / total;
            // Simple donut: active arc
            var activeDash = activePct * 100;
            document.getElementById('svc-donut-active').style.strokeDasharray = activeDash + ' 100';
        }
    }

    /* ---- Recent logs ---- */
    function updateLogs(data) {
        var logs = data.logs || [];
        var el = document.getElementById('recent-logs');
        if (!el) return;
        el.innerHTML = logs.map(function(l) {
            var color = l.level === 'error' ? '#ef4444' : (l.level === 'warning' ? '#f59e0b' : '#10b981');
            return '<div style="padding:5px 10px; font-size:11px; display:flex; gap:6px; border-bottom:1px solid var(--border);">\
                <span style="color:var(--text-muted); min-width:60px;">' + (l.timestamp || '--:--:--') + '</span>\
                <span style="width:6px; height:6px; border-radius:50%; background:' + color + '; flex-shrink:0;"></span>\
                <span>' + (l.message || '') + '</span>\
            </div>';
        }).join('') || '<div style="padding:6px 10px; font-size:11px; color:var(--text-muted);">No logs</div>';
    }

    /* ---- System Activity chart (canvas-based) ---- */
    var chartData = { cpu: [], mem: [] };
    function renderChart() {
        if (latest.cpu) {
            chartData.cpu.push(latest.cpu.load5 || 0);
        }
        if (latest.ram) {
            chartData.mem.push(latest.ram.used_pct || 0);
        }
        if (chartData.cpu.length > 60) chartData.cpu.shift();
        if (chartData.mem.length > 60) chartData.mem.shift();

        var canvas = document.getElementById('chart-activity');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        var w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        // Grid lines
        ctx.strokeStyle = 'rgba(255,255,255,0.03)';
        ctx.lineWidth = 1;
        for (var i = 0; i <= 4; i++) {
            var y = (i / 4) * h;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Draw CPU line (purple)
        if (chartData.cpu.length > 1) {
            var maxCpu = Math.max.apply(null, chartData.cpu) || 1;
            var maxV = Math.max(maxCpu, Math.max.apply(null, chartData.mem) || 0, 100);
            ctx.strokeStyle = '#a855f7';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            chartData.cpu.forEach(function(v, i) {
                var x = (i / (chartData.cpu.length - 1)) * w;
                var y = h - (v / maxV) * h;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
        }

        // Draw Memory line (blue)
        if (chartData.mem.length > 1) {
            var maxMem = Math.max.apply(null, chartData.mem) || 1;
            var maxV2 = Math.max(maxMem, Math.max.apply(null, chartData.cpu) || 0, 100);
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            chartData.mem.forEach(function(v, i) {
                var x = (i / (chartData.mem.length - 1)) * w;
                var y = h - (v / maxV2) * h;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
        }
    }

    /* ---- Top processes (table) ---- */
    function updateTopProcesses(data) {
        var procs = data.processes || [];
        var tbody = document.getElementById('top-processes');
        if (!tbody) return;
        if (procs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">No processes</td></tr>';
            return;
        }
        tbody.innerHTML = procs.map(function(p) {
            var cpuVal = typeof p.cpu === 'number' ? p.cpu.toFixed(1) + 's' : (p.cpu || '?');
            var memKb = p.mem || 0;
            var memVal = memKb >= 1024 ? (memKb / 1024).toFixed(0) + ' MB' : memKb + ' kB';
            return '<tr>' +
                '<td class="proc-name">' + (p.command || p.name || '?') + '</td>' +
                '<td class="mono">' + cpuVal + '</td>' +
                '<td class="mono">' + memVal + '</td>' +
            '</tr>';
        }).join('');
    }

    /* ---- SSE message handler ---- */
    evtSource.onmessage = function(e) {
        try {
            var msg = JSON.parse(e.data);
            if (msg.type === 'connect') return;
            var metric = msg.metric;
            var data = msg.data;
            if (metric === 'cpu') { updateCpu(data); renderChart(); }
            else if (metric === 'ram') { updateRam(data); renderChart(); }
            else if (metric === 'thermal') updateThermal(data);
            else if (metric === 'battery') { updateBattery(data); updateBatteryPill(); }
            else if (metric === 'network') updateNetwork(data);
        } catch (err) { /* skip */ }
    };

    evtSource.onopen = function() {
        var el = document.getElementById('sse-status');
        var txt = document.getElementById('sse-status-text');
        el.className = 'connected';
        txt.textContent = 'Live';
    };

    evtSource.onerror = function() {
        var el = document.getElementById('sse-status');
        var txt = document.getElementById('sse-status-text');
        el.className = 'disconnected';
        txt.textContent = 'Disconnected';
        evtSource.close();
        setTimeout(function() {
            var ns = new EventSource(SSE_URL);
            ns.onopen = evtSource.onopen;
            ns.onmessage = evtSource.onmessage;
            ns.onerror = evtSource.onerror;
        }, 5000);
    };

    /* ---- REST fetches ---- */
    function fetchJson(url) {
        return fetch(url).then(function(r) { return r.json(); }).catch(function() {});
    }

    fetchJson('/api/system/storage').then(function(d) { if (d) updateStorage(d); });
    fetchJson('/api/system/services').then(function(d) { if (d) updateServices(d); });
    fetchJson('/api/system/logs?limit=10').then(function(d) { if (d) updateLogs(d); });
    fetchJson('/api/device/network').then(function(d) { if (d) updateNetworkDetails(d); });
    fetchJson('/api/system/processes?sort_by=mem&limit=5').then(function(d) { if (d) updateTopProcesses(d); });
})();
