"""Regenerate the committed fixture CSV and golden signal files.

Run deliberately, review the diff, and re-run the Pine parity harness (M4)
before shipping any detector change that alters these files.

    uv run python tests/generate_golden.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from smc_research.detectors import ALL_DETECTORS, run  # noqa: E402
from tests.conftest import FIXTURE_CSV, GOLDEN_DIR, make_fixture  # noqa: E402
from tests.test_detectors import signals_to_jsonable  # noqa: E402


def main() -> None:
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    df = make_fixture()
    df.to_csv(FIXTURE_CSV)
    print(f"wrote {FIXTURE_CSV} ({len(df)} bars)")
    for name, cls in sorted(ALL_DETECTORS.items()):
        signals = signals_to_jsonable(run(cls(), df))
        path = GOLDEN_DIR / f"{name}.json"
        path.write_text(json.dumps(signals, indent=1) + "\n")
        print(f"wrote {path} ({len(signals)} signals)")


if __name__ == "__main__":
    main()
