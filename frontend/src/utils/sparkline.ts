/**
 * Normalize a ring-buffer of arbitrary length to exactly targetLen data points.
 * Pads with zeros at the front if shorter, trims the oldest if longer.
 */
export function normalizeBuffer(buf: number[], targetLen = 30): number[] {
  if (!buf || buf.length === 0) return new Array(targetLen).fill(0);
  if (buf.length >= targetLen) return buf.slice(buf.length - targetLen);
  const pad = new Array(targetLen - buf.length).fill(buf[0]);
  return [...pad, ...buf];
}

/**
 * Build smooth Catmull-Rom cubic bezier SVG path strings (line and area)
 * for a data buffer, matching the original live telemetry engine.
 */
export function buildSparkPaths(
  buf: number[],
  w = 100,
  h = 32,
  minRange = 10,
  clampMin?: number,
  clampMax?: number,
): { line: string; area: string } {
  if (!buf || buf.length < 2) return { line: '', area: '' };

  let min = Math.min(...buf);
  let max = Math.max(...buf);

  if (clampMin !== undefined) min = Math.min(min, clampMin);
  if (clampMax !== undefined) max = Math.max(max, clampMax);

  const currentRange = max - min;
  if (currentRange < minRange) {
    const padRange = (minRange - currentRange) / 2;
    min = clampMin !== undefined ? Math.max(clampMin, min - padRange) : min - padRange;
    max = clampMax !== undefined ? Math.min(clampMax, max + padRange) : max + padRange;
  }
  const range = max - min || 1;
  const pad = h * 0.08;

  const pts = buf.map((v, i) => ({
    x: parseFloat(((i / (buf.length - 1)) * w).toFixed(2)),
    y: parseFloat((pad + (1 - (v - min) / range) * (h - pad * 2)).toFixed(2)),
  }));

  const t = 0.4;
  const ctrlPts = (
    p0: { x: number; y: number },
    p1: { x: number; y: number },
    p2: { x: number; y: number },
    p3: { x: number; y: number },
  ) => ({
    cp1x: p1.x + (p2.x - p0.x) * t,
    cp1y: p1.y + (p2.y - p0.y) * t,
    cp2x: p2.x - (p3.x - p1.x) * t,
    cp2y: p2.y - (p3.y - p1.y) * t,
  });

  let line = `M${pts[0].x},${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c = ctrlPts(p0, p1, p2, p3);
    line += ` C${c.cp1x.toFixed(2)},${c.cp1y.toFixed(2)} ${c.cp2x.toFixed(2)},${c.cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }

  const last = pts[pts.length - 1];
  const area = `${line} L${last.x},${h} L${pts[0].x},${h} Z`;
  return { line, area };
}

/**
 * Build SVG mini sparkline path for per-core micro tiles
 */
export function buildCoreSparkPath(buf: number[], w = 80, h = 24): string {
  if (!buf || buf.length < 2) return '';
  const maxV = Math.max(...buf, 100);
  let points = '';
  buf.forEach((v, idx) => {
    const x = (idx / (buf.length - 1)) * w;
    const y = h - (Math.max(0, v) / maxV) * h;
    points += (idx === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1) + ' ';
  });
  return points;
}

