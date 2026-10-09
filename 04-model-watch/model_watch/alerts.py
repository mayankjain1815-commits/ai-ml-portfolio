"""Alert routing: deduplication, two output sinks, and a pluggable notifier.

Design rules for a monitoring system that must *not* page people every minute:

* The same ``(feature, severity)`` fired within ``window_hours`` collapses into
  one record with a rising ``count``. New/rolled-over occurrences open a new
  record. Severity changes are *not* deduplicated — escalation always fires.
* Everything lands in ``alerts.json`` (machine-readable, what the dashboard
  reads). ``alerts.log`` is the human-readable chronological trail.
* ``notify()`` is the single seam where a real webhook would go (Slack/email/
  PagerDuty): it does nothing but print today, with a comment marking the
  exactly-one place to add ``requests.post(...)``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from model_watch.drift import Detection, Severity

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def notify(message: str) -> None:
    """Outbound alert hook.

    This is where a real integration goes in production. For example::

        requests.post(
            "https://hooks.slack.com/services/T000000/B000000/XXXX",
            json={"text": message},
            timeout=5,
        )

    A webhook post is fire-and-forget — log locally regardless, never let a
    slow or failing notifier block the monitoring loop.
    """
    print(f"[notify] {message}")


@dataclass
class AlertRecord:
    """State of one deduplication group, mirrored 1:1 into alerts.json."""

    feature: str
    metric: str
    severity: Severity
    value: float
    count: int
    first_seen: str
    last_seen: str
    message: str


class AlertManager:
    """Deduplicates and persists alerts; call :meth:`raise_event` from the monitor."""

    def __init__(
        self,
        *,
        log_path: str | Path,
        json_path: str | Path,
        window_hours: float = 24.0,
        clock: Clock = _utc_now,
    ) -> None:
        self.log_path = Path(log_path)
        self.json_path = Path(json_path)
        self.window = timedelta(hours=window_hours)
        self.clock = clock
        self._records: dict[tuple[str, Severity], AlertRecord] = {}
        self._order: list[tuple[str, Severity]] = []
        self._load()

    # -- persistence ----------------------------------------------------------

    def _load(self) -> None:
        if not self.json_path.exists():
            return
        try:
            with self.json_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return
        for item in payload.get("alerts", []):
            key = (item["feature"], item["severity"])
            self._records[key] = AlertRecord(**item)
            self._order.append(key)

    def _save(self) -> None:
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        with self.json_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {"alerts": [self._records[k].__dict__ for k in self._order]},
                handle,
                indent=2,
            )
            handle.write("\n")

    def _append_log(self, record: AlertRecord) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        window = self.window
        stamp = datetime.fromisoformat(record.last_seen)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        line = (
            f"{stamp.isoformat()} [{record.severity.upper()}] "
            f"{record.feature} {record.metric}={record.value:.4f} "
            f"(count={record.count} within {window.total_seconds() / 3600:.0f}h)\n"
        )
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    # -- public API ------------------------------------------------------------

    def raise_event(self, detection: Detection) -> AlertRecord | None:
        """Route one detection through deduplication.

        Returns the record that was created *or* updated, or ``None`` when the
        event is a silent repeat of an active record (still counted).
        """
        if detection.severity == "ok":
            return None  # recovered states are tracked by the monitor, not paged

        key = (detection.feature, detection.severity)
        now = self.clock()
        stamp = now.isoformat()
        message = (
            f"{detection.feature}: {detection.metric}={detection.value:.4f} "
            f"({detection.severity})"
        )

        active = self._records.get(key)
        if active is not None:
            since = datetime.fromisoformat(active.last_seen)
            if since.tzinfo is None:
                since = since.replace(tzinfo=timezone.utc)
            # Within the window → this is the *same* ongoing condition, not a
            # new one: bump the count and stay silent. `<=` (not `<`) so a
            # condition that persists daily never "re-pages"—it pages once and
            # counts its duration. After `window` of silence, a repeat is a
            # fresh alert and opens a new record.
            if now - since <= self.window:
                active.count += 1
                active.last_seen = stamp
                active.value = detection.value
                active.metric = detection.metric
                active.message = message
                self._save()
                return active

        record = AlertRecord(
            feature=detection.feature,
            metric=detection.metric,
            severity=detection.severity,
            value=detection.value,
            count=1,
            first_seen=stamp,
            last_seen=stamp,
            message=message,
        )
        self._records[key] = record
        if key not in self._order:
            self._order.append(key)
        self._append_log(record)
        notify(message)
        self._save()
        return record

    def records(self) -> list[AlertRecord]:
        """Active records, newest first (by ``last_seen``)."""
        live = [(r.last_seen, k) for k, r in self._records.items() if r.count > 0]
        ordered = sorted(live, reverse=True)
        return [self._records[k] for _, k in ordered]

    def summary(self) -> dict[str, int]:
        """Count of records by severity (what the report/dashboard show)."""
        counts: dict[str, int] = {"ok": 0, "warn": 0, "alert": 0}
        for record in self.records():
            counts[record.severity] += 1
        return counts