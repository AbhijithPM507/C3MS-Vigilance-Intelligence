import hashlib
from datetime import datetime
from typing import Dict, List


class BlockchainVerifier:
    """Encapsulates hash generation and chain verification logic."""

    def generate_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def create_block(
        self,
        complaint_id: str,
        redacted_text: str,
        previous_hash: str,
    ) -> Dict:
        """Creates a new integrity block."""

        timestamp = datetime.utcnow().isoformat()

        hash_input = (
            complaint_id +
            redacted_text +
            previous_hash +
            timestamp
        )

        data_hash = self.generate_hash(hash_input)

        return {
            "complaint_id": complaint_id,
            "redacted_text": redacted_text,
            "data_hash": data_hash,
            "previous_hash": previous_hash,
            "timestamp": timestamp,
        }

    def verify_chain(self, blocks: List[Dict]) -> bool:
        """Verifies entire chain integrity. Expects ordered blocks (oldest → newest)."""

        if not blocks:
            return True

        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i - 1]

            # Check previous hash linkage
            if current["previous_hash"] != previous["data_hash"]:
                return False

            # Recalculate current hash
            recalculated = self.generate_hash(
                current["complaint_id"] +
                current["redacted_text"] +
                previous["data_hash"] +
                current["timestamp"]
            )

            if recalculated != current["data_hash"]:
                return False

        return True


# Default instance to preserve module-level function API
_default_verifier = BlockchainVerifier()


def generate_hash(data: str) -> str:
    return _default_verifier.generate_hash(data)


def create_block(complaint_id: str, redacted_text: str, previous_hash: str) -> Dict:
    return _default_verifier.create_block(
        complaint_id=complaint_id,
        redacted_text=redacted_text,
        previous_hash=previous_hash,
    )


def verify_chain(blocks: List[Dict]) -> bool:
    return _default_verifier.verify_chain(blocks)