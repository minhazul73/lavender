import { useState, useCallback } from 'react';

/**
 * Provides clipboard copy with a transient "copied" indicator per key.
 * `copiedKey` is set to the copied key string for 2 seconds, then reset to null.
 */
export function useClipboard(): {
  copiedKey: string | null;
  copy: (text: string, key: string) => void;
} {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const copy = useCallback((text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    });
  }, []);

  return { copiedKey, copy };
}
