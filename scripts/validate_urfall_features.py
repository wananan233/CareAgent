#!/usr/bin/env python3
"""校验 UR Fall 官方特征 CSV，避免序列泄漏。"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

def read_rows(path: Path) -> list[tuple[str, int, int]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for line_no, row in enumerate(csv.reader(handle), 1):
            if len(row) != 11:
                raise ValueError(f"{path}:{line_no}: 期望 11 列，实际 {len(row)}")
            sequence, frame, label = row[:3]
            if not sequence.startswith(("fall-", "adl-")) or int(frame) <= 0 or int(label) not in {-1, 0, 1}:
                raise ValueError(f"{path}:{line_no}: 序列、帧号或标签非法")
            rows.append((sequence, int(frame), int(label)))
    return rows

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("falls", type=Path)
    parser.add_argument("adls", type=Path)
    args = parser.parse_args()
    falls, adls = read_rows(args.falls), read_rows(args.adls)
    fs, ats = {r[0] for r in falls}, {r[0] for r in adls}
    if fs & ats or not fs or not ats:
        raise ValueError("跌倒/ADL 序列为空或发生交叉，禁止继续")
    print(f"OK falls_rows={len(falls)} falls_sequences={len(fs)} adls_rows={len(adls)} adl_sequences={len(ats)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
