import json
from datetime import datetime
from pathlib import Path
from typing import Union


DEFAULT_ANCHOR_FILE = Path("data_layer/blockchain/anchor_log.json")


class AnchorManager:
    """Manages external anchoring of chain hashes to a log file."""

    def __init__(self, anchor_file: Union[str, Path] = DEFAULT_ANCHOR_FILE):
        self.anchor_file = Path(anchor_file)

    def create_anchor(self, latest_hash: str) -> None:
        """Stores latest chain hash externally to strengthen integrity."""

        anchor_record = {
            "anchor_time": datetime.utcnow().isoformat(),
            "latest_hash": latest_hash,
        }

        # Ensure parent dir exists
        self.anchor_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.anchor_file, "a", encoding="utf-8") as f:
            json.dump(anchor_record, f)
            f.write("\n")


# Default manager to preserve module-level API
_default_anchor_manager = AnchorManager()


def create_anchor(latest_hash: str) -> None:
    return _default_anchor_manager.create_anchor(latest_hash)