"""
Test ma tran cau hinh tu UI de bat loi thuc te khi click/chon.

Chay:
    python tests/ui_config_matrix_runner.py
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


BASE_URL = "http://127.0.0.1:5000/"
REPORT_FILE = Path("tests/ui_config_report.json")


@dataclass
class RunCase:
    case_id: str
    mode: int
    graph: str
    heuristic: str
    obstacles: int
    vehicles: int
    capacity: int
    time_windows_on: bool
    pop_size: int = 40
    generations: int = 25
    mutation_rate: int = 5
    delivery_points: int = 12
    speed_kmh: int = 40


def _has_control(page, control_id: str) -> bool:
    return bool(
        page.evaluate(
            """
            (id) => Boolean(document.getElementById(id))
            """,
            control_id,
        )
    )


def _set_control_value(page, control_id: str, value: int | str, *, required: bool = True) -> bool:
    ok = page.evaluate(
        """
        ([controlId, newValue]) => {
          const el = document.getElementById(controlId);
          if (!el) return false;
          el.value = String(newValue);
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return true;
        }
        """,
        [control_id, value],
    )
    if not ok and required:
        raise RuntimeError(f"Khong tim thay control #{control_id}")
    return bool(ok)


def _set_time_window_toggle(page, expected_on: bool, *, required: bool = False) -> bool:
    return bool(
        page.evaluate(
            """
            ([expectedOn, isRequired]) => {
              const btn = document.getElementById('timeWindowsToggle');
              if (!btn) {
                if (isRequired) throw new Error('Khong tim thay #timeWindowsToggle');
                return false;
              }
              const target = expectedOn ? '1' : '0';
              btn.dataset.on = target;
              btn.textContent = target === '1' ? 'Dung khung gio giao' : 'Bo khung gio giao';
              btn.dispatchEvent(new Event('input', { bubbles: true }));
              btn.dispatchEvent(new Event('change', { bubbles: true }));
              return true;
            }
            """,
            [expected_on, required],
        )
    )


def _read_text(page, selector: str) -> str:
    loc = page.locator(selector)
    if loc.count() == 0:
        return ""
    return (loc.first.text_content() or "").strip()


def _wait_badge(page, expected: set[str], timeout_ms: int) -> str:
    start = time.time()
    timeout_s = timeout_ms / 1000.0
    while True:
        badge = _read_text(page, "#hbadge").upper()
        if badge in expected:
            return badge
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Qua thoi gian cho hbadge, hien tai: {badge}")
        page.wait_for_timeout(250)


def _collect_runtime_snapshot(page) -> dict:
    return page.evaluate(
        """
        () => {
          const badge = (document.getElementById('hbadge')?.textContent || '').trim();
          const status = (document.getElementById('topstatus')?.textContent || '').trim();
          const runLabel = (document.getElementById('fp-run')?.textContent || '').trim();
          const routeItems = document.querySelectorAll('#rlist .RI, #rlist .ri').length;
          const points = Array.isArray(window.pts) ? window.pts.length : -1;
          const vehicles = Array.isArray(window.vehs) ? window.vehs.length : -1;
          const blocked = Array.isArray(window.pts)
            ? window.pts.filter(p => p && p.id !== 0 && p.undeliverable).length
            : -1;
          return { badge, status, runLabel, routeItems, points, vehicles, blocked };
        }
        """
    )


def _apply_case(page, case: RunCase) -> None:
    page.evaluate("(mode) => window.setMode(mode)", case.mode)

    _set_control_value(page, "np", case.delivery_points, required=True)
    _set_control_value(page, "spd", case.speed_kmh, required=True)
    _set_control_value(page, "obstacles", case.obstacles, required=False)
    _set_control_value(page, "astarGraph", case.graph, required=True)
    _set_control_value(page, "heur", case.heuristic, required=True)
    _set_control_value(page, "vehicles", case.vehicles, required=True)
    _set_control_value(page, "capacity", case.capacity, required=True)
    _set_control_value(page, "ps", case.pop_size, required=True)
    _set_control_value(page, "gens", case.generations, required=True)
    _set_control_value(page, "mr", case.mutation_rate, required=True)
    _set_time_window_toggle(page, case.time_windows_on, required=False)


def _build_cases() -> list[RunCase]:
    cases: list[RunCase] = []

    # Nhom 1: smoke cho 4 mode x 3 graph
    for mode in (0, 1, 2, 3):
        for graph in ("road", "straight", "grid"):
            cases.append(
                RunCase(
                    case_id=f"smoke_m{mode}_{graph}",
                    mode=mode,
                    graph=graph,
                    heuristic="euclidean",
                    obstacles=1,
                    vehicles=2,
                    capacity=24,
                    time_windows_on=True,
                )
            )

    # Nhom 2: stress cac rang buoc mode ket hop chinh (mode 0 + road)
    for heuristic in ("euclidean", "manhattan"):
        for obstacles in (0, 3):
            for vehicles in (1, 4):
                for tw_on in (True, False):
                    cases.append(
                        RunCase(
                            case_id=f"cfg_road_h{heuristic[:3]}_o{obstacles}_v{vehicles}_tw{int(tw_on)}",
                            mode=0,
                            graph="road",
                            heuristic=heuristic,
                            obstacles=obstacles,
                            vehicles=vehicles,
                            capacity=18 if vehicles >= 3 else 24,
                            time_windows_on=tw_on,
                        )
                    )

    return cases


def _run_step_checks(page, base_cases: Iterable[RunCase]) -> list[dict]:
    results: list[dict] = []
    for graph in ("road", "straight", "grid"):
        case = next(c for c in base_cases if c.mode == 0 and c.graph == graph)
        step_id = f"step_{graph}"
        item = {"case_id": step_id, "graph": graph, "ok": False}
        try:
            _apply_case(page, case)
            page.evaluate("() => window.doGen()")
            _wait_badge(page, {"READY", "ERROR"}, timeout_ms=30_000)
            if _read_text(page, "#hbadge").upper() == "ERROR":
                item["error"] = "generate_error"
                item["snapshot"] = _collect_runtime_snapshot(page)
                results.append(item)
                continue

            page.evaluate("() => window.toggleStepMode()")
            page.wait_for_timeout(1_000)
            first = _collect_runtime_snapshot(page)
            page.evaluate("() => window.toggleStepMode()")
            page.wait_for_timeout(400)
            second = _collect_runtime_snapshot(page)

            item["ok"] = (
                "LOI BACKEND PYTHON" not in (first["status"] or "").upper()
                and first["badge"].upper() != "ERROR"
            )
            item["snapshot_enter"] = first
            item["snapshot_exit"] = second
        except Exception as exc:  # noqa: BLE001
            item["error"] = repr(exc)
        results.append(item)
    return results


def main() -> int:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    cases = _build_cases()
    run_results: list[dict] = []
    step_results: list[dict] = []
    page_errors: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        def _on_page_error(exc):
            page_errors.append(str(exc))

        def _on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("pageerror", _on_page_error)
        page.on("console", _on_console)

        page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(1_500)

        for case in cases:
            case_result = asdict(case)
            case_result["ok"] = False
            case_result["errors"] = []

            start_page_error = len(page_errors)
            start_console_error = len(console_errors)
            try:
                _apply_case(page, case)
                page.evaluate("() => window.doGen()")
                gen_badge = _wait_badge(page, {"READY", "ERROR"}, timeout_ms=30_000)
                case_result["generate_badge"] = gen_badge
                case_result["generate_status"] = _read_text(page, "#topstatus")
                if gen_badge == "ERROR":
                    case_result["errors"].append("generate_error")
                    case_result["snapshot"] = _collect_runtime_snapshot(page)
                    run_results.append(case_result)
                    continue

                page.evaluate("() => window.doRun()")
                try:
                    run_badge = _wait_badge(page, {"DONE", "ERROR", "BLOCKED"}, timeout_ms=90_000)
                except TimeoutError as exc:
                    run_badge = _read_text(page, "#hbadge").upper()
                    if run_badge != "BLOCKED":
                        case_result["errors"].append(f"run_timeout: {exc}")

                case_result["run_badge"] = run_badge
                case_result["snapshot"] = _collect_runtime_snapshot(page)
                case_result["ok"] = run_badge in {"DONE", "BLOCKED"}
                if run_badge == "BLOCKED":
                    case_result["blocked_by_obstacle"] = True
                elif run_badge != "DONE":
                    case_result["errors"].append("run_not_done")
            except PlaywrightTimeoutError as exc:
                case_result["errors"].append(f"playwright_timeout: {exc}")
            except Exception as exc:  # noqa: BLE001
                case_result["errors"].append(repr(exc))

            case_result["page_errors"] = page_errors[start_page_error:]
            case_result["console_errors"] = console_errors[start_console_error:]
            if case_result["page_errors"]:
                case_result["ok"] = False
            if case_result["console_errors"]:
                case_result["ok"] = False
            run_results.append(case_result)

        # Chay them nhom A* Step cho 3 graph mode.
        step_results = _run_step_checks(page, cases)
        browser.close()

    failed_runs = [x for x in run_results if not x.get("ok")]
    failed_steps = [x for x in step_results if not x.get("ok")]

    report = {
        "base_url": BASE_URL,
        "run_total": len(run_results),
        "run_failed": len(failed_runs),
        "step_total": len(step_results),
        "step_failed": len(failed_steps),
        "failed_case_ids": [x["case_id"] for x in failed_runs] + [x["case_id"] for x in failed_steps],
        "run_results": run_results,
        "step_results": step_results,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"UI matrix done. run_failed={len(failed_runs)}, step_failed={len(failed_steps)}")
    print(f"Report: {REPORT_FILE}")
    return 1 if (failed_runs or failed_steps) else 0


if __name__ == "__main__":
    raise SystemExit(main())
