"""生成不含身份信息的 V0 合成 YOLO 数据集。"""
from __future__ import annotations

import argparse
import random
from pathlib import Path



def generate(root: Path, count: int, seed: int = 7) -> None:
    import cv2
    import numpy as np
    rng = random.Random(seed)
    for split, size in (("train", count), ("val", max(2, count // 4))):
        image_dir, label_dir = root / "images" / split, root / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for index in range(size):
            canvas = np.zeros((128, 128, 3), dtype=np.uint8)
            cx, cy = rng.randint(24, 104), rng.randint(24, 104)
            radius = rng.randint(10, 20)
            cv2.circle(canvas, (cx, cy), radius, (255, 255, 255), -1)
            (image_dir / f"synthetic-{index:04d}.png").write_bytes(cv2.imencode(".png", canvas)[1].tobytes())
            label_dir.joinpath(f"synthetic-{index:04d}.txt").write_text(
                f"0 {cx / 128:.6f} {cy / 128:.6f} {2 * radius / 128:.6f} {2 * radius / 128:.6f}\n",
                encoding="utf-8",
            )
    (root / "dataset.yaml").write_text(
        f"path: {root}\ntrain: images/train\nval: images/val\nnames:\n  0: synthetic_observation\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--count", type=int, default=24)
    args = parser.parse_args()
    generate(args.root, args.count)
    print(f"generated_dataset={args.root} count={args.count}")


if __name__ == "__main__":
    main()
