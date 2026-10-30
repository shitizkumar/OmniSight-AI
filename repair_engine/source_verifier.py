
import subprocess

from repair_engine.self_heal import (
    PROJECT_ROOT,
    apply_source_patch,
    rollback_source_patch,
)


def verify_source_patch(css_patch: str) -> dict:
    # Apply the patch before entering the build/rollback section.
    patch_result = apply_source_patch(css_patch)

    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=PROJECT_ROOT / "mock-store",
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            rollback_source_patch()

            return {
                "status": "rolled_back",
                "verification_status": "build_failed",
                "source_code_modified": False,
                "error": result.stderr[-2000:],
            }

        return {
            "status": "verified",
            "verification_status": "build_passed",
            "source_code_modified": True,
            "source_file": patch_result["source_file"],
        }

    except Exception:
        rollback_source_patch()
        raise

