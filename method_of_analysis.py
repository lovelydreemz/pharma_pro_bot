# handlers/moa_handler.py

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

from method_of_analysis import MethodOfAnalysisInput, generate_moa_html

# Conversation states
(
    MOA_METHOD_ID,
    MOA_TITLE,
    MOA_PRODUCT,
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
    MOA_SAMPLE_PREP,
    MOA_PROCEDURE,
    MOA_SYSTEM_SUIT,
    MOA_CALC,
    MOA_ACCEPT,
    MOA_VALIDATION,
    MOA_SAFETY,
) = range(20)


# --------------------------------------------------------------------
# ENTRY POINT
# --------------------------------------------------------------------
def start_moa(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🧪 *Method of Analysis Builder*\n\n"
        "Let's create a Method of Analysis.\n"
        "Step 1️⃣: Send *Method ID* (e.g. MOA-API-001)",
        parse_mode="Markdown",
    )
    return MOA_METHOD_ID


# --------------------------------------------------------------------
# STEP-BY-STEP QUESTIONS
# --------------------------------------------------------------------
def moa_method_id(update, context):
    context.user_data["moa"] = {}
    context.user_data["moa"]["method_id"] = update.message.text.strip()

    update.message.reply_text("Step 2️⃣: Send *Method Title*")
    return MOA_TITLE


def moa_title(update, context):
    context.user_data["moa"]["method_title"] = update.message.text.strip()
    update.message.reply_text("Step 3️⃣: Send *Product / Material Name*")
    return MOA_PRODUCT


def moa_product(update, context):
    context.user_data["moa"]["product_or_material_name"] = update.message.text.strip()
    update.message.reply_text(
        "Step 4️⃣: Send *Sample Type* (API / Finished Product / Raw Material / Packing Material)"
    )
    return MOA_SAMPLE_TYPE


def moa_sample_type(update, context):
    context.user_data["moa"]["sample_type"] = update.message.text.strip()
    update.message.reply_text("Step 5️⃣: Send *Purpose* (Assay / Impurity / etc.)")
    return MOA_PURPOSE


def moa_purpose(update, context):
    context.user_data["moa"]["purpose"] = update.message.text.strip()
    update.message.reply_text("Step 6️⃣: Send *Scope*")
    return MOA_SCOPE


def moa_scope(update, context):
    context.user_data["moa"]["scope"] = update.message.text.strip()
    update.message.reply_text("Step 7️⃣: Send *Principle*")
    return MOA_PRINCIPLE


def moa_principle(update, context):
    context.user_data["moa"]["principle"] = update.message.text.strip()
    update.message.reply_text(
        "Step 8️⃣: Send *References* (comma separated)\nExample: USP, Internal Spec XYZ"
    )
    return MOA_REFERENCES


def moa_references(update, context):
    txt = update.message.text.strip()
    context.user_data["moa"]["references"] = [r.strip() for r in txt.split(",")]
    update.message.reply_text("Step 9️⃣: Send *Reagents* (comma separated)")
    return MOA_REAGENTS


def moa_reagents(update, context):
    txt = update.message.text.strip()
    context.user_data["moa"]["reagents"] = [r.strip() for r in txt.split(",")]
    update.message.reply_text("Step 🔟: Send *Standards* (comma separated)")
    return MOA_STANDARDS


def moa_standards(update, context):
    txt = update.message.text.strip()
    context.user_data["moa"]["standards"] = [r.strip() for r in txt.split(",")]
    update.message.reply_text("Step 1️⃣1️⃣: Send *Equipment / Apparatus* (comma separated)")
    return MOA_EQUIPMENT


def moa_equipment(update, context):
    txt = update.message.text.strip()
    context.user_data["moa"]["equipment"] = [r.strip() for r in txt.split(",")]
    update.message.reply_text("Step 1️⃣2️⃣: Send *Chromatographic / Instrumental Conditions*")
    return MOA_CHROMA


def moa_chroma(update, context):
    context.user_data["moa"]["chromatographic_conditions"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣3️⃣: Send *Standard Preparation*")
    return MOA_STD_PREP


def moa_std_prep(update, context):
    context.user_data["moa"]["standard_preparation"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣4️⃣: Send *Sample Preparation*")
    return MOA_SAMPLE_PREP


def moa_sample_prep(update, context):
    context.user_data["moa"]["sample_preparation"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣5️⃣: Send *Procedure*")
    return MOA_PROCEDURE


def moa_procedure(update, context):
    context.user_data["moa"]["procedure"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣6️⃣: Send *System Suitability*")
    return MOA_SYSTEM_SUIT


def moa_system_suit(update, context):
    context.user_data["moa"]["system_suitability"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣7️⃣: Send *Calculations*")
    return MOA_CALC


def moa_calc(update, context):
    context.user_data["moa"]["calculation"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣8️⃣: Send *Acceptance Criteria*")
    return MOA_ACCEPT


def moa_accept(update, context):
    context.user_data["moa"]["acceptance_criteria"] = update.message.text.strip()
    update.message.reply_text("Step 1️⃣9️⃣: Send *Validation Status*")
    return MOA_VALIDATION


def moa_validation(update, context):
    context.user_data["moa"]["validation_status"] = update.message.text.strip()
    update.message.reply_text("Last Step 2️⃣0️⃣: Send *Safety & Precautions*")
    return MOA_SAFETY


# --------------------------------------------------------------------
# FINAL STEP — GENERATE HTML
# --------------------------------------------------------------------
def moa_safety(update, context):
    context.user_data["moa"]["safety_precautions"] = update.message.text.strip()

    # Build dataclass
    info = MethodOfAnalysisInput(**context.user_data["moa"])

    html = generate_moa_html(info)

    bio = BytesIO(html.encode("utf-8"))
    bio.name = f"{info.method_id}_MOA.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="📄 *Your Method of Analysis is ready!*",
        parse_mode="Markdown",
    )

    return ConversationHandler.END


# --------------------------------------------------------------------
# CANCEL HANDLER
# --------------------------------------------------------------------
def cancel_moa(update, context):
    update.message.reply_text("MOA creation cancelled.")
    return ConversationHandler.END


# --------------------------------------------------------------------
# CONVERSATION HANDLER
# --------------------------------------------------------------------
moa_conv = ConversationHandler(
    entry_points=[
        CommandHandler("moa", start_moa),
        MessageHandler(Filters.regex("^🧪 Method of Analysis$"), start_moa),
    ],
    states={
        MOA_METHOD_ID: [MessageHandler(Filters.text & ~Filters.command, moa_method_id)],
        MOA_TITLE: [MessageHandler(Filters.text & ~Filters.command, moa_title)],
        MOA_PRODUCT: [MessageHandler(Filters.text & ~Filters.command, moa_product)],
        MOA_SAMPLE_TYPE: [MessageHandler(Filters.text & ~Filters.command, moa_sample_type)],
        MOA_PURPOSE: [MessageHandler(Filters.text & ~Filters.command, moa_purpose)],
        MOA_SCOPE: [MessageHandler(Filters.text & ~Filters.command, moa_scope)],
        MOA_PRINCIPLE: [MessageHandler(Filters.text & ~Filters.command, moa_principle)],
        MOA_REFERENCES: [MessageHandler(Filters.text & ~Filters.command, moa_references)],
        MOA_REAGENTS: [MessageHandler(Filters.text & ~Filters.command, moa_reagents)],
        MOA_STANDARDS: [MessageHandler(Filters.text & ~Filters.command, moa_standards)],
        MOA_EQUIPMENT: [MessageHandler(Filters.text & ~Filters.command, moa_equipment)],
        MOA_CHROMA: [MessageHandler(Filters.text & ~Filters.command, moa_chroma)],
        MOA_STD_PREP: [MessageHandler(Filters.text & ~Filters.command, moa_std_prep)],
        MOA_SAMPLE_PREP: [MessageHandler(Filters.text & ~Filters.command, moa_sample_prep)],
        MOA_PROCEDURE: [MessageHandler(Filters.text & ~Filters.command, moa_procedure)],
        MOA_SYSTEM_SUIT: [MessageHandler(Filters.text & ~Filters.command, moa_system_suit)],
        MOA_CALC: [MessageHandler(Filters.text & ~Filters.command, moa_calc)],
        MOA_ACCEPT: [MessageHandler(Filters.text & ~Filters.command, moa_accept)],
        MOA_VALIDATION: [MessageHandler(Filters.text & ~Filters.command, moa_validation)],
        MOA_SAFETY: [MessageHandler(Filters.text & ~Filters.command, moa_safety)],
    },
    fallbacks=[CommandHandler("cancel", cancel_moa)],
)

