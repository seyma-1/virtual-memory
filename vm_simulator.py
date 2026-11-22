#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

POLICIES = ("fifo", "lru", "opt", "clock")
MAX_FRAMES = 64
MAX_REFERENCES = 256
MAX_PAGE = 999
M_US = 1
TIN_US = 10_000
TOUT_US = 10_000

WORKLOADS = {
    "A": "7:R 0:W 1:R 2:W 0:R 3:R 0:W 4:R 2:R 3:W 0:R 3:R 2:W 1:R 2:R 0:R 1:W 7:R 0:R 1:R",
    "B": "1:R 2:R 3:R 4:R 1:R 2:R 5:R 1:R 2:R 3:R 4:R 5:R",
}

@dataclass
class Frame:
    page: Optional[int] = None
    dirty: bool = False
    loaded_at: int = -1
    last_used: int = -1
    ref_bit: int = 0

@dataclass(frozen=True)
class Reference:
    page: int
    op: str

def parse_references(raw: str) -> list[Reference]:
    if not raw or not raw.strip():
        raise ValueError("Reference sequence must be nonempty.")
    tokens = raw.split()
    if len(tokens) > MAX_REFERENCES:
        raise ValueError(f"At most {MAX_REFERENCES} references are allowed; received {len(tokens)}.")
    refs: list[Reference] = []
    for position, token in enumerate(tokens, start=1):
        match = re.fullmatch(r"(\d{1,3}):([RrWw])", token)
        if not match:
            raise ValueError(
                f"Invalid reference #{position} {token!r}. Expected PAGE:R or PAGE:W, "
                f"where PAGE is 0–{MAX_PAGE}."
            )
        page = int(match.group(1))
        if not 0 <= page <= MAX_PAGE:
            raise ValueError(f"Page number in reference #{position} must be 0–{MAX_PAGE}.")
        refs.append(Reference(page, match.group(2).upper()))
    return refs

def validate_capacity(capacity: int) -> None:
    if not 1 <= capacity <= MAX_FRAMES:
        raise ValueError(f"Frame capacity must be between 1 and {MAX_FRAMES}.")

def next_use(refs: list[Reference], page: int, current_index: int) -> float:
    for future_index in range(current_index + 1, len(refs)):
        if refs[future_index].page == page:
            return future_index
    return math.inf

def frame_text(frame: Frame) -> str:
    if frame.page is None:
        return "-"
    return f"{frame.page}/{'D' if frame.dirty else 'C'}"

def simulate(refs: list[Reference], capacity: int, policy: str) -> tuple[list[dict], dict]:
    validate_capacity(capacity)
    if policy not in POLICIES:
        raise ValueError(f"Unknown policy {policy!r}; choose one of {', '.join(POLICIES)}.")
    if not refs:
        raise ValueError("Reference sequence must be nonempty.")
    if len(refs) > MAX_REFERENCES:
        raise ValueError(f"At most {MAX_REFERENCES} references are allowed.")

    frames = [Frame() for _ in range(capacity)]
    hand = 0
    hits = faults = evictions = writebacks = 0
    trace: list[dict] = []

    for step, ref in enumerate(refs, start=1):
        index = next((i for i, frame in enumerate(frames) if frame.page == ref.page), None)
        outcome = "HIT" if index is not None else "FAULT"
        victim = ""
        writeback = 0

        if index is not None:
            hits += 1
            frame = frames[index]
            frame.last_used = step
            if ref.op == "W":
                frame.dirty = True
            if policy == "clock":
                frame.ref_bit = 1
        else:
            faults += 1
            empty = [i for i, frame in enumerate(frames) if frame.page is None]
            if policy == "clock":
                # Clock follows the hand even when empty frames exist.
                # It stops at the first empty frame or a frame with ref_bit 0.
                while frames[hand].page is not None and frames[hand].ref_bit == 1:
                    frames[hand].ref_bit = 0
                    hand = (hand + 1) % capacity
                target = hand
            elif empty:
                # FIFO, LRU and OPT use the lowest-index empty frame.
                target = min(empty)
            elif policy == "fifo":
                target = min(range(capacity), key=lambda i: (frames[i].loaded_at, i))
            elif policy == "lru":
                target = min(range(capacity), key=lambda i: (frames[i].last_used, i))
            else:  # OPT
                # Farthest next use; never-used-again is infinity.
                # Ties are resolved by the lowest frame index.
                target = max(
                    range(capacity),
                    key=lambda i: (next_use(refs, frames[i].page, step - 1), -i)
                )

            old = frames[target]
            if old.page is not None:
                victim = str(old.page)
                evictions += 1
                if old.dirty:
                    writeback = 1
                    writebacks += 1

            frames[target] = Frame(
                page=ref.page,
                dirty=(ref.op == "W"),
                loaded_at=step,
                last_used=step,
                ref_bit=(1 if policy == "clock" else 0),
            )
            if policy == "clock":
                hand = (target + 1) % capacity

        # Invariants after every reference.
        resident_pages = [f.page for f in frames if f.page is not None]
        assert len(resident_pages) <= capacity
        assert len(resident_pages) == len(set(resident_pages))

        row = {
            "step": step,
            "reference": f"{ref.page}:{ref.op}",
            "page": ref.page,
            "operation": ref.op,
            "result": outcome,
            "victim": victim or "none",
            "dirty_writeback": "yes" if writeback else "no",
        }
        for i, frame in enumerate(frames):
            row[f"frame_{i}"] = frame_text(frame)
        if policy == "clock":
            for i, frame in enumerate(frames):
                row[f"ref_{i}"] = frame.ref_bit
            row["next_hand"] = hand
        trace.append(row)

    final_dirty_pages = sorted(f.page for f in frames if f.page is not None and f.dirty)
    total_refs = len(refs)
    total_time = total_refs * M_US + faults * TIN_US + writebacks * TOUT_US
    summary = {
        "policy": policy.upper(),
        "frames": capacity,
        "references": total_refs,
        "hits": hits,
        "faults": faults,
        "evictions": evictions,
        "dirty_writebacks": writebacks,
        "final_resident_dirty_pages": ";".join(map(str, final_dirty_pages)) or "none",
        "final_resident_dirty_count": len(final_dirty_pages),
        "total_modeled_time_us": total_time,
        "average_modeled_time_us_per_reference": f"{total_time / total_refs:.2f}",
    }

    assert hits + faults == total_refs
    assert writebacks <= evictions <= faults
    assert len([f for f in frames if f.page is not None]) <= capacity
    return trace, summary

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def run_named(name: str, capacity: int, policy: str, outdir: Path) -> dict:
    refs = parse_references(WORKLOADS[name])
    trace, summary = simulate(refs, capacity, policy)
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / f"workload_{name.lower()}_{capacity}_{policy}.csv", trace)
    return summary

def main() -> int:
    parser = argparse.ArgumentParser(description="FIFO/LRU/OPT/Clock virtual-memory simulator")
    parser.add_argument("--policy", choices=POLICIES, help="replacement policy for a custom sequence")
    parser.add_argument("--frames", type=int, help="number of frames (1–64)")
    parser.add_argument("--refs", help='custom references, e.g. "7:R 0:W 1:R"')
    parser.add_argument("--workload", choices=("A", "B"), help="run a supplied workload")
    parser.add_argument("--all", action="store_true", help="run all six required assignment configurations")
    parser.add_argument("--outdir", default="traces", help="directory for CSV traces (default: traces)")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    summaries: list[dict] = []
    try:
        if args.all:
            configurations = [
                ("A", 3, "fifo"), ("A", 3, "lru"), ("A", 3, "opt"), ("A", 3, "clock"),
                ("B", 3, "fifo"), ("B", 4, "fifo"),
            ]
            for name, cap, policy in configurations:
                summaries.append(run_named(name, cap, policy, outdir))
        elif args.refs:
            if args.policy is None or args.frames is None:
                parser.error("--refs requires both --policy and --frames.")
            refs = parse_references(args.refs)
            trace, summary = simulate(refs, args.frames, args.policy)
            outdir.mkdir(parents=True, exist_ok=True)
            write_csv(outdir / f"custom_{args.frames}_{args.policy}.csv", trace)
            summaries.append(summary)
        elif args.workload:
            if args.policy is None or args.frames is None:
                parser.error("--workload requires both --policy and --frames.")
            summaries.append(run_named(args.workload, args.frames, args.policy, outdir))
        else:
            parser.error("Choose --all, or provide --refs with --policy/--frames, or --workload with --policy/--frames.")
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    if summaries:
        summary_path = outdir / "summary.csv"
        write_csv(summary_path, summaries)
        print("policy,frames,references,hits,faults,evictions,dirty_writebacks,final_resident_dirty_pages,total_modeled_time_us,average_modeled_time_us_per_reference")
        for s in summaries:
            print(",".join(str(s[k]) for k in (
                "policy", "frames", "references", "hits", "faults", "evictions",
                "dirty_writebacks", "final_resident_dirty_pages",
                "total_modeled_time_us", "average_modeled_time_us_per_reference"
            )))
        print(f"\nCSV traces and summary written to: {outdir.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
