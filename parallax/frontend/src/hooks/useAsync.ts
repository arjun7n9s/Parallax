import { useCallback, useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Run an async fetcher and expose {data, loading, error, reload}. Aborts/ignores
 * stale results on dependency change, so pages get clean loading → data | error
 * → empty states without bespoke boilerplate. The fetcher should throw on
 * failure (ApiError); the message is surfaced to the UI.
 */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const live = useRef(true);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    live.current = true;
    setLoading(true);
    setError(null);
    fn()
      .then((res) => {
        if (live.current) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (live.current) {
          setError(e instanceof Error ? e.message : "Something went wrong");
          setLoading(false);
        }
      });
    return () => {
      live.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, loading, error, reload };
}
