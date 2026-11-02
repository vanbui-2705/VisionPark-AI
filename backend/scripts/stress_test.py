"""VisionPark Cash Checkout Peak-Hour Stress & Performance Test.

Executes concurrent parking lifecycles (Check-In -> Cash Preview -> Cash Check-Out)
using ThreadPoolExecutor and httpx, benchmarking system throughput and latency.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

STEP_CHECKIN = "1. Check-In"
STEP_PREVIEW = "2. Cash Preview"
STEP_CHECKOUT = "3. Cash Check-Out"


@dataclass
class RequestRecord:
    """Record of an individual HTTP request."""

    step_name: str
    status_code: int
    duration_ms: float
    success: bool
    error_message: str | None = None


@dataclass
class CycleRecord:
    """Record of an entire Check-In -> Preview -> Check-Out parking lifecycle."""

    cycle_index: int
    license_plate: str
    success: bool
    total_duration_ms: float
    requests: list[RequestRecord] = field(default_factory=list)
    error_step: str | None = None


def compute_percentile(sorted_values: list[float], pct: float) -> float:
    """Compute percentile using linear interpolation between closest ranks."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    d = k - f
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * d


def load_env_defaults() -> dict[str, str]:
    """Load configuration values from environment or local .env files."""
    env_vars: dict[str, str] = {}
    try:
        from dotenv import dotenv_values

        search_paths = [
            Path(".env"),
            Path("../.env"),
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parents[1] / ".env",
        ]
        for path in search_paths:
            if path.is_file():
                for k, v in dotenv_values(path).items():
                    if v is not None and k not in env_vars:
                        env_vars[k] = v
    except ImportError:
        pass

    for k, v in os.environ.items():
        env_vars.setdefault(k, v)

    return env_vars


def create_mock_transport() -> httpx.MockTransport:
    """Create an in-memory mock HTTP transport for dry-run and local verification."""
    mock_sessions: dict[str, dict[str, Any]] = {}
    in_lane_id = "00000000-0000-0000-0000-000000000001"
    out_lane_id = "00000000-0000-0000-0000-000000000002"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method
        time.sleep(random.uniform(0.003, 0.012))

        if path.endswith("/api/v1/auth/login") and method == "POST":
            return httpx.Response(
                200,
                json={
                    "access_token": f"mock-jwt-token-{uuid4().hex[:12]}",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "user": {
                        "id": str(uuid4()),
                        "username": "operator",
                        "display_name": "Mock Operator",
                        "role": "OPERATOR",
                        "is_active": True,
                    },
                },
            )

        if path.endswith("/api/v1/lanes/active") or path.endswith("/api/v1/lanes/"):
            if method == "GET":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": in_lane_id,
                            "name": "MOCK_LANE_IN",
                            "direction": "IN",
                            "is_active": True,
                        },
                        {
                            "id": out_lane_id,
                            "name": "MOCK_LANE_OUT",
                            "direction": "OUT",
                            "is_active": True,
                        },
                    ],
                )
            if method == "POST":
                body = json.loads(request.content.decode("utf-8"))
                return httpx.Response(
                    201,
                    json={
                        "id": str(uuid4()),
                        "name": body.get("name", "MOCK_LANE"),
                        "direction": body.get("direction", "IN"),
                        "is_active": True,
                        "video_source": body.get("video_source", "mock"),
                    },
                )

        if path.endswith("/api/v1/parking/check-in") and method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            session_id = str(uuid4())
            plate = body.get("license_plate", "30A12345")
            mock_sessions[session_id] = {
                "id": session_id,
                "license_plate": plate,
                "status": "PARKED",
                "check_in_time": datetime.now(UTC).isoformat(),
            }
            return httpx.Response(
                201,
                json={
                    "transaction": {
                        "id": session_id,
                        "license_plate": plate,
                        "status": "PARKED",
                        "vehicle_type": body.get("vehicle_type", "CAR"),
                        "check_in_time": datetime.now(UTC).isoformat(),
                    },
                    "message": "Check-in successful",
                },
            )

        if path.endswith("/api/v1/parking/check-out/preview") and method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            session_id = body.get("session_id") or list(mock_sessions.keys())[-1]
            plate = body.get("license_plate", "30A12345")
            return httpx.Response(
                200,
                json={
                    "session_id": session_id,
                    "license_plate": plate,
                    "vehicle_type_in": "CAR",
                    "vehicle_type_out": "CAR",
                    "vehicle_type_mismatch": False,
                    "duration_minutes": 35,
                    "fee": 15000.0,
                    "status": "PARKED",
                    "message": "Preview calculation complete",
                },
            )

        if path.endswith("/api/v1/parking/check-out") and method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            session_id = body.get("session_id") or str(uuid4())
            plate = body.get("license_plate", "30A12345")
            if session_id in mock_sessions:
                mock_sessions[session_id]["status"] = "COMPLETED"
            return httpx.Response(
                200,
                json={
                    "transaction": {
                        "id": session_id,
                        "license_plate": plate,
                        "status": "COMPLETED",
                    },
                    "fee": 15000.0,
                    "status": "COMPLETED",
                    "barrier_opened": True,
                    "vehicle_type_mismatch": False,
                    "message": "Cash checkout complete. Barrier opened.",
                },
            )

        return httpx.Response(404, json={"detail": f"Mock route not found: {method} {path}"})

    return httpx.MockTransport(handler)


class StressTestRunner:
    """Orchestrates peak-hour concurrent parking cash checkout stress tests."""

    def __init__(
        self,
        base_url: str,
        concurrency: int,
        total_cycles: int,
        username: str | None = None,
        password: str | None = None,
        in_lane_id: str | None = None,
        out_lane_id: str | None = None,
        timeout: float = 30.0,
        mock_mode: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.concurrency = concurrency
        self.total_cycles = total_cycles
        self.username = username
        self.password = password
        self.in_lane_id = in_lane_id
        self.out_lane_id = out_lane_id
        self.timeout = timeout
        self.mock_mode = mock_mode

        transport = create_mock_transport() if mock_mode else None
        limits = httpx.Limits(
            max_connections=concurrency * 2,
            max_keepalive_connections=concurrency,
        )
        self.client = httpx.Client(
            base_url=self.base_url,
            transport=transport,
            limits=limits,
            timeout=self.timeout,
            follow_redirects=True,
        )

        self.token: str | None = None
        self.auth_headers: dict[str, str] = {}
        self.logged_in_user: str = ""

    def close(self) -> None:
        self.client.close()

    def authenticate(self) -> str:
        """Authenticate as OPERATOR or SYSTEM_ADMIN to acquire a Bearer JWT."""
        env = load_env_defaults()
        user_candidates = []

        if self.username and self.password:
            user_candidates.append((self.username, self.password))
        else:
            if env.get("SEED_OPERATOR_USERNAME") and env.get("SEED_OPERATOR_PASSWORD"):
                user_candidates.append(
                    (env["SEED_OPERATOR_USERNAME"], env["SEED_OPERATOR_PASSWORD"])
                )
            if env.get("SEED_ADMIN_USERNAME") and env.get("SEED_ADMIN_PASSWORD"):
                user_candidates.append((env["SEED_ADMIN_USERNAME"], env["SEED_ADMIN_PASSWORD"]))
            user_candidates.extend(
                [
                    ("operator", "change-me-operator"),
                    ("admin", "change-me-admin"),
                ]
            )

        last_error = "No credentials available"
        for username, password in user_candidates:
            try:
                res = self.client.post(
                    "/api/v1/auth/login",
                    json={"username": username, "password": password},
                )
                if res.status_code == 200:
                    data = res.json()
                    self.token = data["access_token"]
                    self.auth_headers = {"Authorization": f"Bearer {self.token}"}
                    self.logged_in_user = username
                    return self.token
                last_error = f"Status {res.status_code}: {res.text[:120]}"
            except httpx.RequestError as exc:
                last_error = f"Connection error to {self.base_url}: {exc}"

        error_summary = f"Authentication failed for candidate users. Last error: {last_error}"
        raise RuntimeError(error_summary)

    def resolve_lanes(self) -> tuple[str, str]:
        """Locate active IN and OUT lanes, or auto-provision them if authorized."""
        if self.in_lane_id and self.out_lane_id:
            return self.in_lane_id, self.out_lane_id

        in_id = self.in_lane_id
        out_id = self.out_lane_id

        try:
            res = self.client.get("/api/v1/lanes/active", headers=self.auth_headers)
            if res.status_code != 200:
                res = self.client.get("/api/v1/lanes/", headers=self.auth_headers)

            if res.status_code == 200:
                lanes = res.json()
                for lane in lanes:
                    direction = lane.get("direction")
                    if direction == "IN" and not in_id:
                        in_id = str(lane["id"])
                    elif direction == "OUT" and not out_id:
                        out_id = str(lane["id"])
        except httpx.RequestError as exc:
            raise RuntimeError(f"Failed to query lanes: {exc}") from exc

        # If missing, attempt creation
        if not in_id:
            create_in = self.client.post(
                "/api/v1/lanes/",
                headers=self.auth_headers,
                json={
                    "name": f"STRESS_IN_{uuid4().hex[:4]}",
                    "direction": "IN",
                    "video_source": "synthetic-stress-in",
                    "is_active": True,
                },
            )
            if create_in.status_code in (200, 201):
                in_id = str(create_in.json()["id"])

        if not out_id:
            create_out = self.client.post(
                "/api/v1/lanes/",
                headers=self.auth_headers,
                json={
                    "name": f"STRESS_OUT_{uuid4().hex[:4]}",
                    "direction": "OUT",
                    "video_source": "synthetic-stress-out",
                    "is_active": True,
                },
            )
            if create_out.status_code in (200, 201):
                out_id = str(create_out.json()["id"])

        if not in_id or not out_id:
            raise RuntimeError(
                f"Could not resolve active lanes (in={in_id}, out={out_id}). "
                "Specify explicitly with --lane-in and --lane-out."
            )

        self.in_lane_id = in_id
        self.out_lane_id = out_id
        return in_id, out_id

    def _execute_single_request(
        self,
        step_name: str,
        method: str,
        url: str,
        json_body: dict[str, Any],
        headers: dict[str, str],
        expected_status: tuple[int, ...] = (200, 201),
    ) -> tuple[RequestRecord, dict[str, Any] | None]:
        started = time.perf_counter()
        try:
            res = self.client.request(
                method=method,
                url=url,
                json=json_body,
                headers=headers,
            )
            duration_ms = (time.perf_counter() - started) * 1000.0
            is_success = res.status_code in expected_status
            error_msg = None if is_success else f"HTTP {res.status_code}: {res.text[:120]}"
            data = None
            if is_success:
                try:
                    data = res.json()
                except Exception:
                    data = {}

            record = RequestRecord(
                step_name=step_name,
                status_code=res.status_code,
                duration_ms=duration_ms,
                success=is_success,
                error_message=error_msg,
            )
            return record, data

        except Exception as exc:
            duration_ms = (time.perf_counter() - started) * 1000.0
            record = RequestRecord(
                step_name=step_name,
                status_code=0,
                duration_ms=duration_ms,
                success=False,
                error_message=str(exc),
            )
            return record, None

    def execute_lifecycle_cycle(self, cycle_index: int) -> CycleRecord:
        """Execute one complete cycle: Check-In -> Cash Preview -> Cash Check-Out."""
        plate = f"51A{random.randint(100, 999)}{uuid4().hex[:3].upper()}"
        cycle_start = time.perf_counter()
        requests: list[RequestRecord] = []

        # 1. Step: Check-In
        checkin_headers = {
            **self.auth_headers,
            "Idempotency-Key": f"stress-in-{cycle_index}-{uuid4()}",
        }
        checkin_body = {
            "lane_id": self.in_lane_id,
            "license_plate": plate,
            "vehicle_type": "CAR",
        }
        rec_checkin, checkin_data = self._execute_single_request(
            step_name=STEP_CHECKIN,
            method="POST",
            url="/api/v1/parking/check-in",
            json_body=checkin_body,
            headers=checkin_headers,
            expected_status=(200, 201),
        )
        requests.append(rec_checkin)

        if not rec_checkin.success or not checkin_data:
            total_duration = (time.perf_counter() - cycle_start) * 1000.0
            return CycleRecord(
                cycle_index=cycle_index,
                license_plate=plate,
                success=False,
                total_duration_ms=total_duration,
                requests=requests,
                error_step=STEP_CHECKIN,
            )

        session_id = checkin_data.get("transaction", {}).get("id")

        # 2. Step: Preview Calculation
        preview_body = {
            "session_id": session_id,
            "exit_lane_id": self.out_lane_id,
            "license_plate": plate,
            "vehicle_type_out": "CAR",
        }
        rec_preview, preview_data = self._execute_single_request(
            step_name=STEP_PREVIEW,
            method="POST",
            url="/api/v1/parking/check-out/preview",
            json_body=preview_body,
            headers=self.auth_headers,
            expected_status=(200,),
        )
        requests.append(rec_preview)

        if not rec_preview.success:
            total_duration = (time.perf_counter() - cycle_start) * 1000.0
            return CycleRecord(
                cycle_index=cycle_index,
                license_plate=plate,
                success=False,
                total_duration_ms=total_duration,
                requests=requests,
                error_step=STEP_PREVIEW,
            )

        # 3. Step: Cash Checkout (payment_method='CASH')
        checkout_headers = {
            **self.auth_headers,
            "Idempotency-Key": f"stress-out-{cycle_index}-{uuid4()}",
        }
        checkout_body = {
            "session_id": session_id,
            "exit_lane_id": self.out_lane_id,
            "license_plate": plate,
            "vehicle_type_out": "CAR",
            "payment_method": "CASH",
        }
        rec_checkout, _ = self._execute_single_request(
            step_name=STEP_CHECKOUT,
            method="POST",
            url="/api/v1/parking/check-out",
            json_body=checkout_body,
            headers=checkout_headers,
            expected_status=(200,),
        )
        requests.append(rec_checkout)

        total_duration = (time.perf_counter() - cycle_start) * 1000.0
        cycle_success = rec_checkout.success
        error_step = None if cycle_success else STEP_CHECKOUT

        return CycleRecord(
            cycle_index=cycle_index,
            license_plate=plate,
            success=cycle_success,
            total_duration_ms=total_duration,
            requests=requests,
            error_step=error_step,
        )

    def run_benchmark(self) -> dict[str, Any]:
        """Run concurrent stress test and collect comprehensive statistics."""
        self.authenticate()
        self.resolve_lanes()

        print(f"\n[STRESS TEST] Target Host : {self.base_url}")
        print(f"[STRESS TEST] Mode        : {'MOCK (In-memory)' if self.mock_mode else 'LIVE'}")
        print(f"[STRESS TEST] Operator    : {self.logged_in_user}")
        print(f"[STRESS TEST] Lane IN     : {self.in_lane_id}")
        print(f"[STRESS TEST] Lane OUT    : {self.out_lane_id}")
        print(f"[STRESS TEST] Concurrency : {self.concurrency} workers")
        print(f"[STRESS TEST] Cycles      : {self.total_cycles} lifecycles (3 reqs/cycle)")
        print(f"[STRESS TEST] Total Reqs  : ~{self.total_cycles * 3} requests")
        print("\nStarting execution...")

        cycles: list[CycleRecord] = []
        wall_clock_start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [
                executor.submit(self.execute_lifecycle_cycle, i + 1)
                for i in range(self.total_cycles)
            ]
            completed_count = 0
            for future in as_completed(futures):
                record = future.result()
                cycles.append(record)
                completed_count += 1
                if completed_count % max(1, self.total_cycles // 5) == 0 or (
                    completed_count == self.total_cycles
                ):
                    print(
                        f"  -> Progress: {completed_count}/{self.total_cycles} cycles completed "
                        f"({(completed_count / self.total_cycles) * 100:.0f}%)"
                    )

        wall_clock_duration = time.perf_counter() - wall_clock_start

        return self._aggregate_metrics(cycles, wall_clock_duration)

    def _aggregate_metrics(
        self, cycles: list[CycleRecord], wall_clock_duration: float
    ) -> dict[str, Any]:
        """Compute all benchmark metrics, percentiles, throughput and breakdowns."""
        all_requests: list[RequestRecord] = []
        for cycle in cycles:
            all_requests.extend(cycle.requests)

        total_requests = len(all_requests)
        successful_requests = sum(1 for r in all_requests if r.success)
        failed_requests = total_requests - successful_requests

        successful_cycles = sum(1 for c in cycles if c.success)
        failed_cycles = len(cycles) - successful_cycles

        req_throughput = (
            total_requests / wall_clock_duration if wall_clock_duration > 0 else 0.0
        )
        cycle_throughput = (
            len(cycles) / wall_clock_duration if wall_clock_duration > 0 else 0.0
        )

        # All request latencies
        all_latencies = sorted(r.duration_ms for r in all_requests)
        mean_latency = (
            sum(all_latencies) / len(all_latencies) if all_latencies else 0.0
        )
        min_latency = all_latencies[0] if all_latencies else 0.0
        max_latency = all_latencies[-1] if all_latencies else 0.0

        p50 = compute_percentile(all_latencies, 50.0)
        p90 = compute_percentile(all_latencies, 90.0)
        p95 = compute_percentile(all_latencies, 95.0)
        p99 = compute_percentile(all_latencies, 99.0)

        # Step-level breakdown
        steps_info: dict[str, dict[str, Any]] = {}
        for step in [STEP_CHECKIN, STEP_PREVIEW, STEP_CHECKOUT]:
            step_reqs = [r for r in all_requests if r.step_name == step]
            step_total = len(step_reqs)
            step_success = sum(1 for r in step_reqs if r.success)
            step_failed = step_total - step_success
            step_lats = sorted(r.duration_ms for r in step_reqs)
            steps_info[step] = {
                "total": step_total,
                "success": step_success,
                "failed": step_failed,
                "avg_ms": sum(step_lats) / len(step_lats) if step_lats else 0.0,
                "min_ms": step_lats[0] if step_lats else 0.0,
                "max_ms": step_lats[-1] if step_lats else 0.0,
                "p50_ms": compute_percentile(step_lats, 50.0),
                "p90_ms": compute_percentile(step_lats, 90.0),
                "p95_ms": compute_percentile(step_lats, 95.0),
                "p99_ms": compute_percentile(step_lats, 99.0),
            }

        # Failure details
        errors: dict[str, int] = {}
        for r in all_requests:
            if not r.success and r.error_message:
                errors[r.error_message] = errors.get(r.error_message, 0) + 1

        return {
            "host": self.base_url,
            "concurrency": self.concurrency,
            "total_cycles": self.total_cycles,
            "wall_clock_duration_seconds": round(wall_clock_duration, 3),
            "requests": {
                "total": total_requests,
                "successful": successful_requests,
                "failed": failed_requests,
                "success_rate_pct": (
                    round((successful_requests / total_requests) * 100, 2)
                    if total_requests > 0
                    else 0.0
                ),
                "throughput_req_per_sec": round(req_throughput, 2),
            },
            "cycles": {
                "total": len(cycles),
                "successful": successful_cycles,
                "failed": failed_cycles,
                "success_rate_pct": (
                    round((successful_cycles / len(cycles)) * 100, 2)
                    if cycles
                    else 0.0
                ),
                "throughput_cycle_per_sec": round(cycle_throughput, 2),
            },
            "latency_ms": {
                "avg": round(mean_latency, 2),
                "min": round(min_latency, 2),
                "max": round(max_latency, 2),
                "p50": round(p50, 2),
                "p90": round(p90, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            },
            "step_breakdown": steps_info,
            "errors": errors,
        }


def print_ascii_table(title: str, rows: list[tuple[str, str]], width: int = 76) -> None:
    """Print a clean ASCII two-column key-value table."""
    col1_w = 46
    col2_w = width - col1_w - 7

    border = "+" + "-" * (col1_w + 2) + "+" + "-" * (col2_w + 2) + "+"
    sep = "+" + "-" * (width - 2) + "+"

    print(sep)
    print(f"| {title.center(width - 4)} |")
    print(border)
    for key, val in rows:
        print(f"| {key:<{col1_w}} | {val:>{col2_w}} |")
    print(border)


def print_step_breakdown_table(steps: dict[str, dict[str, Any]]) -> None:
    """Print step-by-step performance breakdown table."""
    headers = ["Step", "Total", "Success", "Failed", "Avg(ms)", "p50(ms)", "p95(ms)", "p99(ms)"]
    widths = [19, 7, 9, 8, 9, 9, 9, 9]

    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    header_row = (
        "| "
        + " | ".join(
            f"{h:<{widths[i]}}" if i == 0 else f"{h:>{widths[i]}}"
            for i, h in enumerate(headers)
        )
        + " |"
    )

    print("\nSTEP-BY-STEP LATENCY & THROUGHPUT BREAKDOWN:")
    print(border)
    print(header_row)
    print(border)

    for step_name, data in steps.items():
        row_vals = [
            f"{step_name:<{widths[0]}}",
            f"{data['total']:>{widths[1]}}",
            f"{data['success']:>{widths[2]}}",
            f"{data['failed']:>{widths[3]}}",
            f"{data['avg_ms']:>{widths[4]}.2f}",
            f"{data['p50_ms']:>{widths[5]}.2f}",
            f"{data['p95_ms']:>{widths[6]}.2f}",
            f"{data['p99_ms']:>{widths[7]}.2f}",
        ]
        print("| " + " | ".join(row_vals) + " |")

    print(border)


def print_report(results: dict[str, Any]) -> None:
    """Print beautiful terminal report summarizing stress test results."""
    reqs = results["requests"]
    cycles = results["cycles"]
    lats = results["latency_ms"]
    duration = results["wall_clock_duration_seconds"]

    summary_rows = [
        ("Target Host", str(results["host"])),
        ("Concurrency (Workers)", str(results["concurrency"])),
        ("Planned Cycles", str(results["total_cycles"])),
        ("Total Requests Dispatched", str(reqs["total"])),
        ("Successful Requests (HTTP 200/201)", str(reqs["successful"])),
        ("Failed Requests", str(reqs["failed"])),
        ("Request Success Rate", f"{reqs['success_rate_pct']:.2f} %"),
        (
            "Completed Cycles (CheckIn->Preview->Out)",
            f"{cycles['successful']} / {cycles['total']} ({cycles['success_rate_pct']:.2f} %)",
        ),
        ("Total Test Duration (Wall-clock)", f"{duration:.3f} s"),
        ("Request Throughput", f"{reqs['throughput_req_per_sec']:.2f} req/s"),
        ("Cycle Throughput", f"{cycles['throughput_cycle_per_sec']:.2f} cycles/s"),
    ]

    latency_rows = [
        ("Average (Mean) Latency", f"{lats['avg']:.2f} ms"),
        ("Minimum Latency", f"{lats['min']:.2f} ms"),
        ("Median (p50) Latency", f"{lats['p50']:.2f} ms"),
        ("90th Percentile (p90) Latency", f"{lats['p90']:.2f} ms"),
        ("95th Percentile (p95) Latency", f"{lats['p95']:.2f} ms"),
        ("99th Percentile (p99) Latency", f"{lats['p99']:.2f} ms"),
        ("Maximum Latency", f"{lats['max']:.2f} ms"),
    ]

    print("\n" + "=" * 76)
    print("   VISIONPARK CASH CHECKOUT STRESS & PERFORMANCE TEST REPORT   ".center(76))
    print("=" * 76)

    print_ascii_table("OVERALL BENCHMARK METRICS", summary_rows)
    print_ascii_table("OVERALL REQUEST LATENCY DISTRIBUTION", latency_rows)
    print_step_breakdown_table(results["step_breakdown"])

    if results["errors"]:
        print("\nTOP ERROR CAUSES:")
        for err, count in results["errors"].items():
            print(f"  [{count}x] {err}")
    print("=" * 76 + "\n")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="VisionPark Cash Checkout Peak-Hour Stress & Performance Test Tool"
    )
    parser.add_argument(
        "--host",
        default="http://127.0.0.1:8000",
        help="Target backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent worker threads (default: 10)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=50,
        help="Total number of complete parking cycles to execute (default: 50)",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Operator or Admin username (default: reads from .env or defaults)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Operator or Admin password (default: reads from .env or defaults)",
    )
    parser.add_argument(
        "--lane-in",
        default=None,
        help="Specific UUID of IN lane (default: auto-detected)",
    )
    parser.add_argument(
        "--lane-out",
        default=None,
        help="Specific UUID of OUT lane (default: auto-detected)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Execute against an internal high-fidelity mock transport for dry-run/testing",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Path to write JSON benchmark report for CI/monitoring",
    )
    return parser.parse_args()


def main() -> int:
    # Ensure stdout handles UTF-8 on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_arguments()
    runner = StressTestRunner(
        base_url=args.host,
        concurrency=args.concurrency,
        total_cycles=args.requests,
        username=args.username,
        password=args.password,
        in_lane_id=args.lane_in,
        out_lane_id=args.lane_out,
        timeout=args.timeout,
        mock_mode=args.mock,
    )

    try:
        results = runner.run_benchmark()
        print_report(results)

        if args.json_output:
            out_path = Path(args.json_output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"[REPORT] Saved JSON metrics to: {out_path.resolve()}")

        # Exit code: non-zero if there were failed requests
        failed = results["requests"]["failed"]
        return 1 if failed > 0 else 0

    except Exception as exc:
        print(f"\n[ERROR] Stress test failed with exception: {exc}", file=sys.stderr)
        return 2
    finally:
        runner.close()


if __name__ == "__main__":
    sys.exit(main())
