# Dashboard UI Assessment & Improvement Backlog

**Generated:** 2026-08-16  
**Context:** RN7 Linux Dashboard (`/home/rahat/hermes-device-dashboard`)  
**Status:** Backlog — not yet actioned. User intends to tackle improvements in chunks.

---

## What the research says (from 6 articles: UXPin, UX Pilot, Qlik, Mockplus, Pencil & Paper, UXDesign.cc)

1. **Lead with the answer, not the navigation** — The overview should answer "is my device OK?" in under 3 seconds. Critical data (battery, memory pressure, service failures, disk space, network) should be visible without clicking tabs.

2. **Information hierarchy over data dumping** — Don't scatter everything. Group related data into purposeful cards. 5–6 cards max on the initial view is the sweet spot; more than that dilutes attention.

3. **Card UI patterns with intentional density** — Cards shouldn't be half-empty. If you pull data, use the card real estate to show the most relevant slice, not just one big number.

4. **Status at a glance** — Modern system dashboards surface a health summary (often a status bar or row of indicators) so the user knows the overall state before drilling in.

5. **Actionable, not just observable** — Data should connect to actions. If battery is low, the card should hint at what to do. If a service failed, the card should link to it.

6. **Avoid hiding high-value data behind tabs** — Tabs are for *detailed* views, not for data that belongs on the landing screen. Thermal zones, CPU freq, network latency, top processes, package updates — these are all pulled by the API but invisible from `/`.

---

## What's dull about the current dashboard

### 1. The overview page is a skeleton, not a dashboard

Six cards, each showing one stat:

- **Services:** "27 active of 42 total" — no failed/launched/recently-changed count
- **Storage:** "48.8G total / 6.8G used / 39.5G free" — one number per line, lots of empty card space. No partition breakdown, no mount table, no largest directories
- **Memory:** "RAM Used of total · free" — generic labels, no swap, no cache, no pressure indicator
- **Network:** emoji + "Gateway OK · Internet OK" — actual latency numbers (which the API returns) are hidden
- **Battery:** "27% charging" — temperature, voltage, charge rate, time-to-full are all pulled but not shown
- **Hermes:** "✅ Gateway / ✅ Dashboard running" — binary, no session count, no memory pressure, no network quality detail

Each card is roughly 280px wide × ~100px tall of actual content. The rest is card chrome. On desktop it looks sparse.

### 2. High-value data lives one tab-click away

| Data we pull | Where it is | Visible from `/`? |
|---|---|---|
| Battery temperature | Battery tab | ❌ |
| Battery voltage, charge rate, time-to-full/empty | Battery tab | ❌ |
| Thermal zones (12 zones, temps) | Thermal tab | ❌ |
| CPU freq per core, governors, min/max | CPU tab | ❌ |
| Network latency (gateway + internet ping ms) | Connectivity tab | ❌ |
| WiFi signal, quality, channel, TX rate | WiFi tab | ❌ |
| DNS servers | DNS tab | ❌ |
| Top processes, system load (1/5/15 min) | Processes page | ❌ |
| Available package updates | Packages page | ❌ |
| Logged-in users, sudoers | Users page | ❌ |
| Service failed/inactive count | Services page (filter) | ❌ |
| Disk mount breakdown, largest dirs | Storage page (was removed) | ❌ |

The overview is the page a user sees 90% of the time. Right now it shows maybe 20% of the data the system is collecting.

### 3. No system health summary

No single place says "everything is fine" or "battery low + disk 90% full + 3 services failed". A status row or health pill at the top of the overview — even just 4–5 colored indicators — would give the user the answer to "is my device OK?" without scanning 6 cards.

### 4. Cards don't connect to detail pages

The Services card has a "View All" button. Battery, Memory, Network, Storage, Hermes cards don't. A user who sees "27% battery" on the overview has no obvious way to get to the battery page with temperature, voltage, and charge rate — they'd have to know the sidebar exists and click it.

### 5. The storage overview is too thin

Stripped down to one root-disk stat when the Storage page was removed. That saved space but left a gap: the overview card for storage now shows less than it could (no mount table, no usage breakdown, no largest directories). A middle ground — compact mount list + top 3 largest directories — would fit in a card or a small expandable section.

### 6. No visual urgency / alerting

Low battery (<20%), high temperature (>70°C), failed services, disk >90% full, high latency — all represented as text values. No color coding at the card level, no alert row, no "warning" state that makes the card visually distinct. CSS has `.alert-warning`, `.badge.crit`, etc. but they're not wired into the overview cards.

### 7. Tab UX is fragmented

Battery, Network pages use vanilla JS tab switching (not HTMX). Each tab fetches its own data independently. No shared data fetch, no loading coordination, no tab-state persistence. Switching tabs feels like separate pages.

### 8. Power page is two buttons with no context

Reboot and poweroff. No current power state, no battery-aware advice, no suspend option, no confirmation of what's running before you reboot.

### 9. Hermes status is binary with no depth

"Gateway ✅ / Dashboard ✅" — that's it. The API actually returns session count, memory pressure, network quality, cron jobs, gateway logs. None of that reaches the overview or the Hermes page meaningfully.

### 10. No device context on the overview

Sidebar says "Redmi Note 7" but the overview doesn't surface device model, battery technology (Li-ion), vendor, serial, CPU architecture — all available from the battery API. For a device-specific dashboard, this is low-effort missed context.

---

## What could be improved (not in edit order — just observations)

### High impact — makes the overview actually useful

- **Enrich each overview card with 1–2 extra data points** from data already being fetched. Battery card: add temperature + charge rate. Network card: add actual latency numbers. Memory card: add swap + pressure. Storage card: add mount count + largest directory. Hermes card: add session count + memory pressure. Services card: add failed/inactive count, not just active.
- **Add a health/status row** at the top of the overview — 4–6 small indicators (battery, disk, memory, services, network) with color coding. Single biggest UX upgrade: the user sees the device state in one glance.
- **Add "View details →" links** to every overview card so the user knows where to go for more.

### Medium impact — fills blank space with real data

- **Compact storage section on overview** — instead of one root-disk stat, show a small mount table (device, mount, size, used, avail, %) + top 3 largest directories. Fits in a card or a collapsible section.
- **Processes preview on overview** — top 3 processes by CPU or memory, plus load average (1/5/15). Currently the processes page exists but the overview shows nothing about process load.
- **Packages preview on overview** — count of available updates, maybe the top 2 outdated packages. Currently hidden on the packages page.
- **Users preview on overview** — logged-in user count, current user. Currently hidden on the users page.

### Medium impact — visual hierarchy and alerting

- **Color-code card states** — battery card turns yellow/red at low %, storage card at high usage, services card when failures exist. Use existing CSS (`.badge.crit`, `.alert-warning`, etc.).
- **Add a small sparkline or trend indicator** where apples-to-apples — battery % over time, temperature trend, memory usage trend. Point-in-time numbers are less useful than "battery was 35% an hour ago, now 27%".
- **Wire existing alert CSS** into the overview so warning states are visually distinct, not just text.

### Lower impact — polish and context

- **Device info block** on overview or sidebar — model, vendor, battery tech, CPU architecture. Small, static, adds device specificity.
- **Power page context** — show current battery % and a warning if battery is low before offering reboot. Add suspend option if available.
- **Hermes page depth** — surface session count, memory pressure, network quality, recent cron activity on the Hermes page instead of just binary active/inactive.
- **Tab UX consolidation** — consider HTMX-driven tabs instead of vanilla JS for Battery and Network pages, so tab switches feel like part of one page rather than independent loads.

### Structural — not UI, but affects UI

- **One shared data fetch on page load** for pages that show multiple tabs (Battery, Network). Currently each tab fetches independently — wasteful and uncoordinated.
- **Overview card navigation consistency** — either all cards link to their detail page, or none do. Right now it's inconsistent.

---

## What's already decent

- Dark theme, card grid, sidebar nav, and color palette are solid — match the system dashboard aesthetic that articles recommend (clean, dense, purpose-built).
- CSS has good building blocks: status indicators, badges, progress bars, alerts, thermal cards, battery gauge, CPU cards, interface cards. The problem isn't missing CSS — it's that the overview page doesn't use most of it.
- The API layer pulls a lot of useful data. The gap is purely in what gets shown on the landing page vs. what stays hidden.
- HTMX + fetch hybrid approach works. The issue is how much of the fetched data gets rendered.

---

## Bottom line

The dashboard is functional but reads like a skeleton — six thin cards on the overview, with most of the actual system data one tab-click away. The research consensus is that a dashboard's job is to answer "what's the state of my system?" in under 3 seconds, and right now the overview doesn't do that. The data is all there in the APIs; it just isn't surfaced where the user looks first.

---

## Backlog (chunked — to be tackled incrementally)

_Date each chunk as it's started. This section grows as work progresses._

### Chunk backlog (empty — waiting for user direction)

_No chunks assigned yet. User will pick chunks from the improvement list above._
