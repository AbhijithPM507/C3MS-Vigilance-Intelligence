import json
import hashlib
import sqlite3
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

from data_layer.config import DATABASE_URL


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured.")
    return psycopg2.connect(DATABASE_URL)


# -------------------------------------------------
# INIT DATABASE
# -------------------------------------------------
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id TEXT PRIMARY KEY,
            official_name TEXT,
            position TEXT,
            place TEXT,
            description TEXT,
            category TEXT,
            risk_level TEXT,
            severity_score REAL,
            timestamp TEXT,
            integrity_hash TEXT,
            evidence_hash TEXT,
            escalation_required BOOLEAN,
            escalation_timestamp TEXT,
            status TEXT,
            chat_id TEXT,
            input_format TEXT,
            staged_file_path TEXT,
            original_text TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS latest_block_hash (
            id TEXT PRIMARY KEY,
            latest_hash TEXT NOT NULL
        )
    """)

    cursor.execute(
        "INSERT INTO latest_block_hash (id, latest_hash) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        ("chain_head", "0"),
    )

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------------------------------
# LATEST HASH HELPERS
# -------------------------------------------------
def get_latest_hash():
    connection = None
    cursor = None
    try:
        connection = sqlite3.connect("complaints.db")
        cursor = connection.cursor()
        cursor.execute(
            "SELECT integrity_hash FROM complaints ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        return "0"
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    return "0"


# -------------------------------------------------
# SAVE COMPLAINT
# -------------------------------------------------
def save_complaint(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    escalation_required = data["risk_level"] == "High"
    escalation_timestamp = datetime.utcnow().isoformat() if escalation_required else None

    cursor.execute("""
        INSERT INTO complaints (
            id,
            official_name,
            position,
            place,
            description,
            category,
            risk_level,
            severity_score,
            timestamp,
            integrity_hash,
            evidence_hash,
            escalation_required,
            escalation_timestamp,
            status,
            chat_id,
            input_format,
            staged_file_path,
            original_text
        ) VALUES (
            %(id)s,
            %(official_name)s,
            %(position)s,
            %(place)s,
            %(description)s,
            %(category)s,
            %(risk_level)s,
            %(severity_score)s,
            %(timestamp)s,
            %(integrity_hash)s,
            %(evidence_hash)s,
            %(escalation_required)s,
            %(escalation_timestamp)s,
            %(status)s,
            %(chat_id)s,
            %(input_format)s,
            %(staged_file_path)s,
            %(original_text)s
        )
        ON CONFLICT (id) DO UPDATE SET
            official_name = EXCLUDED.official_name,
            position = EXCLUDED.position,
            place = EXCLUDED.place,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            risk_level = EXCLUDED.risk_level,
            severity_score = EXCLUDED.severity_score,
            timestamp = EXCLUDED.timestamp,
            integrity_hash = EXCLUDED.integrity_hash,
            evidence_hash = EXCLUDED.evidence_hash,
            escalation_required = EXCLUDED.escalation_required,
            escalation_timestamp = EXCLUDED.escalation_timestamp,
            status = EXCLUDED.status,
            chat_id = EXCLUDED.chat_id,
            input_format = EXCLUDED.input_format,
            staged_file_path = EXCLUDED.staged_file_path,
            original_text = EXCLUDED.original_text
    """, {
        "id": data.get("complaint_id"),
        "official_name": data.get("official_name"),
        "position": data.get("position"),
        "place": data.get("place"),
        "description": data.get("description"),
        "category": data.get("category"),
        "risk_level": data.get("risk_level"),
        "severity_score": data.get("severity_score"),
        "timestamp": data.get("timestamp"),
        "integrity_hash": data.get("data_hash"),
        "evidence_hash": data.get("evidence_hash"),
        "escalation_required": escalation_required,
        "escalation_timestamp": escalation_timestamp,
        "status": "Escalated" if escalation_required else "Submitted",
        "chat_id": data.get("chat_id"),
        "input_format": data.get("input_format"),
        "staged_file_path": data.get("staged_file_path"),
        "original_text": data.get("original_text"),
    })

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------------------------------
# SAVE PENDING COMPLAINT
# -------------------------------------------------
def save_pending_complaint(data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO complaints (
            id,
            official_name,
            position,
            place,
            description,
            category,
            risk_level,
            severity_score,
            timestamp,
            integrity_hash,
            evidence_hash,
            escalation_required,
            escalation_timestamp,
            status,
            chat_id,
            input_format,
            staged_file_path,
            original_text
        ) VALUES (
            %(id)s,
            %(official_name)s,
            %(position)s,
            %(place)s,
            %(description)s,
            %(category)s,
            %(risk_level)s,
            %(severity_score)s,
            %(timestamp)s,
            %(integrity_hash)s,
            %(evidence_hash)s,
            %(escalation_required)s,
            %(escalation_timestamp)s,
            %(status)s,
            %(chat_id)s,
            %(input_format)s,
            %(staged_file_path)s,
            %(original_text)s
        )
        ON CONFLICT (id) DO UPDATE SET
            official_name = EXCLUDED.official_name,
            position = EXCLUDED.position,
            place = EXCLUDED.place,
            description = EXCLUDED.description,
            category = EXCLUDED.category,
            risk_level = EXCLUDED.risk_level,
            severity_score = EXCLUDED.severity_score,
            timestamp = EXCLUDED.timestamp,
            integrity_hash = EXCLUDED.integrity_hash,
            evidence_hash = EXCLUDED.evidence_hash,
            escalation_required = EXCLUDED.escalation_required,
            escalation_timestamp = EXCLUDED.escalation_timestamp,
            status = EXCLUDED.status,
            chat_id = EXCLUDED.chat_id,
            input_format = EXCLUDED.input_format,
            staged_file_path = EXCLUDED.staged_file_path,
            original_text = EXCLUDED.original_text
    """, data)

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------------------------------
# FINALIZE COMPLAINT WITH HASH CHAIN
# -------------------------------------------------
def finalize_complaint_with_chain(complaint_id: str, update_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT latest_hash FROM latest_block_hash WHERE id = %s FOR UPDATE", ("chain_head",))
        row = cursor.fetchone()

        if row:
            previous_hash = row[0]
        else:
            cursor.execute("LOCK TABLE latest_block_hash IN SHARE ROW EXCLUSIVE MODE")
            cursor.execute(
                "INSERT INTO latest_block_hash (id, latest_hash) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                ("chain_head", "0"),
            )
            cursor.execute("SELECT latest_hash FROM latest_block_hash WHERE id = %s FOR UPDATE", ("chain_head",))
            row = cursor.fetchone()
            previous_hash = row[0] if row else "0"

        timestamp = update_data.get("timestamp") or datetime.utcnow().isoformat()
        update_data["timestamp"] = timestamp

        canonical_payload = {
            "previous_hash": previous_hash,
            "complaint_id": complaint_id,
            "payload": {
                key: update_data[key]
                for key in sorted(update_data)
                if key not in {"integrity_hash", "evidence_hash"}
            },
            "timestamp": timestamp,
        }
        hash_input = json.dumps(canonical_payload, sort_keys=True, ensure_ascii=False)
        integrity_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        update_data["integrity_hash"] = integrity_hash
        update_data["evidence_hash"] = previous_hash

        assignments = []
        values = []
        for key in [
            "official_name",
            "position",
            "place",
            "description",
            "category",
            "risk_level",
            "severity_score",
            "timestamp",
            "integrity_hash",
            "evidence_hash",
            "escalation_required",
            "escalation_timestamp",
            "status",
        ]:
            if key in update_data:
                assignments.append(f"{key} = %s")
                values.append(update_data[key])

        if not assignments:
            raise ValueError("No update fields provided to finalize complaint.")

        values.append(complaint_id)
        cursor.execute(
            f"UPDATE complaints SET {', '.join(assignments)} WHERE id = %s",
            values,
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Complaint {complaint_id} does not exist for finalization.")

        cursor.execute(
            "UPDATE latest_block_hash SET latest_hash = %s WHERE id = %s",
            (integrity_hash, "chain_head"),
        )

        conn.commit()
        return {"data_hash": integrity_hash, "previous_hash": previous_hash}
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# -------------------------------------------------
# UPDATE COMPLAINT RESULT
# -------------------------------------------------
def update_complaint_result(complaint_id: str, update_data: dict):
    conn = get_connection()
    cursor = conn.cursor()

    assignments = []
    values = []

    for key in [
        "official_name",
        "position",
        "place",
        "description",
        "category",
        "risk_level",
        "severity_score",
        "timestamp",
        "integrity_hash",
        "evidence_hash",
        "escalation_required",
        "escalation_timestamp",
        "status",
    ]:
        if key in update_data:
            assignments.append(f"{key} = %s")
            values.append(update_data[key])

    if not assignments:
        cursor.close()
        conn.close()
        return

    values.append(complaint_id)
    cursor.execute(f"UPDATE complaints SET {', '.join(assignments)} WHERE id = %s", values)

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------------------------------
# GET COMPLAINT BY ID
# -------------------------------------------------
def get_complaint_by_id(complaint_id: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM complaints WHERE id = %s", (complaint_id,))
    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return dict(row) if row else None


# -------------------------------------------------
# GET ALL COMPLAINTS
# -------------------------------------------------
def get_all_complaints():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("SELECT * FROM complaints ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in rows]
