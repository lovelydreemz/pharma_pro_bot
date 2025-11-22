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

# Your B3 comparison engine
from artwork_review import run_artwork_review


# ===== STATES =====
ARTWORK_STD, ARTWORK_REF = range(2)

TMP_ARTWORK_FOLDER = "tmp_artwork"


# ==========================================================
# HELPERS
# ==========================================================
def _ensure_tmp_folder():
    os.makedirs(TMP_ARTWORK_FOLDER, exist_ok=True)


def _save_pdf(document, prefix: str, chat_id: int) -> str:
    """Save uploaded Telegram document as PDF in a temp folder and return full path."""
    _ensure_tmp_folder()
    filename = f"{prefix}_{chat_id}_{document.file_unique_id}.pdf"
    path = os.path.join(TMP_ARTWORK_FOLDER, filename)
    file = document.get_file()
    file.download(custom_path=path)
    return path


# ==========================================================
# ENTRY POINT
# ==========================================================
def start_artwork(update: Update, context: CallbackContext) -> int:
    """
    Starts when user types:
    - /artwork
    - artwork, review artwork (via regex)
    - menu button "🖼 Artwork Review"
    """
    update.message.reply_markdown(
        "🖼 *Artwork Review Mode*\n\n"
        "Step 1️⃣: Please upload the *Standard / Approved* artwork PDF.\n\n"
        "After that I will ask for the *Reference / New* artwork PDF.",
    )
    return ARTWORK_STD


# ==========================================================
# STEP 1 – STANDARD ARTWORK
# ==========================================================
def artwork_standard_received(update: Update, context: CallbackContext) -> int:
    doc = update.message.document
    if not doc or not (doc.mime_type or "").lower().endswith("pdf"):
        update.message.reply_text("⚠ Please upload a *PDF* file for the Standard artwork.")
        return ARTWORK_STD

    chat_id = update.effective_chat.id
    std_path = _save_pdf(doc, "std", chat_id)
    context.user_data["artwork_std"] = std_path

    update.message.reply_markdown(
        "✅ Standard artwork received.\n\n"
        "Step 2️⃣: Now upload the *Reference / New* artwork PDF."
    )
    return ARTWORK_REF


# ==========================================================
# STEP 2 – REFERENCE ARTWORK + RUN COMPARISON
# ==========================================================
def artwork_reference_received(update: Update, context: CallbackContext) -> int:
    doc = update.message.document
    if not doc or not (doc.mime_type or "").lower().endswith("pdf"):
        update.message.reply_text("⚠ Please upload a *PDF* for the Reference artwork.")
        return ARTWORK_REF

    chat_id = update.effective_chat.id
    ref_path = _save_pdf(doc, "ref", chat_id)

    std_path = context.user_data.get("artwork_std")
    if not std_path or not os.path.exists(std_path):
        update.message.reply_text("❌ Standard artwork missing. Please restart with /artwork")
        return ConversationHandler.END

    update.message.reply_text("🧪 Comparing artworks and generating report...")

    try:
        html = run_artwork_review(std_path, ref_path)
    except Exception as e:
        update.message.reply_text(f"Error during analysis: {e}")
        return ConversationHandler.END

    bio = BytesIO(html.encode("utf-8"))
    bio.name = "artwork_review_report.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="📄 Artwork Review Report",
    )

    # Cleanup
    for f in (std_path, ref_path):
        try:
            os.remove(f)
        except:
            pass

    context.user_data.pop("artwork_std", None)
    return ConversationHandler.END


# ==========================================================
# CANCEL
# ==========================================================
def cancel_artwork(update: Update, context: CallbackContext):
    context.user_data.pop("artwork_std", None)
    update.message.reply_text("Artwork review cancelled.")
    return ConversationHandler.END


# ==========================================================
# CONVERSATION HANDLER (PTB 13.x)
# ==========================================================
artwork_conv = ConversationHandler(
    entry_points=[
        CommandHandler("artwork", start_artwork),
        MessageHandler(Filters.regex(r"(?i)(artwork|review artwork|start artwork)"), start_artwork),
    ],
    states={
        ARTWORK_STD: [
            MessageHandler(Filters.document, artwork_standard_received),
        ],
        ARTWORK_REF: [
            MessageHandler(Filters.document, artwork_reference_received),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_artwork),
    ],
    per_user=True,
)
