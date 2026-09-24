import React, { useMemo } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  fillOpacity?: number;
  gradientId?: string;
  strokeWidth?: number;
  className?: string;
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 100,
  height = 32,
  color = 'var(--purple)',
  fillOpacity = 0.3,
  gradientId,
  strokeWidth = 1.2,
  className = '',
}) => {
  const gid = useMemo(() => gradientId || `grad-${Math.random().toString(36).substring(2, 9)}`, [gradientId]);

  const { linePath, areaPath } = useMemo(() => {
    if (!data || data.length < 2) {
      return { linePath: '', areaPath: '' };
    }

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = height * 0.1;

    const pts = data.map((v, i) => ({
      x: parseFloat(((i / (data.length - 1)) * width).toFixed(2)),
      y: parseFloat((pad + (1 - (v - min) / range) * (height - pad * 2)).toFixed(2)),
    }));

    const t = 0.4; // Catmull-Rom tension
    let line = `M${pts[0].x},${pts[0].y}`;

    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];

      const cp1x = p1.x + (p2.x - p0.x) * t;
      const cp1y = p1.y + (p2.y - p0.y) * t;
      const cp2x = p2.x - (p3.x - p1.x) * t;
      const cp2y = p2.y - (p3.y - p1.y) * t;

      line += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
    }

    const last = pts[pts.length - 1];
    const area = `${line} L${last.x},${height} L${pts[0].x},${height} Z`;

    return { linePath: line, areaPath: area };
  }, [data, width, height]);

  if (!linePath) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        style={{ width: '100%', height: `${height}px` }}
        className={`sparkline ${className}`}
      />
    );
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      style={{ width: '100%', height: `${height}px`, overflow: 'hidden' }}
      className={`sparkline ${className}`}
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={fillOpacity} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gid})`} />
      <path d={linePath} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    </svg>
  );
};
