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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# In-memory state
USER_MODE = {}        # chat_id -> mode string for normal usage
ADMIN_EXPECT = {}     # chat_id -> 'view_pdf_id' / 'approve_pdf_id' / 'add_admin_id'

MAIN_MENU = [
    ["📚 Ask Question", "🧾 SOP Generator"],
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
    """Check if user is admin either in config.ADMIN_IDS or DB flag."""
    db_user = get_user_by_chat_id(chat_id)
    db_flag = bool(db_user and db_user["is_admin"])
    return (chat_id in ADMIN_IDS) or db_flag


def admin_only(func):
    @wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        if not _is_admin_user(user.id):
            update.message.reply_text("Only admins can use this command.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper


def _build_main_keyboard(chat_id: int) -> ReplyKeyboardMarkup:
    rows = [row[:] for row in MAIN_MENU]
    if _is_admin_user(chat_id):
        rows.append(["🛠 Admin Panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def start(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_or_create_user(
        chat_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )
    USER_MODE.pop(user.id, None)
    ADMIN_EXPECT.pop(user.id, None)

    keyboard = _build_main_keyboard(user.id)
    welcome = (
        f"Namaste {user.first_name or ''}! I am *{BOT_NAME}* 🤖💊\n\n"
        "I can help you with:\n"
        "• Pharma Q&A from your reference library\n"
        "• SOP drafting\n"
        "• Regulatory alerts\n"
        "• Training me with your PDFs (after admin approval)\n"
        "• Voice-based questions\n\n"
        "Use the menu below or type /help."
    )
    update.message.reply_markdown(welcome, reply_markup=keyboard)


def help_cmd(update: Update, context: CallbackContext):
    text = (
        "Available commands:\n"
        "/start - Show main menu\n"
        "/help - Show this help\n"
        "/ask - Ask a pharma question\n"
        "/sop - SOP generator mode\n"
        "/alerts - Latest regulatory alerts\n"
        "/uploadpdf - Upload reference PDF for training\n"
        "/subscription - Check your plan & remaining messages\n"
        "/admin - Open admin panel (admins only)\n"
        "/pending_pdfs - (Admin) List pending PDFs\n"
        "/approve_pdf <id> - (Admin) Approve a PDF\n"
        "/view_pdf <id> - (Admin) View a PDF\n"
        "/activate_user <chat_id> - (Admin) Activate lifetime Pro\n"
        "/add_admin <chat_id> - (Admin) Grant admin access"
    )
    update.message.reply_text(text)


def subscription_cmd(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_user_by_chat_id(user.id)
    if not db_user:
        db_user = get_or_create_user(user.id, user.username, user.full_name)
    text = subscription_status_text(db_user)
    update.message.reply_markdown(text)


def ask_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "ask"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text(
        "You are now in *Q&A mode*. Send your pharma question.",
        parse_mode="Markdown",
    )


def sop_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "sop"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text(
        "You are now in *SOP Generator* mode.\n"
        "Send the topic/process name and any special details.",
        parse_mode="Markdown",
    )


def alerts_cmd(update: Update, context: CallbackContext):
    alerts = get_latest_alerts()
    if not alerts:
        update.message.reply_text(
            "No alerts found yet. Admins can seed some via the database.",
        )
        return

    lines = []
    for a in alerts:
        lines.append(f"• *{a['title']}*\n{a['body']}\n")
    update.message.reply_markdown("\n".join(lines))


def uploadpdf_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "uploadpdf"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text(
        "Please send your *PDF file* (max size as per Telegram limits). "
        "It will go to admin for approval before being used in the answer engine.",
        parse_mode="Markdown",
    )


def voice_mode_cmd(update: Update, context: CallbackContext):
    USER_MODE[update.effective_user.id] = "voice"
    ADMIN_EXPECT.pop(update.effective_user.id, None)
    update.message.reply_text(
        "Voice mode activated. Send a *voice message* and I will try to answer.",
        parse_mode="Markdown",
    )


@admin_only
def admin_menu_cmd(update: Update, context: CallbackContext):
    """Show admin-only keyboard."""
    chat_id = update.effective_user.id
    ADMIN_EXPECT.pop(chat_id, None)
    keyboard = ReplyKeyboardMarkup(ADMIN_MENU, resize_keyboard=True)
    update.message.reply_text("🛠 Admin Panel:", reply_markup=keyboard)


def _handle_menu_buttons(update: Update, context: CallbackContext) -> bool:
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    # User menu buttons
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
    if text == "🛠 Admin Panel":
        admin_menu_cmd(update, context)
        return True

    # Admin menu buttons
    if not _is_admin_user(user_id):
        return False

    if text == "📂 Pending PDFs":
        pending_pdfs_cmd(update, context)
        return True
    if text == "👁 View PDF":
        ADMIN_EXPECT[user_id] = "view_pdf_id"
        update.message.reply_text("Send the *PDF ID* you want to view.", parse_mode="Markdown")
        return True
    if text == "✔ Approve PDF":
        ADMIN_EXPECT[user_id] = "approve_pdf_id"
        update.message.reply_text("Send the *PDF ID* you want to approve.", parse_mode="Markdown")
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
        update.message.reply_text("Send the *chat_id* of the user to make admin.", parse_mode="Markdown")
        return True
    if text == "⬅️ Back to User Menu":
        # Go back to normal menu
        ADMIN_EXPECT.pop(user_id, None)
        start(update, context)
        return True

    return False


def _send_users_as_html(update: Update, title: str, rows):
    """Method B: send long lists as downloadable HTML file."""
    html = [
        "<html><head><meta charset='utf-8'><title>",
        title,
        "</title></head><body>",
        f"<h2>{title}</h2>",
        "<table border='1' cellspacing='0' cellpadding='4'>",
        "<tr><th>ID</th><th>Chat ID</th><th>Username</th><th>Name</th><th>Premium</th><th>Admin</th><th>Last Seen (UTC)</th></tr>",
    ]
    for u in rows:
        html.append(
            "<tr>"
            f"<td>{u['id']}</td>"
            f"<td>{u['chat_id']}</td>"
            f"<td>{(u['username'] or '')}</td>"
            f"<td>{(u['full_name'] or '')}</td>"
            f"<td>{'Yes' if u['is_premium'] else 'No'}</td>"
            f"<td>{'Yes' if u['is_admin'] else 'No'}</td>"
            f"<td>{u['last_seen'] or ''}</td>"
            "</tr>"
        )
    html.append("</table></body></html>")
    content = "".join(html)

    bio = BytesIO(content.encode("utf-8"))
    safe_title = title.replace(" ", "_").lower()
    bio.name = f"{safe_title}.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption=f"{title} – total {len(rows)} user(s).",
    )


def text_message(update: Update, context: CallbackContext):
    user = update.effective_user
    message_text = (update.message.text or "").strip()

    # 1) Handle menu buttons (user + admin)
    if _handle_menu_buttons(update, context):
        return

    # 2) Handle admin waiting for ID / chat_id (method B: for admin-only flows)
    admin_mode = ADMIN_EXPECT.get(user.id)
    if admin_mode and _is_admin_user(user.id):
        if admin_mode == "view_pdf_id":
            try:
                doc_id = int(message_text)
            except ValueError:
                update.message.reply_text("Please send a valid numeric PDF ID.")
                return
            _admin_view_pdf_by_id(update, context, doc_id)
            ADMIN_EXPECT.pop(user.id, None)
            return

        if admin_mode == "approve_pdf_id":
            try:
                doc_id = int(message_text)
            except ValueError:
                update.message.reply_text("Please send a valid numeric PDF ID.")
                return
            ok, msg = approve_pending_pdf(doc_id, admin_user_id=user.id)
            update.message.reply_text(msg)
            ADMIN_EXPECT.pop(user.id, None)
            return

        if admin_mode == "add_admin_id":
            try:
                new_admin_chat_id = int(message_text)
            except ValueError:
                update.message.reply_text("Please send a valid numeric chat_id.")
                return
            set_user_admin(new_admin_chat_id, True)
            update.message.reply_text(f"User with chat_id {new_admin_chat_id} is now an admin.")
            ADMIN_EXPECT.pop(user.id, None)
            return

    # 3) Normal commands starting with "/"
    if message_text.startswith("/"):
        return  # let CommandHandlers handle it

    # 4) Normal user Q&A / SOP flow
    db_user = get_or_create_user(user.id, user.username, user.full_name)
    allowed, msg = can_user_ask(db_user)
    if not allowed:
        update.message.reply_markdown(msg)
        return

    mode = USER_MODE.get(user.id, "ask")

    try:
        if mode == "sop":
            reply = generate_sop(message_text)
            consume_message(db_user)
            save_message(db_user["id"], "user", message_text)
            save_message(db_user["id"], "assistant", reply)
            update.message.reply_text(reply)
        else:  # default: ask
            reply = answer_with_context(message_text)
            consume_message(db_user)
            save_message(db_user["id"], "user", message_text)
            save_message(db_user["id"], "assistant", reply)

            # If reply is VERY long, send as file instead of crashing Telegram
            if len(reply) > 3500:
                short = reply[:3000] + "\n\n[Full answer attached as file.]"
                update.message.reply_text(short)

                bio = BytesIO(reply.encode("utf-8"))
                bio.name = "answer.txt"
                update.message.reply_document(
                    document=bio,
                    filename=bio.name,
                    caption="Full detailed answer.",
                )
            else:
                update.message.reply_text(reply)
    except Exception as e:
        logger.exception("Error in text_message")
        update.message.reply_text(f"Error while generating answer: {e}")


def document_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.full_name)
    doc = update.message.document

    if not doc.mime_type or "pdf" not in doc.mime_type.lower():
        update.message.reply_text("Please upload PDF files only.")
        return

    mode = USER_MODE.get(user.id)
    if mode != "uploadpdf":
        update.message.reply_text(
            "To upload reference PDF, first choose '📤 Upload PDF' from the menu or send /uploadpdf."
        )
        return

    file = doc.get_file()
    os.makedirs(PENDING_PDFS_FOLDER, exist_ok=True)
    temp_path = os.path.join(PENDING_PDFS_FOLDER, f"tmp_{doc.file_unique_id}.pdf")
    file.download(custom_path=temp_path)

    final_path = save_pending_pdf(temp_path, doc.file_name or f"{doc.file_unique_id}.pdf")

    title = doc.file_name or "Untitled PDF"
    doc_id = insert_document(
        title=title,
        filename=os.path.basename(final_path),
        pages=0,
        uploaded_by_user_id=db_user["id"],
        status="pending",
    )

    update.message.reply_text(
        f"Thanks! Your PDF is saved with ID *{doc_id}* and sent to admin for approval.",
        parse_mode="Markdown",
    )

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"New PDF uploaded and pending approval:\n"
                    f"ID: {doc_id}\n"
                    f"Title: {title}\n"
                    f"Uploaded by user id: {db_user['id']} (chat {user.id})"
                ),
            )
        except Exception:
            logger.exception("Failed to notify admin about new PDF")


def voice_handler(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_or_create_user(user.id, user.username, user.full_name)

    allowed, msg = can_user_ask(db_user)
    if not allowed:
        update.message.reply_markdown(msg)
        return

    voice = update.message.voice or update.message.audio
    if not voice:
        update.message.reply_text("No voice message detected.")
        return

    file = voice.get_file()
    os.makedirs("tmp_voice", exist_ok=True)
    file_path = os.path.join("tmp_voice", f"{voice.file_unique_id}.ogg")
    file.download(custom_path=file_path)

    text = transcribe_voice(file_path)
    if not text:
        update.message.reply_text(
            "Sorry, I couldn't transcribe this audio. Voice-to-text is not configured yet."
        )
        return

    try:
        reply = answer_with_context(text)
        consume_message(db_user)
        save_message(db_user["id"], "user", f"[voice] {text}")
        save_message(db_user["id"], "assistant", reply)
        update.message.reply_text(reply)
    except Exception as e:
        logger.exception("Error in voice_handler")
        update.message.reply_text(f"Error while answering your voice question: {e}")


@admin_only
def pending_pdfs_cmd(update: Update, context: CallbackContext):
    docs = list_pending_documents()
    if not docs:
        update.message.reply_text("No pending PDFs.")
        return

    lines = []
    for d in docs:
        lines.append(
            f"ID: {d['id']}, Title: {d['title']}, File: {d['filename']}, Status: {d['status']}"
        )

    text = "Pending PDFs:\n" + "\n".join(lines)
    if len(text) < 3500:
        update.message.reply_text(text)
    else:
        # If too long, send as file
        bio = BytesIO(text.encode("utf-8"))
        bio.name = "pending_pdfs.txt"
        update.message.reply_document(
            document=bio,
            filename=bio.name,
            caption=f"Pending PDFs – total {len(docs)}",
        )


def _admin_view_pdf_by_id(update: Update, context: CallbackContext, doc_id: int):
    d = get_document(doc_id)
    if not d:
        update.message.reply_text("PDF not found with that ID.")
        return

    # Prefer pending folder if still pending, else books
    folder = PENDING_PDFS_FOLDER if d["status"] == "pending" else BOOKS_FOLDER
    file_path = os.path.join(folder, d["filename"])
    if not os.path.exists(file_path):
        update.message.reply_text("PDF file not found on server.")
        return

    with open(file_path, "rb") as f:
        update.message.reply_document(
            document=f,
            filename=d["filename"],
            caption=f"PDF ID {doc_id} – {d['title']} (status: {d['status']})",
        )


@admin_only
def view_pdf_cmd(update: Update, context: CallbackContext):
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /view_pdf <id>")
        return
    try:
        doc_id = int(parts[1])
    except ValueError:
        update.message.reply_text("Invalid document id.")
        return

    _admin_view_pdf_by_id(update, context, doc_id)


@admin_only
def approve_pdf_cmd(update: Update, context: CallbackContext):
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /approve_pdf <id>")
        return

    try:
        doc_id = int(parts[1])
    except ValueError:
        update.message.reply_text("Invalid document id.")
        return

    ok, msg = approve_pending_pdf(doc_id, admin_user_id=update.effective_user.id)
    update.message.reply_text(msg)


@admin_only
def activate_user_cmd(update: Update, context: CallbackContext):
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /activate_user <chat_id>")
        return

    try:
        chat_id = int(parts[1])
    except ValueError:
        update.message.reply_text("Invalid chat id.")
        return

    set_user_premium(chat_id, True)
    update.message.reply_text(f"User with chat_id {chat_id} activated as Lifetime Pro.")

    try:
        context.bot.send_message(
            chat_id=chat_id,
            text="Your payment is verified. Lifetime Pro access is now active. ✅",
        )
    except Exception:
        logger.exception("Failed to notify user about activation")


@admin_only
def add_admin_cmd(update: Update, context: CallbackContext):
    parts = (update.message.text or "").split()
    if len(parts) < 2:
        update.message.reply_text("Usage: /add_admin <chat_id>")
        return

    try:
        chat_id = int(parts[1])
    except ValueError:
        update.message.reply_text("Invalid chat id.")
        return

    set_user_admin(chat_id, True)
    update.message.reply_text(f"User with chat_id {chat_id} is now an admin.")


@admin_only
def admin_online_users_cmd(update: Update, context: CallbackContext):
    rows = list_online_users(minutes=15)
    update.message.reply_text(f"Online users (last 15 min): {len(rows)}")
    if rows:
        _send_users_as_html(update, "Online Users (last 15 min)", rows)


@admin_only
def admin_subscribed_users_cmd(update: Update, context: CallbackContext):
    rows = list_users_by_premium(1)
    update.message.reply_text(f"Subscribed (premium) users: {len(rows)}")
    if rows:
        _send_users_as_html(update, "Subscribed Users", rows)


@admin_only
def admin_free_users_cmd(update: Update, context: CallbackContext):
    rows = list_users_by_premium(0)
    update.message.reply_text(f"Free / unsubscribed users: {len(rows)}")
    if rows:
        _send_users_as_html(update, "Free / Unsubscribed Users", rows)


def main():
    init_db()

    # Mark config.ADMIN_IDS as admins in DB (bootstrap)
    for cid in ADMIN_IDS:
        try:
            set_user_admin(cid, True)
        except Exception:
            logger.exception("Failed to ensure admin in DB")

    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

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

    dp.add_handler(MessageHandler(Filters.document, document_handler))
    dp.add_handler(MessageHandler(Filters.voice | Filters.audio, voice_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_message))

    updater.start_polling()
    updater.idle()# method_of_analysis.py

from dataclasses import dataclass, field
from typing import List
import datetime


@dataclass
class MethodOfAnalysisInput:
    method_id: str
    method_title: str
    product_or_material_name: str
    sample_type: str  # API / Finished Product / Raw Material / Packing Material

    purpose: str = ""   # e.g. Assay / Impurity / Content uniformity / ID / etc.
    scope: str = ""
    principle: str = ""
    references: List[str] = field(default_factory=list)  # e.g. Pharmacopoeia, internal specs

    reagents: List[str] = field(default_factory=list)
    standards: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)

    chromatographic_conditions: str = ""  # if applicable
    sample_preparation: str = ""
    standard_preparation: str = ""

    system_suitability: str = ""
    procedure: str = ""
    calculation: str = ""
    acceptance_criteria: str = ""

    validation_status: str = ""  # e.g. Validated / Verified / Under validation
    safety_precautions: str = ""


def _render_list(items: List[str]) -> str:
    if not items:
        return "<p>NA</p>"
    html = "<ul>"
    for i in items:
        html += f"<li>{i}</li>"
    html += "</ul>"
    return html


def generate_moa_html(data: MethodOfAnalysisInput) -> str:
    refs = _render_list(data.references)

    html = f"""
<html>
<head>
<title>Method of Analysis – {data.method_id}</title>
<style>
    body {{ font-family: Arial, sans-serif; font-size: 13px; }}
    h1 {{ font-size: 18px; }}
    h2 {{ font-size: 15px; margin-top: 18px; }}
    table.meta {{ border-collapse: collapse; width: 100%; }}
    table.meta td {{ border: 1px solid #000; padding: 4px; vertical-align: top; }}
</style>
</head>
<body>
<h1>Method of Analysis (MoA)</h1>

<h2>1. General Information</h2>
<table class="meta">
  <tr><td><b>Method ID</b></td><td>{data.method_id}</td></tr>
  <tr><td><b>Title</b></td><td>{data.method_title}</td></tr>
  <tr><td><b>Product / Material</b></td><td>{data.product_or_material_name}</td></tr>
  <tr><td><b>Sample Type</b></td><td>{data.sample_type}</td></tr>
  <tr><td><b>Purpose</b></td><td>{data.purpose}</td></tr>
</table>

<h2>2. Scope</h2>
<p>{data.scope}</p>

<h2>3. Principle</h2>
<p>{data.principle}</p>

<h2>4. References</h2>
{refs}

<h2>5. Reagents, Standards & Equipment</h2>
<p><b>Reagents:</b></p>
{_render_list(data.reagents)}
<p><b>Standards:</b></p>
{_render_list(data.standards)}
<p><b>Equipment / Apparatus:</b></p>
{_render_list(data.equipment)}

<h2>6. Chromatographic / Instrumental Conditions</h2>
<p>{data.chromatographic_conditions}</p>

<h2>7. Preparation of Solutions</h2>
<p><b>Standard Preparation:</b><br>{data.standard_preparation}</p>
<p><b>Sample Preparation:</b><br>{data.sample_preparation}</p>

<h2>8. Procedure</h2>
<p>{data.procedure}</p>

<h2>9. System Suitability</h2>
<p>{data.system_suitability}</p>

<h2>10. Calculations</h2>
<p>{data.calculation}</p>

<h2>11. Acceptance Criteria</h2>
<p>{data.acceptance_criteria}</p>

<h2>12. Validation / Verification Status</h2>
<p>{data.validation_status}</p>

<h2>13. Safety & Precautions</h2>
<p>{data.safety_precautions}</p>

</body>
</html>
"""
    return html


if __name__ == "__main__":
    today = datetime.date.today().strftime("%d-%m-%Y")
    sample = MethodOfAnalysisInput(
        method_id="MOA-API-001",
        method_title="Assay of API XYZ by HPLC",
        product_or_material_name="API XYZ",
        sample_type="API",
        purpose="Assay",
        scope="This method applies to routine assay of API XYZ for release and stability samples.",
        principle="API XYZ is separated by reverse-phase HPLC and quantified by UV detection.",
        references=["USP monograph", "Internal Specification QSP-XYZ-01"],
        reagents=["Acetonitrile HPLC grade", "Water HPLC grade", "Buffer pH 3.0"],
        standards=["API XYZ Working Standard"],
        equipment=["HPLC system with UV detector", "Analytical balance", "Ultrasonicator"],
        chromatographic_conditions="Column: C18, 250 x 4.6 mm; Mobile phase: Buffer:ACN (60:40); Flow: 1.0 mL/min; Detection: 254 nm; Injection volume: 20 µL.",
        standard_preparation="Accurately weigh about 50 mg of API XYZ WS, transfer to 50 mL volumetric flask, dissolve and dilute with mobile phase.",
        sample_preparation="Accurately weigh sample equivalent to 50 mg of API XYZ, transfer to 50 mL volumetric flask, dissolve and dilute with mobile phase, then filter.",
        system_suitability="The %RSD of peak area for six replicate injections of standard shall not be more than 2.0%. Tailing factor shall not be more than 2.0.",
        procedure="Set the chromatographic conditions as described. Inject blank, standard and sample solutions. Record chromatograms and peak areas.",
        calculation="Assay (%) = (Area_sample / Area_standard) x (Wt_standard / Wt_sample) x (Purity_standard) x 100.",
        acceptance_criteria="API content should be between 98.0% and 102.0% of label claim.",
        validation_status="Validated as per ICH Q2(R1).",
        safety_precautions="Handle organic solvents in fume hood and use appropriate PPE."
    )

    html_output = generate_moa_html(sample)
    with open("sample_moa.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    print("sample_moa.html generated.")



if __name__ == "__main__":
    main()
