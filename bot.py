import logging
import os
from functools import wraps
from io import BytesIO
from datetime import datetime

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    ConversationHandler,
)

from config import TELEGRAM_BOT_TOKEN, ADMIN_IDS, BOOKS_FOLDER, PENDING_PDFS_FOLDER, BOT_NAME
from database import (
    init_db,
    get_or_create_user,
    get_user_by_chat_id,
    save_message,
    list_pending_documents,
    insert_document,
    get_document,
    set_user_premium,
    set_user_admin,
    get_all_users,
    list_users_by_premium,
    list_online_users,
)
from subscription import can_user_ask, consume_message, subscription_status_text
from ai_engine import answer_with_context, generate_sop
from regulatory_alerts import get_latest_alerts
from voice_handler import transcribe_voice
from pdf_approval import save_pending_pdf, approve_pending_pdf

# ==========================================================
# NEW IMPORTS (conversation handlers)
# ==========================================================
try:
    from handlers.moa_handler import moa_conv
    from handlers.deviation_handler import deviation_conv
    from handlers.capa_handler import capa_conv
    from handlers.changecontrol_handler import cc_conv
    from handlers.artwork_handler import artwork_conv
except Exception:
    moa_conv = None
    deviation_conv = None
    capa_conv = None
    cc_conv = None
    artwork_conv = None
# ==========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory state
USER_MODE = {}   # chat_id -> "ask" / "sop" / "uploadpdf" / "voice"
ADMIN_EXPECT = {}  # chat_id -> "view_pdf_id" / "approve_pdf_id" / "add_admin_id"

# ==========================================================
# UPDATED MAIN MENU
# ==========================================================
MAIN_MENU = [
    ["📚 Ask Question", "🧾 SOP Generator"],
    ["📄 Deviation", "🧪 Method of Analysis"],
    ["🛡 CAPA", "⚙ Change Control"],
    ["🖼 Artwork Review"],
    ["🚨 Regulatory Alerts", "📤 Upload PDF"],
    ["🎙 Voice Q&A", "💳 Subscription Status"],
]

ADMIN_MENU = [
    ["📂 Pending PDFs"],
    ["👁 View PDF", "✔ Approve PDF"],
    ["👥 Online Users"],
    ["✅ Subscribed Users", "🚫 Free Users"],
    ["➕ Add Admin"],
    ["⬅️ Back to User Menu"],
]


def _is_admin_user(chat_id: int) -> bool:
    db_user = get_user_by_chat_id(chat_id)
    db_flag = bool(db_user and db_user["is_admin"])
    return (chat_id in ADMIN_IDS) or db_flag


def admin_only(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not _is_admin_user(update.effective_user.id):
            update.message.reply_text("Only admins can use this command.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper


def _build_main_keyboard(chat_id: int) -> ReplyKeyboardMarkup:
    rows = [row[:] for row in MAIN_MENU]
    if _is_admin_user(chat_id):
        rows.append(["🛠 Admin Panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ==========================================================
# START / HELP / MENU COMMANDS
# ==========================================================
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.full_name)
    USER_MODE.pop(user.id, None)
    ADMIN_EXPECT.pop(user.id, None)

    keyboard = _build_main_keyboard(user.id)
    welcome = (
        f"Namaste {user.first_name or ''}! I am *{BOT_NAME}* 🤖💊\n\n"
        "I can help you with:\n"
        "• Pharma Q&A\n"
        "• SOP drafting\n"
        "• Regulatory alerts\n"
        "• Deviation / CAPA / Change Control\n"
        "• Method of Analysis\n"
        "• Artwork Review\n"
        "• Trained PDF-based answers\n"
        "• Voice mode\n\n"
        "Use the menu below 👇"
    )
    update.message.reply_markdown(welcome, reply_markup=keyboard)


def help_cmd(update: Update, context: CallbackContext):
    text = (
        "Available commands:\n"
        "/start - Show main menu\n"
        "/help - Show this help\n"
        "/ask - Ask a pharma question\n"
        "/sop - SOP generator mode\n"
        "/alerts - Regulatory alerts\n"
        "/uploadpdf - Upload reference PDF\n"
        "/subscription - Your subscription status\n"
        "/admin - Admin panel\n"
        "\n"
        "NEW:\n"
        "/moa – Method of Analysis\n"
        "/deviation – Deviation Report\n"
        "/capa – CAPA\n"
        "/cc – Change Control\n"
        "/artwork – Artwork Review\n"
    )
    update.message.reply_text(text)


# ==========================================================
# EXISTING COMMANDS: SUBSCRIPTION / Q&A / SOP / ALERTS
# ==========================================================
def subscription_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.full_name)
    update.message.reply_markdown(subscription_status_text(db_user))


def ask_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "ask"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text("You are now in *Q&A mode*.", parse_mode="Markdown")


def sop_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "sop"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text(
        "You are now in *SOP Generator* mode.\nSend topic/process.",
        parse_mode="Markdown",
    )


def alerts_cmd(update: Update, context: CallbackContext):
    alerts = get_latest_alerts()
    if not alerts:
        update.message.reply_text("No regulatory alerts found.")
        return

    lines = []
    for a in alerts:
        lines.append(f"• *{a['title']}*\n{a['body']}\n")
    update.message.reply_markdown("\n".join(lines))


def uploadpdf_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "uploadpdf"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text("Send your PDF file.", parse_mode="Markdown")


def voice_mode_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "voice"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text("Voice mode ON. Send audio.", parse_mode="Markdown")


# ==========================================================
# ADMIN MENU COMMAND
# ==========================================================
@admin_only
def admin_menu_cmd(update: Update, context: CallbackContext):
    chat_id = update.effective_user.id
    ADMIN_EXPECT.pop(chat_id, None)
    keyboard = ReplyKeyboardMarkup(ADMIN_MENU, resize_keyboard=True)
    update.message.reply_text("🛠 Admin Panel:", reply_markup=keyboard)


# ==========================================================
# 🎯 MENU BUTTON HANDLER (ONLY SIMPLE ACTIONS HERE)
# ==========================================================
def _handle_menu_buttons(update: Update, context: CallbackContext) -> bool:
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    # USER MENU (simple mode switches)
    if text == "📚 Ask Question":
        ask_cmd(update, context)
        return True

    if text == "🧾 SOP Generator":
        sop_cmd(update, context)
        return True

    if text == "🚨 Regulatory Alerts":
        alerts_cmd(update, context)
        return True

    if text == "📤 Upload PDF":
        uploadpdf_cmd(update, context)
        return True

    if text == "🎙 Voice Q&A":
        voice_mode_cmd(update, context)
        return True

    if text == "💳 Subscription Status":
        subscription_cmd(update, context)
        return True

    # IMPORTANT:
    # Do NOT manually call start_moa / start_deviation / etc here.
    # The ConversationHandlers will capture these button texts
    # via Filters.regex entry_points in their own files.

    # ADMIN BUTTONS
    if text == "🛠 Admin Panel" and _is_admin_user(user_id):
        admin_menu_cmd(update, context)
        return True

    if not _is_admin_user(user_id):
        return False

    # Admin actions
    if text == "📂 Pending PDFs":
        pending_pdfs_cmd(update, context)
        return True

    if text == "👁 View PDF":
        ADMIN_EXPECT[user_id] = "view_pdf_id"
        update.message.reply_text("Send PDF ID.")
        return True

    if text == "✔ Approve PDF":
        ADMIN_EXPECT[user_id] = "approve_pdf_id"
        update.message.reply_text("Send PDF ID to approve.")
        return True

    if text == "👥 Online Users":
        admin_online_users_cmd(update, context)
        return True

    if text == "✅ Subscribed Users":
        admin_subscribed_users_cmd(update, context)
        return True

    if text == "🚫 Free Users":
        admin_free_users_cmd(update, context)
        return True

    if text == "➕ Add Admin":
        ADMIN_EXPECT[user_id] = "add_admin_id"
        update.message.reply_text("Send chat_id to grant admin.")
        return True

    if text == "⬅️ Back to User Menu":
        start(update, context)
        return True

    return False


# ==========================================================
# TEXT MESSAGE HANDLER
# ==========================================================
def text_message(update: Update, context: CallbackContext):
    user = update.effective_user
    message_text = (update.message.text or "").strip()

    # 1) Handle menu buttons
    if _handle_menu_buttons(update, context):
        return

    # 2) Handle admin expectations (ID entry)
    admin_mode = ADMIN_EXPECT.get(user.id)
    if admin_mode and _is_admin_user(user.id):
        if admin_mode == "view_pdf_id":
            try:
                doc_id = int(message_text)
                _admin_view_pdf_by_id(update, context, doc_id)
            except Exception:
                update.message.reply_text("Invalid PDF ID.")
            ADMIN_EXPECT.pop(user.id, None)
            return

        if admin_mode == "approve_pdf_id":
            try:
                doc_id = int(message_text)
                ok, msg = approve_pending_pdf(doc_id, user.id)
                update.message.reply_text(msg)
            except Exception:
                update.message.reply_text("Invalid PDF ID.")
            ADMIN_EXPECT.pop(user.id, None)
            return

        if admin_mode == "add_admin_id":
            try:
                new_admin = int(message_text)
                set_user_admin(new_admin, True)
                update.message.reply_text(f"User {new_admin} is now admin.")
            except Exception:
                update.message.reply_text("Invalid chat_id.")
            ADMIN_EXPECT.pop(user.id, None)
            return

    # 3) Allow /commands to go to CommandHandlers
    if message_text.startswith("/"):
        return

    # 4) MAIN ENGINE (Ask / SOP)
    db_user = get_or_create_user(user.id, user.username, user.full_name)
    allowed, msg = can_user_ask(db_user)
    if not allowed:
        update.message.reply_markdown(msg)
        return

    mode = USER_MODE.get(user.id, "ask")

    try:
        if mode == "sop":
            reply = generate_sop(message_text)
        else:
            reply = answer_with_context(message_text)

        consume_message(db_user)
        save_message(db_user["id"], "user", message_text)
        save_message(db_user["id"], "assistant", reply)

        if len(reply) > 3500:
            short = reply[:3000] + "\n\n[Full answer attached]"
            update.message.reply_text(short)

            bio = BytesIO(reply.encode("utf-8"))
            bio.name = "answer.txt"
            update.message.reply_document(bio, filename=bio.name)
        else:
            update.message.reply_text(reply)

    except Exception as e:
        logger.exception("Error in text_message")
        update.message.reply_text(f"Error: {e}")


# ==========================================================
# 📤 PDF UPLOAD HANDLER
# ==========================================================
def document_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.full_name)
    doc = update.message.document

    if not doc.mime_type or "pdf" not in doc.mime_type.lower():
        update.message.reply_text("Upload PDF only.")
        return

    if USER_MODE.get(user.id) != "uploadpdf":
        update.message.reply_text("Use '📤 Upload PDF' first.")
        return

    file = doc.get_file()
    os.makedirs(PENDING_PDFS_FOLDER, exist_ok=True)
    tmp_path = os.path.join(PENDING_PDFS_FOLDER, f"tmp_{doc.file_unique_id}.pdf")
    file.download(tmp_path)

    final_path = save_pending_pdf(tmp_path, doc.file_name)
    doc_id = insert_document(
        title=doc.file_name,
        filename=os.path.basename(final_path),
        pages=0,
        uploaded_by_user_id=db_user["id"],
        status="pending",
    )

    update.message.reply_text(
        f"Your PDF is saved with ID *{doc_id}* and sent to admin.",
        parse_mode="Markdown",
    )

    for admin_id in ADMIN_IDS:
        try:
            context.bot.send_message(
                admin_id,
                f"New PDF pending:\nID: {doc_id}\nUser: {db_user['id']} (chat {user.id})",
            )
        except Exception:
            pass


# ==========================================================
# 🎙 VOICE HANDLER
# ==========================================================
def voice_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.full_name)

    allowed, msg = can_user_ask(db_user)
    if not allowed:
        update.message.reply_markdown(msg)
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        update.message.reply_text("No audio found.")
        return

    file = voice.get_file()
    os.makedirs("tmp_voice", exist_ok=True)
    path = os.path.join("tmp_voice", f"{voice.file_unique_id}.ogg")
    file.download(path)

    text = transcribe_voice(path)
    if not text:
        update.message.reply_text("Failed to transcribe audio.")
        return

    try:
        reply = answer_with_context(text)
        consume_message(db_user)
        save_message(db_user["id"], "user", f"[voice] {text}")
        save_message(db_user["id"], "assistant", reply)

        update.message.reply_text(reply)
    except Exception as e:
        update.message.reply_text(f"Error: {e}")


# ==========================================================
# 📂 ADMIN LIST FUNCTIONS
# ==========================================================
@admin_only
def pending_pdfs_cmd(update: Update, context: CallbackContext):
    docs = list_pending_documents()
    if not docs:
        update.message.reply_text("No pending PDFs.")
        return

    lines = [f"ID: {d['id']}, {d['title']}, File: {d['filename']}" for d in docs]
    text = "Pending PDFs:\n" + "\n".join(lines)

    if len(text) < 3500:
        update.message.reply_text(text)
    else:
        bio = BytesIO(text.encode())
        bio.name = "pending_pdfs.txt"
        update.message.reply_document(bio)


@admin_only
def view_pdf_cmd(update: Update, context: CallbackContext):
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /view_pdf <id>")
        return

    try:
        doc_id = int(parts[1])
        _admin_view_pdf_by_id(update, context, doc_id)
    except Exception:
        update.message.reply_text("Invalid ID")


def _admin_view_pdf_by_id(update: Update, context: CallbackContext, doc_id: int):
    d = get_document(doc_id)
    if not d:
        update.message.reply_text("PDF not found.")
        return

    folder = PENDING_PDFS_FOLDER if d["status"] == "pending" else BOOKS_FOLDER
    path = os.path.join(folder, d["filename"])

    if not os.path.exists(path):
        update.message.reply_text("File missing.")
        return

    with open(path, "rb") as f:
        update.message.reply_document(f, filename=d["filename"])


@admin_only
def approve_pdf_cmd(update: Update, context: CallbackContext):
    parts = update.message.text.split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /approve_pdf <id>")
        return

    try:
        doc_id = int(parts[1])
    except Exception:
        update.message.reply_text("Invalid ID.")
        return

    ok, msg = approve_pending_pdf(doc_id, update.effective_user.id)
    update.message.reply_text(msg)


# ==========================================================
# ADMIN: USER MANAGEMENT
# ==========================================================
@admin_only
def activate_user_cmd(update: Update, context: CallbackContext):
    parts = update.message.text.split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /activate_user <chat_id>")
        return

    try:
        chat_id = int(parts[1])
        set_user_premium(chat_id, True)
        update.message.reply_text(f"User {chat_id} is now Lifetime Pro.")
        context.bot.send_message(chat_id, "Your Pro plan is activated. 🎉")
    except Exception:
        update.message.reply_text("Invalid chat_id.")


@admin_only
def add_admin_cmd(update: Update, context: CallbackContext):
    parts = update.message.text.split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /add_admin <chat_id>")
        return

    try:
        chat_id = int(parts[1])
        set_user_admin(chat_id, True)
        update.message.reply_text(f"User {chat_id} is now admin.")
    except Exception:
        update.message.reply_text("Invalid chat_id.")


@admin_only
def admin_online_users_cmd(update: Update, context: CallbackContext):
    rows = list_online_users(minutes=15)
    update.message.reply_text(f"Online users: {len(rows)}")

    if rows:
        _send_users_as_html(update, "Online Users (15 min)", rows)


@admin_only
def admin_subscribed_users_cmd(update: Update, context: CallbackContext):
    rows = list_users_by_premium(1)
    update.message.reply_text(f"Premium users: {len(rows)}")
    if rows:
        _send_users_as_html(update, "Premium Users", rows)


@admin_only
def admin_free_users_cmd(update: Update, context: CallbackContext):
    rows = list_users_by_premium(0)
    update.message.reply_text(f"Free users: {len(rows)}")
    if rows:
        _send_users_as_html(update, "Free Users", rows)


# ==========================================================
# HTML REPORT TABLE GENERATOR
# ==========================================================
def _send_users_as_html(update: Update, title: str, rows):
    html = [
        "<html><body>",
        f"<h2>{title}</h2>",
        "<table border='1' cellspacing='0' cellpadding='4'>",
        "<tr><th>ID</th><th>Chat ID</th><th>Username</th><th>Name</th>"
        "<th>Premium</th><th>Admin</th><th>Last Seen</th></tr>",
    ]
    for u in rows:
        html.append(
            "<tr>"
            f"<td>{u['id']}</td>"
            f"<td>{u['chat_id']}</td>"
            f"<td>{u['username'] or ''}</td>"
            f"<td>{u['full_name'] or ''}</td>"
            f"<td>{'Yes' if u['is_premium'] else 'No'}</td>"
            f"<td>{'Yes' if u['is_admin'] else 'No'}</td>"
            f"<td>{u['last_seen']}</td>"
            "</tr>"
        )
    html.append("</table></body></html>")

    bio = BytesIO("".join(html).encode("utf-8"))
    bio.name = "users.html"

    update.message.reply_document(bio, filename=bio.name)


# ==========================================================
# MAIN ENTRYPOINT
# ==========================================================
def main():
    init_db()

    for cid in ADMIN_IDS:
        try:
            set_user_admin(cid, True)
        except Exception:
            pass

    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # COMMANDS
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("subscription", subscription_cmd))
    dp.add_handler(CommandHandler("ask", ask_cmd))
    dp.add_handler(CommandHandler("sop", sop_cmd))
    dp.add_handler(CommandHandler("alerts", alerts_cmd))
    dp.add_handler(CommandHandler("uploadpdf", uploadpdf_cmd))
    dp.add_handler(CommandHandler("voice", voice_mode_cmd))
    dp.add_handler(CommandHandler("admin", admin_menu_cmd))
    dp.add_handler(CommandHandler("pending_pdfs", pending_pdfs_cmd))
    dp.add_handler(CommandHandler("approve_pdf", approve_pdf_cmd))
    dp.add_handler(CommandHandler("view_pdf", view_pdf_cmd))
    dp.add_handler(CommandHandler("activate_user", activate_user_cmd))
    dp.add_handler(CommandHandler("add_admin", add_admin_cmd))

    # NEW QA FEATURE CONVERSATION HANDLERS
    if moa_conv:
        dp.add_handler(moa_conv)
    if deviation_conv:
        dp.add_handler(deviation_conv)
    if capa_conv:
        dp.add_handler(capa_conv)
    if cc_conv:
        dp.add_handler(cc_conv)
    if artwork_conv:
        dp.add_handler(artwork_conv)

    # FILE & VOICE
    dp.add_handler(MessageHandler(Filters.document, document_handler))
    dp.add_handler(MessageHandler(Filters.voice | Filters.audio, voice_handler))

    # TEXT (fallback)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
