import { useEffect, useRef, useState } from 'react';

async function fetchSnapshot() {
  const response = await fetch('/api/dashboard');
  if (!response.ok) throw new Error(`Dashboard unavailable (${response.status})`);
  const payload = await response.json();
  return payload.data;
}

export function useSentinel({ onAlert } = {}) {
  const [snapshot, setSnapshot] = useState(null);
  const [connection, setConnection] = useState('connecting');
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const seenAlerts = useRef(new Set());
  const initialized = useRef(false);
  const onAlertRef = useRef(onAlert);
  const mounted = useRef(true);
  const lastSocketMessage = useRef(0);

  onAlertRef.current = onAlert;

  const applySnapshot = (nextSnapshot) => {
    if (!mounted.current || !nextSnapshot) return;

    const incomingAlerts = nextSnapshot.alerts ?? [];
    if (initialized.current) {
      incomingAlerts.forEach((alert) => {
        if (!seenAlerts.current.has(alert.id)) {
          onAlertRef.current?.(alert);
        }
      });
    }
    incomingAlerts.forEach((alert) => seenAlerts.current.add(alert.id));
    initialized.current = true;

    setSnapshot(nextSnapshot);
    setLastUpdated(new Date());
    setError(null);
  };

  useEffect(() => {
    mounted.current = true;
    let disposed = false;

    fetchSnapshot()
      .then((data) => {
        if (!disposed) {
          applySnapshot(data);
          setConnection('polling');
        }
      })
      .catch((loadError) => {
        if (!disposed) {
          setError(loadError.message);
          setConnection('offline');
        }
      });

    return () => {
      disposed = true;
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let pingTimer;
    let attempts = 0;
    let disposed = false;

    const scheduleReconnect = () => {
      if (disposed) return;
      attempts += 1;
      const delay = Math.min(12_000, 900 * 2 ** Math.min(attempts, 4));
      reconnectTimer = window.setTimeout(connect, delay);
    };

    const connect = () => {
      if (disposed) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

      socket.onopen = () => {
        if (disposed) return;
        attempts = 0;
        setConnection('live');
        setError(null);
        pingTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'ping' }));
          }
        }, 20_000);
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'snapshot') {
            lastSocketMessage.current = Date.now();
            applySnapshot(message.data);
            setConnection('live');
          }
        } catch {
          // Ignore malformed frames; polling remains available as a fallback.
        }
      };

      socket.onerror = () => {
        if (!disposed) setConnection('polling');
      };

      socket.onclose = () => {
        if (disposed) return;
        window.clearInterval(pingTimer);
        setConnection('polling');
        scheduleReconnect();
      };
    };

    connect();

    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer);
      window.clearInterval(pingTimer);
      socket?.close();
    };
  }, []);

  useEffect(() => {
    const poll = async () => {
      if (Date.now() - lastSocketMessage.current < 9_000) return;
      try {
        const data = await fetchSnapshot();
        applySnapshot(data);
        setConnection((current) => (current === 'offline' ? 'polling' : current));
      } catch (loadError) {
        if (mounted.current) {
          setError(loadError.message);
          setConnection((current) => (current === 'live' ? current : 'offline'));
        }
      }
    };

    const timer = window.setInterval(poll, 12_000);
    return () => window.clearInterval(timer);
  }, []);

  return { snapshot, connection, error, lastUpdated };
}
