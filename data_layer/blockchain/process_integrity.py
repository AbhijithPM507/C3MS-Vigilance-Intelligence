from typing import Dict
from . import hash_chain
from . import anchor


class IntegrityProcessor:
    """Orchestrates creation of integrity blocks and anchoring policy."""

    def __init__(self, anchor_every: int = 5):
        self.anchor_every = anchor_every

    def process_integrity(
        self,
        complaint_id: str,
        redacted_text: str,
        previous_hash: str,
        total_blocks: int,
    ) -> Dict:
        """Main integrity function. Called by backend after redaction."""

        block = hash_chain.create_block(
            complaint_id=complaint_id,
            redacted_text=redacted_text,
            previous_hash=previous_hash,
        )

        # Anchor every `anchor_every` blocks
        if (total_blocks + 1) % self.anchor_every == 0:
            anchor.create_anchor(block["data_hash"])

        return block


# Default instance to preserve module-level API
_default_processor = IntegrityProcessor()


def process_integrity(
    complaint_id: str,
    redacted_text: str,
    previous_hash: str,
    total_blocks: int,
) -> Dict:
    return _default_processor.process_integrity(
        complaint_id=complaint_id,
        redacted_text=redacted_text,
        previous_hash=previous_hash,
        total_blocks=total_blocks,
    )