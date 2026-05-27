import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Union

from .web3_anchor import anchor_hash_onchain

logger = logging.getLogger(__name__)

DEFAULT_ANCHOR_FILE = Path("data_layer/blockchain/anchor_log.json")

USE_ONCHAIN = True


class AnchorManager:
    """Manages external anchoring of chain hashes — writes to on-chain
    contract by default, with local JSON fallback."""

    def __init__(self, anchor_file: Union[str, Path] = DEFAULT_ANCHOR_FILE):
        self.anchor_file = Path(anchor_file)

    def create_anchor(self, latest_hash: str) -> None:
        if USE_ONCHAIN:
            ok = anchor_hash_onchain(latest_hash)
            if ok:
                return
            logger.warning("On-chain anchor failed, falling back to local log")

        anchor_record = {
            "anchor_time": datetime.utcnow().isoformat(),
            "latest_hash": latest_hash,
        }

        self.anchor_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.anchor_file, "a", encoding="utf-8") as f:
            json.dump(anchor_record, f)
            f.write("\n")


_default_anchor_manager = AnchorManager()


def create_anchor(latest_hash: str) -> None:
    return _default_anchor_manager.create_anchor(latest_hash)