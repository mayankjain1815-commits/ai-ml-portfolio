"""A tiny, dependency-free model registry.

Real MLOps shops use MLflow or weights & biases; this project does the same
job with two files per version — a pickled estimator and a manifest entry —
because the point is the *mechanics*: versioning, promotion, and provenance.

Layout::

    registry/
    ├── model_v1.pkl
    ├── model_v2.pkl
    └── manifest.json        # {"latest_version": 2, "models": [...]}
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RegistryError(RuntimeError):
    """Raised when a version is requested that was never registered."""


class ModelRegistry:
    """Versioned model store rooted at ``root`` (created on first use)."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._manifest_path = self.root / "manifest.json"

    # -- filesystem helpers -------------------------------------------------

    def _model_path(self, version: int) -> Path:
        return self.root / f"model_v{version}.pkl"

    def _read_manifest(self) -> dict[str, Any]:
        if not self._manifest_path.exists():
            return {"latest_version": 0, "models": []}
        with self._manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_manifest(self, manifest: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self._manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, default=str)
            handle.write("\n")

    # -- public API ---------------------------------------------------------

    def register(
        self,
        *,
        model: Any,
        algorithm: str,
        hyperparams: dict[str, Any],
        metrics: dict[str, float],
        dataset_hash: str,
        feature_names: list[str],
        dataset_seed: int | None = None,
        n_rows: int | None = None,
        notes: str = "",
    ) -> int:
        """Freeze ``model`` as the next version and return its version number.

        ``dataset_hash`` is the SHA-256 of the training frame, so a future run
        can verify (or rebuild) the exact distribution the model learned on.
        ``dataset_seed``/``n_rows`` let the monitor and dashboard regenerate
        that distribution offline instead of shipping a 12k-row CSV.
        """
        manifest = self._read_manifest()
        version = manifest["latest_version"] + 1

        entry = {
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "algorithm": algorithm,
            "hyperparams": hyperparams,
            "metrics": metrics,
            "dataset_hash": dataset_hash,
            "dataset_seed": dataset_seed,
            "n_rows": n_rows,
            "feature_names": feature_names,
            "notes": notes,
        }
        self.root.mkdir(parents=True, exist_ok=True)
        with self._model_path(version).open("wb") as handle:
            pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)

        manifest["latest_version"] = version
        manifest["models"].append(entry)
        self._write_manifest(manifest)
        return version

    def list_versions(self) -> list[dict[str, Any]]:
        """All registered versions, newest first."""
        return list(reversed(self._read_manifest()["models"]))

    def latest(self) -> dict[str, Any] | None:
        """Manifest entry of the most recent version, or ``None`` if empty."""
        models = self._read_manifest()["models"]
        return models[-1] if models else None

    def model_path(self, version: int) -> Path:
        """Path of a version's pickle, verifying it exists."""
        path = self._model_path(version)
        if not path.exists():
            raise RegistryError(
                f"model_v{version}.pkl is missing (registered but file deleted?)"
            )
        return path

    def load(self, version: int | None = None) -> tuple[Any, dict[str, Any]]:
        """Load ``(model, manifest_entry)``; ``None`` means the latest version."""
        manifest = self._read_manifest()
        if version is None:
            version = manifest["latest_version"]
        if version < 1:
            raise RegistryError("registry is empty — run `python -m model_watch train` first")
        with self.model_path(version).open("rb") as handle:
            model = pickle.load(handle)
        entry = next((m for m in manifest["models"] if m["version"] == version), None)
        if entry is None:
            raise RegistryError(f"manifest has no entry for version {version}")
        return model, entry