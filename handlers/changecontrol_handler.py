# handlers/changecontrol_handler.py

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)
from io import BytesIO

from modules.change_control import ChangeControlInput, generate_cc_html


# ===== STATES =====
(
    CC_ID,
    CC_DATE,
    CC_INITIATOR,
    CC_DEPT,
    CC_TYPE,
    CC_PRIORITY,
    CC_PROPOSAL,
    CC_JUSTIFICATION,
    CC_PRODUCT,
    CC_BATCHES,
    CC_RISK,
    CC_IMPACT_VALIDATION,
    CC_IMPACT_QMS,
    CC_IMPACT_REGULATORY,
    CC_ACTION_PLAN,
    CC_RESPONSIBLE,
    CC_TARGET_DATE,
    CC_APPROVAL,
) = range(18)


# ==========================================================
# ENTRY POINT
# ==========================================================
def start_cc(update: Update, context: CallbackContext):
    update.message.reply_text(
        "⚙ *Change Control (CC) Generator*\n\n"
        "Let's start your Change Control request.\n"
        "Send *CC ID* (e.g., CC-001):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data["cc"] = {}
    return CC_ID


# ==========================================================
# QUESTION FLOW
# ==========================================================
def cc_id(update, context):
    context.user_data["cc"]["cc_id"] = update.message.text.strip()
    update.message.reply_text("Enter *Date Initiated* (DD-MM-YYYY):")
    return CC_DATE


def cc_date(update, context):
    context.user_data["cc"]["date_initiated"] = update.message.text.strip()
    update.message.reply_text("Enter *Initiator Name*:")
    return CC_INITIATOR


def cc_initiator(update, context):
    context.user_data["cc"]["initiator"] = update.message.text.strip()
    update.message.reply_text("Enter *Department* initiating change:")
    return CC_DEPT


def cc_dept(update, context):
    context.user_data["cc"]["department"] = update.message.text.strip()
    update.message.reply_text(
        "Enter *Type of Change*:\n"
        "• Document Change\n"
        "• Equipment Change\n"
        "• Material Change\n"
        "• Process Change\n"
        "• Facility Change\n"
        "• Specification Change\n"
        "• Packaging Change"
    )
    return CC_TYPE


def cc_type(update, context):
    context.user_data["cc"]["change_type"] = update.message.text.strip()
    update.message.reply_text("Enter *Priority*: Critical / Major / Minor")
    return CC_PRIORITY


def cc_priority(update, context):
    context.user_data["cc"]["priority"] = update.message.text.strip()
    update.message.reply_text("Describe the *Proposed Change*:")
    return CC_PROPOSAL


def cc_proposal(update, context):
    context.user_data["cc"]["proposed_change"] = update.message.text.strip()
    update.message.reply_text("Enter *Justification / Reason* for the change:")
    return CC_JUSTIFICATION


def cc_justification(update, context):
    context.user_data["cc"]["justification"] = update.message.text.strip()
    update.message.reply_text("List *Products* impacted (comma separated):")
    return CC_PRODUCT


def cc_product(update, context):
    products = [p.strip() for p in update.message.text.split(",")]
    context.user_data["cc"]["products_impacted"] = products
    update.message.reply_text("List *Batches* impacted (comma separated or NA):")
    return CC_BATCHES


def cc_batches(update, context):
    batches = [b.strip() for b in update.message.text.split(",")]
    context.user_data["cc"]["batches_impacted"] = batches
    update.message.reply_text("Enter *Risk Assessment Summary*:")
    return CC_RISK


def cc_risk(update, context):
    context.user_data["cc"]["risk_assessment"] = update.message.text.strip()
    update.message.reply_text("Impact on *Validation* (Yes/No + details):")
    return CC_IMPACT_VALIDATION


def cc_impact_validation(update, context):
    context.user_data["cc"]["impact_on_validation"] = update.message.text.strip()
    update.message.reply_text("Impact on *QMS / SOPs / Documents*:")
    return CC_IMPACT_QMS


def cc_impact_qms(update, context):
    context.user_data["cc"]["impact_on_qms"] = update.message.text.strip()
    update.message.reply_text("Impact on *Regulatory Filing / Approvals*:")
    return CC_IMPACT_REGULATORY


def cc_impact_regulatory(update, context):
    context.user_data["cc"]["impact_on_regulatory"] = update.message.text.strip()
    update.message.reply_text("Enter *Action Plan* (comma separated steps):")
    return CC_ACTION_PLAN


def cc_action_plan(update, context):
    actions = [a.strip() for a in update.message.text.split(",")]
    context.user_data["cc"]["action_plan"] = actions
    update.message.reply_text("Enter *Responsible Person(s)*:")
    return CC_RESPONSIBLE


def cc_responsible(update, context):
    context.user_data["cc"]["responsible_person"] = update.message.text.strip()
    update.message.reply_text("Enter *Target Completion Date*:")
    return CC_TARGET_DATE


def cc_target_date(update, context):
    context.user_data["cc"]["target_date"] = update.message.text.strip()
    update.message.reply_text("Enter *Approver Name / Designation*:")
    return CC_APPROVAL


# ==========================================================
# FINAL STEP
# ==========================================================
def cc_approval(update, context):
    context.user_data["cc"]["approver"] = update.message.text.strip()

    data = ChangeControlInput(**context.user_data["cc"])
    html = generate_cc_html(data)

    bio = BytesIO(html.encode("utf-8"))
    bio.name = f"{data.cc_id}.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="✅ Change Control Document Generated",
    )

    return ConversationHandler.END


# ==========================================================
# CLEAN ENTRY POINTS (Regex + /command)
# ==========================================================
cc_conv = ConversationHandler(
    entry_points=[
        CommandHandler("cc", start_cc),
        MessageHandler(Filters.regex(r"(?i)(cc|change control|start cc)"), start_cc),
    ],
    states={
        CC_ID: [MessageHandler(Filters.text & ~Filters.command, cc_id)],
        CC_DATE: [MessageHandler(Filters.text & ~Filters.command, cc_date)],
        CC_INITIATOR: [MessageHandler(Filters.text & ~Filters.command, cc_initiator)],
        CC_DEPT: [MessageHandler(Filters.text & ~Filters.command, cc_dept)],
        CC_TYPE: [MessageHandler(Filters.text & ~Filters.command, cc_type)],
        CC_PRIORITY: [MessageHandler(Filters.text & ~Filters.command, cc_priority)],
        CC_PROPOSAL: [MessageHandler(Filters.text & ~Filters.command, cc_proposal)],
        CC_JUSTIFICATION: [MessageHandler(Filters.text & ~Filters.command, cc_justification)],
        CC_PRODUCT: [MessageHandler(Filters.text & ~Filters.command, cc_product)],
        CC_BATCHES: [MessageHandler(Filters.text & ~Filters.command, cc_batches)],
        CC_RISK: [MessageHandler(Filters.text & ~Filters.command, cc_risk)],
        CC_IMPACT_VALIDATION: [MessageHandler(Filters.text & ~Filters.command, cc_impact_validation)],
        CC_IMPACT_QMS: [MessageHandler(Filters.text & ~Filters.command, cc_impact_qms)],
        CC_IMPACT_REGULATORY: [MessageHandler(Filters.text & ~Filters.command, cc_impact_regulatory)],
        CC_ACTION_PLAN: [MessageHandler(Filters.text & ~Filters.command, cc_action_plan)],
        CC_RESPONSIBLE: [MessageHandler(Filters.text & ~Filters.command, cc_responsible)],
        CC_TARGET_DATE: [MessageHandler(Filters.text & ~Filters.command, cc_target_date)],
        CC_APPROVAL: [MessageHandler(Filters.text & ~Filters.command, cc_approval)],
    },
    fallbacks=[],
    per_user=True,
)
