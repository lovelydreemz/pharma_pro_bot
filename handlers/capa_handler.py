# handlers/capa_handler.py

from io import BytesIO

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CommandHandler,
)

from modules.capa import CAPAInput, generate_capa_html

# ===== STATES =====
(
    CAPA_ID,
    CAPA_DATE,
    CAPA_BY,
    CAPA_SOURCE,
    CAPA_PROBLEM,
    CAPA_ROOT_CAUSE,
    CAPA_TOOLS,
    CAPA_CONTAINMENT,
    CAPA_CA,
    CAPA_PA,
    CAPA_RESPONSIBLE,
    CAPA_TARGET_DATE,
    CAPA_EFFECTIVENESS_CRITERIA,
    CAPA_EFFECTIVENESS_PLAN,
) = range(14)


# ===== ENTRY COMMAND =====
def start_capa(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🛡 *CAPA Generator*\n\n"
        "Let's create a CAPA.\n"
        "Enter *CAPA ID* (e.g., CAPA-001):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data["capa"] = {}
    return CAPA_ID


# ===== QUESTION FLOW =====
def capa_id(update, context):
    context.user_data["capa"]["capa_id"] = update.message.text.strip()
    update.message.reply_text("Enter *Date Initiated*:")
    return CAPA_DATE


def capa_date(update, context):
    context.user_data["capa"]["date_initiated"] = update.message.text.strip()
    update.message.reply_text("Enter *Initiated By*:")
    return CAPA_BY


def capa_by(update, context):
    context.user_data["capa"]["initiated_by"] = update.message.text.strip()
    update.message.reply_text("Enter *Source* (Deviation, Audit, Complaint, etc.):")
    return CAPA_SOURCE


def capa_source(update, context):
    context.user_data["capa"]["source"] = update.message.text.strip()
    update.message.reply_text("Enter *Problem Statement*:")
    return CAPA_PROBLEM


def capa_problem(update, context):
    context.user_data["capa"]["problem_statement"] = update.message.text.strip()
    update.message.reply_text("Enter *Root Cause*:")
    return CAPA_ROOT_CAUSE


def capa_root_cause(update, context):
    context.user_data["capa"]["root_cause"] = update.message.text.strip()
    update.message.reply_text("Enter *Tools Used* (e.g. 5 Why, Fishbone):")
    return CAPA_TOOLS


def capa_tools(update, context):
    tools = [t.strip() for t in update.message.text.split(",")]
    context.user_data["capa"]["selected_tools"] = tools
    update.message.reply_text("Enter *Containment Actions* (comma separated):")
    return CAPA_CONTAINMENT


def capa_containment(update, context):
    context.user_data["capa"]["containment_actions"] = [
        a.strip() for a in update.message.text.split(",")
    ]
    update.message.reply_text("Enter *Corrective Actions* (comma separated):")
    return CAPA_CA


def capa_ca(update, context):
    context.user_data["capa"]["corrective_actions"] = [
        a.strip() for a in update.message.text.split(",")
    ]
    update.message.reply_text("Enter *Preventive Actions* (comma separated):")
    return CAPA_PA


def capa_pa(update, context):
    context.user_data["capa"]["preventive_actions"] = [
        a.strip() for a in update.message.text.split(",")
    ]
    update.message.reply_text("Enter *Responsible Person*:")
    return CAPA_RESPONSIBLE


def capa_responsible(update, context):
    context.user_data["capa"]["responsible_person"] = update.message.text.strip()
    update.message.reply_text("Enter *Target Date*:")
    return CAPA_TARGET_DATE


def capa_target_date(update, context):
    context.user_data["capa"]["target_date"] = update.message.text.strip()
    update.message.reply_text("Enter *Effectiveness Criteria*:")
    return CAPA_EFFECTIVENESS_CRITERIA


def capa_effectiveness_criteria(update, context):
    context.user_data["capa"]["effectiveness_criteria"] = update.message.text.strip()
    update.message.reply_text("Enter *Effectiveness Check Plan*:")
    return CAPA_EFFECTIVENESS_PLAN


# ===== FINAL STEP =====
def capa_effectiveness_plan(update, context):
    context.user_data["capa"]["effectiveness_check_plan"] = update.message.text.strip()

    data = CAPAInput(**context.user_data["capa"])
    html = generate_capa_html(data)

    bio = BytesIO(html.encode("utf-8"))
    bio.name = f"{data.capa_id}.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="✅ CAPA Document Generated",
    )

    return ConversationHandler.END


# ===== CONVERSATION HANDLER =====
capa_conv = ConversationHandler(
    entry_points=[
        CommandHandler("capa", start_capa),
        MessageHandler(Filters.regex(r"^🛡 CAPA$"), start_capa),
    ],
    states={
        CAPA_ID: [MessageHandler(Filters.text & ~Filters.command, capa_id)],
        CAPA_DATE: [MessageHandler(Filters.text & ~Filters.command, capa_date)],
        CAPA_BY: [MessageHandler(Filters.text & ~Filters.command, capa_by)],
        CAPA_SOURCE: [MessageHandler(Filters.text & ~Filters.command, capa_source)],
        CAPA_PROBLEM: [MessageHandler(Filters.text & ~Filters.command, capa_problem)],
        CAPA_ROOT_CAUSE: [
            MessageHandler(Filters.text & ~Filters.command, capa_root_cause)
        ],
        CAPA_TOOLS: [MessageHandler(Filters.text & ~Filters.command, capa_tools)],
        CAPA_CONTAINMENT: [
            MessageHandler(Filters.text & ~Filters.command, capa_containment)
        ],
        CAPA_CA: [MessageHandler(Filters.text & ~Filters.command, capa_ca)],
        CAPA_PA: [MessageHandler(Filters.text & ~Filters.command, capa_pa)],
        CAPA_RESPONSIBLE: [
            MessageHandler(Filters.text & ~Filters.command, capa_responsible)
        ],
        CAPA_TARGET_DATE: [
            MessageHandler(Filters.text & ~Filters.command, capa_target_date)
        ],
        CAPA_EFFECTIVENESS_CRITERIA: [
            MessageHandler(
                Filters.text & ~Filters.command, capa_effectiveness_criteria
            )
        ],
        CAPA_EFFECTIVENESS_PLAN: [
            MessageHandler(Filters.text & ~Filters.command, capa_effectiveness_plan)
        ],
    },
    fallbacks=[],
    per_user=True,
)
