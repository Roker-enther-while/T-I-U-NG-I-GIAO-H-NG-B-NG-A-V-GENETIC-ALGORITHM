import json
import re
import uuid
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = PROJECT_ROOT / "logs" / "algorithm_runs"
HISTORY_ROOT = LOG_ROOT / "history"


def _safe_name(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value).strip().lower()).strip("_") or "run"


def _json_default(value):
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def route_summary(routes):
    routes = routes or []
    return {
        "route_count": len(routes),
        "routes": routes,
        "route_lengths": [max(0, len(route) - 2) for route in routes],
        "total_stops": sum(max(0, len(route) - 2) for route in routes),
    }


def matrix_summary(matrix, point_count):
    values = [
        value[0]
        for (source, target), value in (matrix or {}).items()
        if source != target and value and value[0] != float("inf")
    ]
    if not values:
        return {
            "point_count": point_count,
            "pair_count": 0,
            "min_km": 0,
            "max_km": 0,
            "avg_km": 0,
        }
    return {
        "point_count": point_count,
        "pair_count": len(values),
        "min_km": round(min(values), 2),
        "max_km": round(max(values), 2),
        "avg_km": round(sum(values) / len(values), 2),
    }


class AlgorithmRunLogger:
    def __init__(self, algorithm, config=None):
        self.algorithm = _safe_name(algorithm)
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
        self.latest_path = LOG_ROOT / f"latest_{self.algorithm}.jsonl"
        self.history_path = HISTORY_ROOT / f"{self.run_id}_{self.algorithm}.jsonl"
        self._files = [
            self.latest_path.open("w", encoding="utf-8"),
            self.history_path.open("w", encoding="utf-8"),
        ]
        self.event("start", config=config or {})

    def event(self, event, **payload):
        record = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "algorithm": self.algorithm,
            "event": event,
            **payload,
        }
        line = json.dumps(record, ensure_ascii=False, default=_json_default)
        for handle in self._files:
            handle.write(line + "\n")
            handle.flush()

    def close(self):
        for handle in self._files:
            if not handle.closed:
                handle.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, _traceback):
        if exc is not None:
            self.event("error", message=str(exc), error_type=getattr(exc_type, "__name__", "Exception"))
        self.close()
