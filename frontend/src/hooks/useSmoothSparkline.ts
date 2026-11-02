import { useState, useEffect, useRef } from 'react';
import { normalizeBuffer, buildSparkPaths, buildCoreSparkPath } from '../utils/sparkline';

/**
 * Hook to smoothly animate SVG sparkline paths using requestAnimationFrame.
 * Eliminates sudden jumps when new metric packets arrive.
 */
export function useSmoothSparkline(
  targetBuffer: number[],
  w = 100,
  h = 32,
  options: {
    duration?: number;
    minRange?: number;
    clampMin?: number;
    clampMax?: number;
  } = {},
): { line: string; area: string } {
  const {
    duration = 550,
    minRange = 10,
    clampMin,
    clampMax,
  } = options;

  const currentRef = useRef<number[]>([]);
  const animRef = useRef<number | null>(null);
  const [paths, setPaths] = useState<{ line: string; area: string }>(() => {
    if (!targetBuffer || targetBuffer.length === 0) return { line: '', area: '' };
    return buildSparkPaths(normalizeBuffer(targetBuffer, 30), w, h, minRange, clampMin, clampMax);
  });

  useEffect(() => {
    if (!targetBuffer || targetBuffer.length === 0) return;
    const target = normalizeBuffer(targetBuffer, 30);

    if (currentRef.current.length !== target.length || typeof requestAnimationFrame === 'undefined') {
      currentRef.current = [...target];
      setPaths(buildSparkPaths(target, w, h, minRange, clampMin, clampMax));
      return;
    }

    const start = [...currentRef.current];
    const startTime = performance.now();

    if (animRef.current) {
      cancelAnimationFrame(animRef.current);
    }

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      // easeOutCubic
      const ease = 1 - Math.pow(1 - progress, 3);

      const interpolated = start.map((s, i) => s + (target[i] - s) * ease);
      currentRef.current = interpolated;
      setPaths(buildSparkPaths(interpolated, w, h, minRange, clampMin, clampMax));

      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      } else {
        animRef.current = null;
      }
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
      }
    };
  }, [targetBuffer, w, h, duration, minRange, clampMin, clampMax]);

  return paths;
}

export function useSmoothCoreSparkline(
  targetBuffer: number[],
  w = 80,
  h = 24,
  duration = 400,
): string {
  const currentRef = useRef<number[]>([]);
  const animRef = useRef<number | null>(null);
  const [path, setPath] = useState<string>(() => {
    if (!targetBuffer || targetBuffer.length === 0) return '';
    return buildCoreSparkPath(normalizeBuffer(targetBuffer, 20), w, h);
  });

  useEffect(() => {
    if (!targetBuffer || targetBuffer.length === 0) return;
    const target = normalizeBuffer(targetBuffer, 20);

    if (currentRef.current.length !== target.length || typeof requestAnimationFrame === 'undefined') {
      currentRef.current = [...target];
      setPath(buildCoreSparkPath(target, w, h));
      return;
    }

    const start = [...currentRef.current];
    const startTime = performance.now();

    if (animRef.current) {
      cancelAnimationFrame(animRef.current);
    }

    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / duration);
      const ease = 1 - Math.pow(1 - progress, 3);

      const interpolated = start.map((s, i) => s + (target[i] - s) * ease);
      currentRef.current = interpolated;
      setPath(buildCoreSparkPath(interpolated, w, h));

      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      } else {
        animRef.current = null;
      }
    };

    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) {
        cancelAnimationFrame(animRef.current);
      }
    };
  }, [targetBuffer, w, h, duration]);

  return path;
}

