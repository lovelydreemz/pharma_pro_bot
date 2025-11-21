# handlers/artwork_handler.py

import os
from io import BytesIO

from telegram import Update
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
)

from artwork_review import run_artwork_review  # your B3 module

ARTWORK_STD, ARTWORK_REF = range(2)

TMP_ARTWORK_FOLDER = "tmp_artwork"


def _ensure_tmp_folder():
    os.makedirs(TMP_ARTWORK_FOLDER, exist_ok=True)


def _save_pdf(document, prefix: str, chat_id: int) -> str:
    _ensure_tmp_folder()
    filename = f"{prefix}_{chat_id}_{document.file_unique_id}.pdf"
    path = os.path.join(TMP_ARTWORK_FOLDER, filename)
    file = document.get_file()
    file.download(custom_path=path)
    return path


def start_artwork_review(update: Update, context: CallbackContext) -> int:
    update.message.reply_markdown(
        "🖼 *Artwork Review Mode*\n\n"
        "Step 1️⃣: Please upload the *Standard / Approved* artwork PDF.\n\n"
        "After that I will ask for the *Reference / New* artwork PDF.",
    )
    return ARTWORK_STD


def artwork_standard_received(update: Update, context: CallbackContext) -> int:
    doc = update.message.document
    if not doc or not (doc.mime_type or "").lower().endswith("pdf"):
        update.message.reply_markdown(
            "⚠ Please upload a *PDF* file for the Standard artwork."
        )
        return ARTWORK_STD

    chat_id = update.effective_chat.id
    std_path = _save_pdf(doc, "std", chat_id)
    context.user_data["artwork_std_path"] = std_path

    update.message.reply_markdown(
        "✅ Standard artwork received.\n\n"
        "Step 2️⃣: Now upload the *Reference / New* artwork PDF."
    )
    return ARTWORK_REF


def artwork_reference_received(update: Update, context: CallbackContext) -> int:
    doc = update.message.document
    if not doc or not (doc.mime_type or "").lower().endswith("pdf"):
        update.message.reply_markdown(
            "⚠ Please upload a *PDF* file for the Reference artwork."
        )
        return ARTWORK_REF

    chat_id = update.effective_chat.id
    ref_path = _save_pdf(doc, "ref", chat_id)
    std_path = context.user_data.get("artwork_std_path")

    if not std_path or not os.path.exists(std_path):
        update.message.reply_text(
            "I lost the Standard artwork file in memory. "
            "Please restart the flow with /artwork."
        )
        return ConversationHandler.END

    update.message.reply_text(
        "🧪 Running artwork comparison and generating HTML report..."
    )

    try:
        html_report = run_artwork_review(std_path, ref_path)
    except Exception as e:
        update.message.reply_text(f"Error while analysing artwork: {e}")
        return ConversationHandler.END

    bio = BytesIO(html_report.encode("utf-8"))
    bio.name = "artwork_review_report.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="📄 Artwork Review Report (HTML)",
    )

    try:
        os.remove(std_path)
    except Exception:
        pass
    try:
        os.remove(ref_path)
    except Exception:
        pass

    context.user_data.pop("artwork_std_path", None)
    return ConversationHandler.END


def cancel_artwork(update: Update, context: CallbackContext) -> int:
    context.user_data.pop("artwork_std_path", None)
    update.message.reply_text("Artwork review cancelled.")
    return ConversationHandler.END


artwork_conv = ConversationHandler(
    entry_points=[
        CommandHandler("artwork", start_artwork_review),
        # Triggered by menu button "🖼 Artwork Review"
        MessageHandler(Filters.regex(r"^🖼 Artwork Review$"), start_artwork_review),
    ],
    states={
        ARTWORK_STD: [
            MessageHandler(Filters.document, artwork_standard_received),
        ],
        ARTWORK_REF: [
            MessageHandler(Filters.document, artwork_reference_received),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_artwork)],
    name="artwork_review_conversation",
    persistent=False,
)
