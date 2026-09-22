/* ===== Live Monitoring JS — SSE-driven overview ===== */
(function() {
    'use strict';

    var SSE_URL = '/api/device/live?metrics=cpu,ram,thermal,battery,network';

    var latest = { cpu: null, ram: null, thermal: null, battery: null, network: null };
    var buffers = { cpu: [], ram: [], batt: [], net_up: [], net_down: [] };
    var MAX_BUF = 30;

    /* ---- Buffer + sparkline ---- */
    function pushBuf(key, val) {
        var buf = buffers[key];
        buf.push(val);
        if (buf.length > MAX_BUF) buf.shift();
    }

    /**
     * Build a smooth Catmull-Rom cubic bezier path for a data buffer.
     * w/h are the SVG viewBox dimensions.
     * Returns { line, area } path strings.
     */
    function buildSparkPaths(buf, w, h) {
        w = w || 100; h = h || 32;
        if (buf.length < 2) return { line: '', area: '' };

        var min = Math.min.apply(null, buf);
        var max = Math.max.apply(null, buf);
        var range = max - min || 1;
        var pad = h * 0.08; // inset so curve peak never reaches the SVG edge

        // Map buffer values to SVG coordinates
        var pts = buf.map(function(v, i) {
            return {
                x: parseFloat(((i / (buf.length - 1)) * w).toFixed(2)),
                y: parseFloat((pad + (1 - (v - min) / range) * (h - pad * 2)).toFixed(2))
            };
        });

        // Catmull-Rom tension
        var t = 0.4;

        function ctrlPts(p0, p1, p2, p3) {
            return {
                cp1x: p1.x + (p2.x - p0.x) * t,
                cp1y: p1.y + (p2.y - p0.y) * t,
                cp2x: p2.x - (p3.x - p1.x) * t,
                cp2y: p2.y - (p3.y - p1.y) * t
            };
        }

        var line = 'M' + pts[0].x + ',' + pts[0].y;
        for (var i = 0; i < pts.length - 1; i++) {
            var p0 = pts[Math.max(0, i - 1)];
            var p1 = pts[i];
            var p2 = pts[i + 1];
            var p3 = pts[Math.min(pts.length - 1, i + 2)];
            var c = ctrlPts(p0, p1, p2, p3);
            line += ' C' + c.cp1x + ',' + c.cp1y + ' ' + c.cp2x + ',' + c.cp2y + ' ' + p2.x + ',' + p2.y;
        }

        // Area path: follow the line then close along the bottom
        var last = pts[pts.length - 1];
        var area = line + ' L' + last.x + ',' + h + ' L' + pts[0].x + ',' + h + ' Z';

        return { line: line, area: area };
    }

    function updateSpark(lineId, bufKey, areaId, svgH) {
        var buf = buffers[bufKey];
        if (!buf || buf.length < 2) return;
        var paths = buildSparkPaths(buf, 100, svgH || 32);
        var lineEl = document.getElementById(lineId);
        if (lineEl) lineEl.setAttribute('d', paths.line);
        if (areaId) {
            var areaEl = document.getElementById(areaId);
            if (areaEl) areaEl.setAttribute('d', paths.area);
        }
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
        var load5 = data.load5 || 0;

        // Main header: load average
        var el = document.getElementById('cpu-load');
        el.textContent = load5.toFixed(2);
        if (load5 > 7) el.style.color = '#ef4444';
        else if (load5 > 3) el.style.color = '#f59e0b';
        else el.style.color = 'inherit';

        document.getElementById('cpu-cores').textContent = data.count + ' Cores';
        if (data.cpus.length > 0 && data.cpus[0].frequency_mhz !== null) {
            var freqs = data.cpus.map(function(c) {
                return c.frequency_mhz !== null ? c.frequency_mhz.toFixed(0) + ' MHz' : '—';
            });
            document.getElementById('cpu-freq').textContent = freqs.join(', ');
        } else {
            document.getElementById('cpu-freq').textContent = 'N/A';
        }

        // Per-core usage bars
        renderCpuCores(data);

        pushBuf('cpu', load5);
        updateSpark('sparkpath-cpu', 'cpu');
    }

    function renderCpuCores(data) {
        var grid = document.getElementById('cpu-cores-grid');
        if (!grid) return;

        var cores = data.per_core_usage || [];
        if (!cores.length) {
            grid.innerHTML = '<p class="text-muted">No core data</p>';
            return;
        }

        // Initialize per-core buffers on first call
        if (!window._coreBuffers) {
            window._coreBuffers = cores.map(() => []);
        }

        // Update buffers
        cores.forEach(function(core, i) {
            var buf = window._coreBuffers[i];
            if (core.usage !== null) buf.push(core.usage);
            if (buf.length > 30) buf.shift();
        });

        var html = '';
        for (var i = 0; i < cores.length; i++) {
            var core = cores[i];
            var buf = window._coreBuffers[i] || [];
            var usage = core.usage !== null ? core.usage.toFixed(1) + '%' : '—';
            var cls = core.usage > 85 ? ' crit' : (core.usage > 70 ? ' warn' : '');

            // Build SVG path for mini sparkline
            var svgPoints = '';
            if (buf.length > 1) {
                var w = 80, h = 24;
                var maxV = Math.max.apply(null, buf) || 100;
                buf.forEach(function(v, idx) {
                    var x = (idx / (buf.length - 1)) * w;
                    var y = h - (v / maxV) * h;
                    svgPoints += (idx === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1) + ' ';
                });
            }

            html += '<div class="cpu-core">' +
                '<div class="cpu-core-label">CPU' + core.core + '</div>' +
                '<svg class="cpu-core-spark" viewBox="0 0 80 24" preserveAspectRatio="none">' +
                '<path d="' + svgPoints + '" stroke-width="1.5" fill="none"/>' +
                '</svg>' +
                '<div class="cpu-core-value' + cls + '">' + usage + '</div>' +
                '</div>';
        }
        grid.innerHTML = html;
    }

    function updateRam(data) {
        latest.ram = data;
        var total = data.total || 0;
        var used = data.used || 0;
        var avail = data.available || 0;
        var pct = data.used_pct || 0;
        var cached = (data.cached || 0) + (data.buffers || 0);
        var swapTotal = data.swap_total || 0;
        var swapUsed = data.swap_used || 0;

        document.getElementById('ram-used').textContent = fmtMem(used);
        var totalEl = document.getElementById('ram-total');
        if (totalEl) totalEl.textContent = '/ ' + fmtMem(total);

        document.getElementById('ram-pct').textContent = pct.toFixed(0) + '%';
        document.getElementById('ram-detail').textContent = fmtMem(avail) + ' free';

        var swapEl = document.getElementById('ram-swap');
        if (swapEl) {
            if (swapTotal > 0) {
                swapEl.textContent = 'Swap: ' + fmtMem(swapUsed);
            } else {
                swapEl.textContent = 'Cache: ' + fmtMem(cached);
            }
        }

        var bar = document.getElementById('ram-bar');
        bar.style.width = Math.min(100, pct) + '%';
        bar.className = 'progress-bar-inner' + (pct > 85 ? ' crit' : (pct > 70 ? ' warn' : ''));

        pushBuf('ram', pct);
        updateSpark('sparkpath-ram', 'ram', 'sparkarea-ram', 32);
    }

    function fmtBatteryTime(val) {
        if (!val) return '—';
        if (typeof val === 'number') {
            if (val >= 60) {
                var h = Math.floor(val / 60);
                var m = val % 60;
                return m > 0 ? h + 'h ' + m + 'm' : h + ' hrs';
            }
            return val + ' min';
        }
        var s = String(val).trim();
        s = s.replace(/hours?/i, 'hrs').replace(/minutes?/i, 'min');
        return s;
    }

    function updateBattery(data) {
        latest.battery = data;
        var pct = data.percentage;
        var rawState = (data.state || data.battery_state || 'unknown').toLowerCase();
        var temp = data.temperature;
        var volt = data.voltage;
        var rate = data.energy_rate;
        var energy = data.energy;
        var energyFull = data.energy_full;
        var capacity = data.capacity;
        var tte = data.time_to_empty;
        var ttf = data.time_to_full;

        // Classify charging vs discharging vs full vs idle
        var isCharging = data.charging || rawState === 'charging';
        var isDischarging = data.discharging || rawState === 'discharging';
        var isFull = rawState === 'full' || rawState === 'fully-charged';

        // 1. Badge & State
        var badgeEl = document.getElementById('batt-badge');
        var badgeText = document.getElementById('batt-badge-text');
        if (badgeEl && badgeText) {
            badgeEl.className = 'batt-badge ' + (
                isCharging ? 'badge-charging' :
                isDischarging ? 'badge-discharging' :
                isFull ? 'badge-full' : 'badge-neutral'
            );
            badgeText.textContent = isCharging ? '⚡ Charging' :
                                   isDischarging ? 'Discharging' :
                                   isFull ? 'Fully Charged' :
                                   (rawState !== 'unknown' ? (rawState.charAt(0).toUpperCase() + rawState.slice(1)) : ((pct !== null && pct !== undefined) ? 'Plugged In' : 'No Battery'));
        }

        // 2. Percentage & Gauge
        var pctEl = document.getElementById('batt-pct');
        var gaugeFill = document.getElementById('batt-gauge-fill');
        if (pctEl) {
            if (pct !== null && pct !== undefined) {
                pctEl.textContent = pct + '%';
                pctEl.style.color = isCharging ? '#10b981' : (pct < 20 ? '#ef4444' : (pct < 50 ? '#f59e0b' : '#10b981'));
            } else {
                pctEl.textContent = '—';
                pctEl.style.color = 'var(--text-muted)';
            }
        }
        if (gaugeFill && pct !== null && pct !== undefined) {
            gaugeFill.style.width = Math.min(100, Math.max(0, pct)) + '%';
            gaugeFill.className = 'batt-gauge-fill' + (
                isCharging ? ' charging' :
                (pct < 20 ? ' crit' : (pct < 50 ? ' warn' : ''))
            );
        } else if (gaugeFill) {
            gaugeFill.style.width = '0%';
            gaugeFill.className = 'batt-gauge-fill';
        }

        // 3. Dynamic Rate (Discharge Rate vs Charge Rate)
        var rateLabelEl = document.getElementById('batt-rate-label');
        var rateValEl = document.getElementById('batt-rate-val');
        if (rateLabelEl && rateValEl) {
            if (isCharging) {
                rateLabelEl.textContent = 'Charge Rate';
                rateValEl.textContent = rate !== null && rate > 0 ? '+' + rate.toFixed(2) + ' W' : (rate !== null ? rate.toFixed(2) + ' W' : '— W');
                rateValEl.style.color = '#34d399';
            } else if (isDischarging) {
                rateLabelEl.textContent = 'Discharge Rate';
                rateValEl.textContent = rate !== null && rate > 0 ? rate.toFixed(2) + ' W' : (rate !== null ? rate.toFixed(2) + ' W' : '— W');
                rateValEl.style.color = '#fbbf24';
            } else if (isFull) {
                rateLabelEl.textContent = 'Power Rate';
                rateValEl.textContent = '0.00 W';
                rateValEl.style.color = 'var(--text-secondary)';
            } else {
                rateLabelEl.textContent = 'Power Rate';
                rateValEl.textContent = rate !== null ? rate.toFixed(2) + ' W' : '— W';
                rateValEl.style.color = 'var(--accent)';
            }
        }

        // 4. Dynamic Estimated Time (Time to Empty vs Time to Full)
        var timeLabelEl = document.getElementById('batt-time-label');
        var timeValEl = document.getElementById('batt-time-val');
        if (timeLabelEl && timeValEl) {
            if (isCharging) {
                timeLabelEl.textContent = 'Time to Full';
                timeValEl.textContent = ttf ? fmtBatteryTime(ttf) : (pct >= 99 ? 'Almost full' : 'Calculating…');
            } else if (isDischarging) {
                timeLabelEl.textContent = 'Time to Empty';
                timeValEl.textContent = tte ? fmtBatteryTime(tte) : (pct !== null ? 'Calculating…' : '—');
            } else if (isFull) {
                timeLabelEl.textContent = 'Status';
                timeValEl.textContent = 'On AC Power';
            } else {
                timeLabelEl.textContent = 'Estimated Time';
                timeValEl.textContent = tte ? fmtBatteryTime(tte) : (ttf ? fmtBatteryTime(ttf) : '—');
            }
        }

        // 5. Secondary Telemetry Grid
        // Voltage with eye-catching display and micro-meter calculation
        var voltEl = document.getElementById('batt-voltage');
        var voltRangeEl = document.getElementById('batt-volt-range');
        var voltBarEl = document.getElementById('batt-volt-bar');
        if (volt !== null && volt !== undefined) {
            if (voltEl) voltEl.textContent = volt.toFixed(2) + ' V';

            // Dynamic voltage range (1S phones vs multi-cell packs)
            var minV = 3.4, maxV = 4.35;
            if (volt > 13.5) { minV = 13.6; maxV = 17.4; }
            else if (volt > 9.0) { minV = 10.2; maxV = 13.05; }
            else if (volt > 5.0) { minV = 6.8; maxV = 8.7; }
            else { minV = 3.4; maxV = 4.35; }

            if (voltRangeEl) voltRangeEl.textContent = minV + '–' + maxV + 'V';
            if (voltBarEl) {
                var vPct = Math.min(100, Math.max(0, ((volt - minV) / (maxV - minV)) * 100));
                voltBarEl.style.width = vPct.toFixed(0) + '%';
            }
        } else {
            if (voltEl) voltEl.textContent = '— V';
            if (voltBarEl) voltBarEl.style.width = '0%';
        }

        var tempEl = document.getElementById('batt-temperature');
        if (tempEl) {
            if (temp !== null && temp !== undefined) {
                tempEl.textContent = temp.toFixed(1) + '°C';
                tempEl.style.color = temp > 45 ? 'var(--red)' : (temp > 38 ? 'var(--yellow)' : 'var(--text-primary)');
            } else {
                tempEl.textContent = '—°C';
                tempEl.style.color = 'var(--text-primary)';
            }
        }

        var energyEl = document.getElementById('batt-energy');
        if (energyEl) {
            if (energy !== null && energyFull !== null) {
                energyEl.textContent = energy.toFixed(1) + ' / ' + energyFull.toFixed(1) + ' Wh';
            } else if (energy !== null) {
                energyEl.textContent = energy.toFixed(1) + ' Wh';
            } else if (energyFull !== null) {
                energyEl.textContent = energyFull.toFixed(1) + ' Wh';
            } else {
                energyEl.textContent = '— Wh';
            }
        }

        var healthEl = document.getElementById('batt-health');
        if (healthEl) {
            if (capacity !== null && capacity !== undefined) {
                healthEl.textContent = typeof capacity === 'number' ? capacity.toFixed(0) + '%' : capacity;
            } else {
                healthEl.textContent = '—';
            }
        }
    }

    function updateNetwork(data) {
        latest.network = data;
        var iface = data.iface || '—';
        var rx = data.rx_rate_bps || 0;
        var tx = data.tx_rate_bps || 0;

        // Middle network card (was top card)
        document.getElementById('net-iface-middle').textContent = iface;
        document.getElementById('net-up-middle').textContent = '↑ ' + fmtRate(tx);
        document.getElementById('net-down-middle').textContent = '↓ ' + fmtRate(rx);

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

        pushBuf('net_up', tx);
        updateSpark('sparkpath-net-up', 'net_up', 'sparkarea-net-up', 40);
        pushBuf('net_down', rx);
        updateSpark('sparkpath-net-down', 'net_down', 'sparkarea-net-down', 40);
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

    /* ---- Thermal (gauge-style zones in bottom card) ---- */
    function updateThermalTop(data) {
        var zones = data.zones || [];
        if (!zones.length) return;

        // Priority zones to show
        var wanted = ['AOSS (Always-On Sensor)', 'GPU (Adreno)', 'CPU SS0 (Gold/Big)', 'CPU SS1 (LITTLE)'];
        var selected = [];
        zones.forEach(function(z) {
            var label = z.display_name || z.name;
            if (wanted.indexOf(label) >= 0) selected.push(z);
        });
        if (selected.length < 4) {
            zones.forEach(function(z) {
                if (selected.indexOf(z) < 0 && selected.length < 4) selected.push(z);
            });
        }

        var container = document.getElementById('thermal-top');
        if (!container) return;

        // Map zone labels to short display names + icon paths
        function zoneIcon(label) {
            var l = label.toLowerCase();
            if (l.indexOf('gpu') >= 0)    return '<path d="M2 4h20v12H2z M8 20h8 M12 16v4"/>';
            if (l.indexOf('cpu') >= 0)    return '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>';
            if (l.indexOf('aoss') >= 0 || l.indexOf('always') >= 0)
                                          return '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>';
            return '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>';
        }

        function shortLabel(label) {
            if (label.indexOf('AOSS') >= 0)    return 'Always-On';
            if (label.indexOf('Gold') >= 0)    return 'CPU Big';
            if (label.indexOf('LITTLE') >= 0)  return 'CPU Little';
            if (label.indexOf('GPU') >= 0)     return 'GPU';
            // Trim long names
            return label.length > 16 ? label.slice(0, 15) + '…' : label;
        }

        // Color stops: cool(≤45) → good(45-60) → warn(60-80) → crit(≥80)
        function tempColor(t) {
            if (t >= 80) return 'var(--red)';
            if (t >= 60) return 'var(--yellow)';
            if (t >= 45) return 'var(--orange)';
            return 'var(--green)';
        }

        function heatGradient(t) {
            if (t >= 80) return 'linear-gradient(90deg, #f97316, #ef4444)';
            if (t >= 60) return 'linear-gradient(90deg, #f59e0b, #f97316)';
            if (t >= 45) return 'linear-gradient(90deg, var(--orange), #f59e0b)';
            return 'linear-gradient(90deg, var(--green), #06b6d4)';
        }

        // Bar fill: 20°C = 0%, 100°C = 100%
        function heatPct(t) {
            return Math.max(0, Math.min(100, ((t - 20) / 80) * 100)).toFixed(1);
        }

        container.innerHTML = selected.map(function(z) {
            var temp  = z.temp_celsius;
            var label = z.display_name || z.name;
            var pct   = heatPct(temp);
            var col   = tempColor(temp);
            var grad  = heatGradient(temp);
            var icon  = zoneIcon(label);
            var short = shortLabel(label);
            var tempStr = (temp !== null) ? temp.toFixed(1) + '°C' : '—';

            return [
                '<div class="tz-row">',
                  '<div class="tz-icon">',
                    '<svg width="12" height="12" viewBox="0 0 24 24" fill="none"',
                    ' stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">',
                    icon, '</svg>',
                  '</div>',
                  '<div class="tz-body">',
                    '<div class="tz-meta">',
                      '<span class="tz-label">' + short + '</span>',
                      '<span class="tz-badge" style="color:' + col + '; border-color:' + col + ';">' + tempStr + '</span>',
                    '</div>',
                    '<div class="tz-track">',
                      '<div class="tz-fill" style="width:' + pct + '%; background:' + grad + ';"></div>',
                    '</div>',
                  '</div>',
                '</div>'
            ].join('');
        }).join('');
    }

    /* ---- Storage ---- */
    function updateStorage(data) {
        var disks = data.disks || [];
        if (!disks.length) return;

        // Health pill — use root disk percentage
        var root = null;
        for (var i = 0; i < disks.length; i++) {
            if (disks[i].mount === '/') { root = disks[i]; break; }
        }
        if (!root && disks.length > 0) root = disks[0];

        var rootPct = root ? _pctNum(root) : 0;
        var dEl = document.getElementById('health-disk');
        if (dEl) {
            dEl.className = 'health-pill' + (rootPct > 90 ? ' crit' : (rootPct > 80 ? ' warn' : ' good'));
            dEl.querySelector('span:last-child').textContent = rootPct + '%';
        }

        // Render all mounts in the storage card body
        var container = document.getElementById('store-mounts');
        if (!container) return;

        // Sort: non-external first (root), then external
        var sorted = disks.slice().sort(function(a, b) {
            var aExt = a.is_external ? 1 : 0;
            var bExt = b.is_external ? 1 : 0;
            return aExt - bExt || (a.mount > b.mount ? 1 : -1);
        });

        container.innerHTML = sorted.map(function(d) {
            var pct = _pctNum(d);
            var barClass = pct > 90 ? ' crit' : (pct > 80 ? ' warn' : '');
            var isExt = d.is_external ? ' is-external' : '';
            var mountDisplay = d.mount === '/' ? 'System (' + d.mount + ')' : d.mount;
            var icon = d.is_external ? '💾' : '📁';
            var used = d.used || '?', total = d.size || '?', avail = d.avail || '?';
            return '<div class="store-mount' + isExt + '">'
                + '<div class="store-mount-header">'
                +  '<span class="store-mount-icon">' + icon + '</span>'
                +  '<span class="store-mount-label">' + mountDisplay + '</span>'
                +  '<span class="store-mount-pct">' + pct + '%</span>'
                + '</div>'
                + '<div class="store-mount-bar-wrap">'
                +  '<div class="store-mount-bar' + barClass + '" style="width:' + pct + '%"></div>'
                + '</div>'
                + '<div class="store-mount-detail">'
                +  used + ' / ' + total + ' · ' + avail + ' free'
                + '</div>'
                + '</div>';
        }).join('');
    }

    function _pctNum(d) {
        if (d.pct_num !== undefined) return d.pct_num;
        return parseInt((d.use_pct || '0').replace('%', '')) || 0;
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

        // Circle donut: circumference = 2π×15.5 ≈ 97.39
        var CIRC = 97.39;
        var total = services.length;
        if (total > 0) {
            var activePct   = active   / total;
            var inactivePct = inactive / total;
            var failedPct   = failed   / total;

            var activeDash   = activePct   * CIRC;
            var inactiveDash = inactivePct * CIRC;
            var failedDash   = failedPct   * CIRC;

            // Stacked arcs using stroke-dashoffset
            var activeEl   = document.getElementById('svc-donut-active');
            var inactiveEl = document.getElementById('svc-donut-inactive');
            var failedEl   = document.getElementById('svc-donut-failed');

            if (activeEl) {
                activeEl.style.strokeDasharray  = activeDash + ' ' + (CIRC - activeDash);
                activeEl.style.strokeDashoffset = '0';
            }
            if (inactiveEl) {
                inactiveEl.style.strokeDasharray  = inactiveDash + ' ' + (CIRC - inactiveDash);
                inactiveEl.style.strokeDashoffset = -activeDash;
            }
            if (failedEl) {
                failedEl.style.strokeDasharray  = failedDash + ' ' + (CIRC - failedDash);
                failedEl.style.strokeDashoffset = -(activeDash + inactiveDash);
            }
        }
    }

    /* ---- Recent logs ---- */
    function updateLogs(data) {
        var logs = data.logs || [];
        var el = document.getElementById('recent-logs');
        if (!el) return;
        if (logs.length === 0) {
            el.innerHTML = '<div class="log-entry"><span class="log-msg" style="color:var(--text-muted);">No logs available</span></div>';
            return;
        }
        el.innerHTML = logs.map(function(l) {
            var dotColor = l.level === 'error' ? 'var(--red)' : (l.level === 'warning' ? 'var(--yellow)' : 'var(--green)');
            var ts = (l.timestamp || '--:--').toString().slice(0, 8);
            return '<div class="log-entry">'
                + '<span class="log-time">' + ts + '</span>'
                + '<span class="log-dot" style="background:' + dotColor + ';"></span>'
                + '<span class="log-msg">' + (l.message || '') + '</span>'
                + '</div>';
        }).join('');
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
    function setStatus(cls, text) {
        var el = document.getElementById('sse-status');
        var txt = document.getElementById('sse-status-text');
        if (el) el.className = cls;
        if (txt) txt.textContent = text;
    }

    function handleMessage(e) {
        try {
            var msg = JSON.parse(e.data);
            var metric = msg.metric;
            if (msg.error) {
                console.warn('live: collector failed for', metric, '-', msg.error);
                return;
            }
            var data = msg.data;
            if (metric === 'cpu') { updateCpu(data); }
            else if (metric === 'ram') { updateRam(data); }
            else if (metric === 'thermal') { updateThermal(data); updateThermalTop({zones: data}); }
            else if (metric === 'battery') { updateBattery(data); updateBatteryPill(); }
            else if (metric === 'network') updateNetwork(data);
        } catch (err) {
            console.warn('live: bad SSE payload', err);
        }
    }

    /* Reconnect with exponential backoff, capped at 30s. A single reconnect
       timer is tracked so a burst of error events cannot stack up timers and
       open several parallel streams. */
    var RECONNECT_MIN_MS = 1000;
    var RECONNECT_MAX_MS = 30000;
    var reconnectDelay = RECONNECT_MIN_MS;
    var reconnectTimer = null;
    var evtSource = null;

    function connect() {
        if (evtSource) evtSource.close();
        evtSource = new EventSource(SSE_URL);

        evtSource.onopen = function() {
            reconnectDelay = RECONNECT_MIN_MS;   // reset backoff on success
            setStatus('connected', 'Live');
        };

        evtSource.onmessage = handleMessage;

        evtSource.onerror = function() {
            setStatus('disconnected', 'Reconnecting…');
            evtSource.close();
            if (reconnectTimer !== null) return;   // a retry is already queued
            reconnectTimer = setTimeout(function() {
                reconnectTimer = null;
                reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
                connect();
            }, reconnectDelay);
        };
    }

    connect();

    /* Drop the stream while the tab is hidden — no point burning phone CPU
       and battery collecting sysfs samples nobody is looking at. */
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            if (reconnectTimer !== null) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
            if (evtSource) { evtSource.close(); evtSource = null; }
            setStatus('disconnected', 'Paused');
        } else if (evtSource === null) {
            reconnectDelay = RECONNECT_MIN_MS;
            connect();
        }
    });

    /* ---- REST fetches ---- */
    function fetchJson(url) {
        return fetch(url).then(function(r) { return r.json(); }).catch(function() {});
    }

    fetchJson('/api/system/storage').then(function(d) { if (d) updateStorage(d); });
    fetchJson('/api/system/services').then(function(d) { if (d) updateServices(d); });
    fetchJson('/api/system/logs?limit=10').then(function(d) { if (d) updateLogs(d); });
    fetchJson('/api/device/battery').then(function(d) {
        if (d) {
            if (d.battery && !d.battery.error) { updateBattery(d.battery); updateBatteryPill(); }
            if (d.thermal) updateThermalTop({zones: d.thermal});
        }
    });
    function loadTopProcesses() {
        fetchJson('/api/system/processes?sort_by=mem&limit=10').then(function(d) { if (d) updateTopProcesses(d); });
    }
    loadTopProcesses();
    setInterval(function() {
        if (!document.hidden) loadTopProcesses();
    }, 5000);
})();
