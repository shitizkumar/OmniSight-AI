import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

STAGES = [
    ("Checkout capture", "browser_agent.checkout"),
    ("UI inspection", "vision_engine.inspect_ui"),
    ("Repair recommendations", "repair_engine.recommend"),
]


def run_stage(name: str, module: str) -> None:
    print(f"\n{'=' * 12} {name} {'=' * 12}", flush=True)

    result = subprocess.run(
        [sys.executable, "-m", module],
        cwd=ROOT_DIR,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{name} failed with exit code {result.returncode}."
        )

    print(f"{name}: completed", flush=True)


def main() -> int:
    try:
        for name, module in STAGES:
            run_stage(name, module)
    except RuntimeError as exc:
        print(f"\nPipeline stopped: {exc}", file=sys.stderr)
        return 1

    print("\nPipeline completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())