# handlers/moa_handler.py

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CommandHandler,
)

from modules.method_of_analysis import MethodOfAnalysisInput, generate_moa_html
from io import BytesIO

# ===== STATES =====
(
    MOA_METHOD_ID,
    MOA_TITLE,
    MOA_NAME,
    MOA_SAMPLE_TYPE,
    MOA_PURPOSE,
    MOA_SCOPE,
    MOA_PRINCIPLE,
    MOA_REFERENCES,
    MOA_REAGENTS,
    MOA_STANDARDS,
    MOA_EQUIPMENT,
    MOA_CHROMA,
    MOA_STD_PREP,
    MOA_SMP_PREP,
    MOA_PROCEDURE,
    MOA_SYSTEM_SUIT,
    MOA_CALC,
    MOA_ACCEPTANCE,
    MOA_VALIDATION,
    MOA_SAFETY,
) = range(20)


# ==========================================================
# ENTRY POINT
# ==========================================================
def start_moa(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🧪 *Method of Analysis – MOA*\n\n"
        "Let's start creating a Method of Analysis.\n"
        "Send the *Method ID* (e.g., MOA-API-001):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )

    context.user_data["moa"] = {}
    return MOA_METHOD_ID


# ==========================================================
# STATES HANDLERS
# ==========================================================
def moa_method_id(update, context):
    context.user_data["moa"]["method_id"] = update.message.text.strip()
    update.message.reply_text("Enter *Method Title*:")
    return MOA_TITLE


def moa_title(update, context):
    context.user_data["moa"]["method_title"] = update.message.text.strip()
    update.message.reply_text("Enter *Product / Material Name*:")
    return MOA_NAME


def moa_name(update, context):
    context.user_data["moa"]["product_or_material_name"] = update.message.text.strip()
    update.message.reply_text("Enter *Sample Type* (API / FP / RM / PM):")
    return MOA_SAMPLE_TYPE


def moa_sample(update, context):
    context.user_data["moa"]["sample_type"] = update.message.text.strip()
    update.message.reply_text("Enter *Purpose*:")
    return MOA_PURPOSE


def moa_purpose(update, context):
    context.user_data["moa"]["purpose"] = update.message.text.strip()
    update.message.reply_text("Enter *Scope*:")
    return MOA_SCOPE


def moa_scope(update, context):
    context.user_data["moa"]["scope"] = update.message.text.strip()
    update.message.reply_text("Enter *Principle*:")
    return MOA_PRINCIPLE


def moa_principle(update, context):
    context.user_data["moa"]["principle"] = update.message.text.strip()
    update.message.reply_text(
        "Enter *References* (comma-separated):\nExample: USP, IP, In-house spec"
    )
    return MOA_REFERENCES


def moa_references(update, context):
    refs = [r.strip() for r in update.message.text.split(",")]
    context.user_data["moa"]["references"] = refs
    update.message.reply_text("Enter *Reagents* (comma separated):")
    return MOA_REAGENTS


def moa_reagents(update, context):
    reag = [r.strip() for r in update.message.text.split(",")]
    context.user_data["moa"]["reagents"] = reag
    update.message.reply_text("Enter *Standards* (comma separated):")
    return MOA_STANDARDS


def moa_standards(update, context):
    stds = [s.strip() for s in update.message.text.split(",")]
    context.user_data["moa"]["standards"] = stds
    update.message.reply_text("Enter *Equipment / Instruments* (comma separated):")
    return MOA_EQUIPMENT


def moa_equipment(update, context):
    eq = [e.strip() for e in update.message.text.split(",")]
    context.user_data["moa"]["equipment"] = eq
    update.message.reply_text("Enter *Chromatographic / Instrumental Conditions*:")
    return MOA_CHROMA


def moa_chroma(update, context):
    context.user_data["moa"]["chromatographic_conditions"] = update.message.text.strip()
    update.message.reply_text("Enter *Standard Preparation*:")
    return MOA_STD_PREP


def moa_std_prep(update, context):
    context.user_data["moa"]["standard_preparation"] = update.message.text.strip()
    update.message.reply_text("Enter *Sample Preparation*:")
    return MOA_SMP_PREP


def moa_smp_prep(update, context):
    context.user_data["moa"]["sample_preparation"] = update.message.text.strip()
    update.message.reply_text("Enter *Procedure*:")
    return MOA_PROCEDURE


def moa_procedure(update, context):
    context.user_data["moa"]["procedure"] = update.message.text.strip()
    update.message.reply_text("Enter *System Suitability*:")
    return MOA_SYSTEM_SUIT


def moa_system(update, context):
    context.user_data["moa"]["system_suitability"] = update.message.text.strip()
    update.message.reply_text("Enter *Calculation*:")
    return MOA_CALC


def moa_calc(update, context):
    context.user_data["moa"]["calculation"] = update.message.text.strip()
    update.message.reply_text("Enter *Acceptance Criteria*:")
    return MOA_ACCEPTANCE


def moa_accept(update, context):
    context.user_data["moa"]["acceptance_criteria"] = update.message.text.strip()
    update.message.reply_text("Enter *Validation Status*:")
    return MOA_VALIDATION


def moa_validation(update, context):
    context.user_data["moa"]["validation_status"] = update.message.text.strip()
    update.message.reply_text("Enter *Safety Precautions*:")
    return MOA_SAFETY


# ==========================================================
# FINAL STEP
# ==========================================================
def moa_safety(update, context):
    context.user_data["moa"]["safety_precautions"] = update.message.text.strip()

    data = MethodOfAnalysisInput(**context.user_data["moa"])
    html = generate_moa_html(data)

    bio = BytesIO(html.encode("utf-8"))
    bio.name = f"{data.method_id}.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="✅ Method of Analysis Generated",
    )

    return ConversationHandler.END


# ==========================================================
# CONVERSATION HANDLER (STRONG ENTRY)
# ==========================================================
moa_conv = ConversationHandler(
    entry_points=[
        CommandHandler("moa", start_moa),
        MessageHandler(Filters.regex(r"(?i)(moa|method.*analysis)"), start_moa),
    ],
    states={
        MOA_METHOD_ID: [MessageHandler(Filters.text & ~Filters.command, moa_method_id)],
        MOA_TITLE: [MessageHandler(Filters.text & ~Filters.command, moa_title)],
        MOA_NAME: [MessageHandler(Filters.text & ~Filters.command, moa_name)],
        MOA_SAMPLE_TYPE: [MessageHandler(Filters.text & ~Filters.command, moa_sample)],
        MOA_PURPOSE: [MessageHandler(Filters.text & ~Filters.command, moa_purpose)],
        MOA_SCOPE: [MessageHandler(Filters.text & ~Filters.command, moa_scope)],
        MOA_PRINCIPLE: [MessageHandler(Filters.text & ~Filters.command, moa_principle)],
        MOA_REFERENCES: [MessageHandler(Filters.text & ~Filters.command, moa_references)],
        MOA_REAGENTS: [MessageHandler(Filters.text & ~Filters.command, moa_reagents)],
        MOA_STANDARDS: [MessageHandler(Filters.text & ~Filters.command, moa_standards)],
        MOA_EQUIPMENT: [MessageHandler(Filters.text & ~Filters.command, moa_equipment)],
        MOA_CHROMA: [MessageHandler(Filters.text & ~Filters.command, moa_chroma)],
        MOA_STD_PREP: [MessageHandler(Filters.text & ~Filters.command, moa_std_prep)],
        MOA_SMP_PREP: [MessageHandler(Filters.text & ~Filters.command, moa_smp_prep)],
        MOA_PROCEDURE: [MessageHandler(Filters.text & ~Filters.command, moa_procedure)],
        MOA_SYSTEM_SUIT: [MessageHandler(Filters.text & ~Filters.command, moa_system)],
        MOA_CALC: [MessageHandler(Filters.text & ~Filters.command, moa_calc)],
        MOA_ACCEPTANCE: [MessageHandler(Filters.text & ~Filters.command, moa_accept)],
        MOA_VALIDATION: [MessageHandler(Filters.text & ~Filters.command, moa_validation)],
        MOA_SAFETY: [MessageHandler(Filters.text & ~Filters.command, moa_safety)],
    },
    fallbacks=[],
    per_user=True,
)
