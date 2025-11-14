import { useEffect, useRef } from "react";

export function usePolling(callback: () => Promise<void> | void, intervalMs: number, enabled: boolean) {
  const savedCallback = useRef<typeof callback>();

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    let timer: number;

    const tick = async () => {
      if (savedCallback.current) {
        await savedCallback.current();
      }
      timer = window.setTimeout(tick, intervalMs);
    };

    timer = window.setTimeout(tick, intervalMs);

    return () => window.clearTimeout(timer);
  }, [enabled, intervalMs]);
}
