import os
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

from backend.celery_app import celery_app
from data_layer.storage.database import get_complaint_by_id, update_complaint_result, finalize_complaint_with_chain
from backend.logic.service import process_complaint
from preprocessing.media_pipeline import extract_text_from_media

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
bot = Bot(token=TELEGRAM_BOT_TOKEN)


def format_result_message(result, complaint_id):
    category = result.get("category", "Unknown")
    risk = result.get("risk_level", "Unknown")
    action = result.get("recommended_action", "No recommendation provided.")

    return f"""
✅ Complaint Processing Complete

ID: {complaint_id}
Category: {category}
Risk Level: {risk}
Recommended Action: {action}
"""


@celery_app.task(name="backend.tasks.process_complaint_task")
def process_complaint_task(complaint_id: str):
    record = get_complaint_by_id(complaint_id)
    if not record:
        return {"error": "complaint_not_found", "complaint_id": complaint_id}

    complaint_text = record.get("original_text")
    input_format = record.get("input_format")
    staged_file = record.get("staged_file_path")

    if input_format != "Text":
        if not staged_file or not os.path.exists(staged_file):
            update_complaint_result(
                complaint_id,
                {
                    "description": "Staged media file not found.",
                    "status": "Failed",
                },
            )
            bot.send_message(
                chat_id=record["chat_id"],
                text=f"⚠ Your complaint {complaint_id} could not be processed because the uploaded file was unavailable.",
            )
            return {"error": "staged_file_missing", "complaint_id": complaint_id}

        try:
            complaint_text = extract_text_from_media(staged_file)
        except Exception as exc:
            update_complaint_result(
                complaint_id,
                {
                    "description": "Media extraction failed.",
                    "status": "Failed",
                },
            )
            bot.send_message(
                chat_id=record["chat_id"],
                text=f"⚠ Your complaint {complaint_id} could not be processed due to media extraction failure.",
            )
            return {"error": "media_extraction_failed", "complaint_id": complaint_id}

    if not complaint_text or len(complaint_text.strip()) < 15:
        update_complaint_result(
            complaint_id,
            {
                "description": "Complaint text was too short after extraction.",
                "status": "Failed",
            },
        )
        bot.send_message(
            chat_id=record["chat_id"],
            text=f"⚠ Your complaint {complaint_id} was received, but the extracted text contained too little information.",
        )
        return {"error": "insufficient_text", "complaint_id": complaint_id}

    result = process_complaint(complaint_text)
    status = "Escalated" if result.get("escalation_required") else "Submitted"

    update_data = {
        "description": complaint_text,
        "category": result.get("category"),
        "risk_level": result.get("risk_level"),
        "severity_score": result.get("severity_score"),
        "timestamp": result.get("timestamp"),
        "escalation_required": bool(result.get("escalation_required")),
        "escalation_timestamp": datetime.utcnow().isoformat() if result.get("escalation_required") else None,
        "status": status,
    }

    finalize_complaint_with_chain(complaint_id, update_data)

    bot.send_message(
        chat_id=record["chat_id"],
        text=format_result_message(result, complaint_id),
    )

    if result.get("risk_level") == "High" and ADMIN_CHAT_ID:
        bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🚨 HIGH RISK CORRUPTION ALERT\n\nID: {complaint_id}\nCategory: {result.get('category')}\nRisk: {result.get('risk_level')}\n\nImmediate review recommended.",
        )

    return {"status": "completed", "complaint_id": complaint_id}
