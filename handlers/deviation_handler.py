# handlers/deviation_handler.py

from io import BytesIO

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CommandHandler,
)

from modules.deviation import DeviationInput, generate_deviation_html

# ===== STATES =====
(
    DEV_ID,
    DEV_DATE,
    DEV_BY,
    DEV_DEPT,
    DEV_PRODUCT,
    DEV_BATCH,
    DEV_MATERIAL,
    DEV_TYPE,
    DEV_CATEGORY,
    DEV_DATE_OCCUR,
    DEV_LOCATION,
    DEV_DESC,
    DEV_IMMEDIATE,
    DEV_INVESTIGATION,
    DEV_ROOT_CAUSE,
    DEV_TOOLS,
    DEV_RISK,
    DEV_IMPACT_PRODUCT,
    DEV_IMPACT_COMPLIANCE,
    DEV_IMPACT_TIME,
    DEV_CA,
    DEV_PA,
    DEV_RESPONSIBLE,
    DEV_TARGET_DATE,
    DEV_EFFECTIVENESS,
) = range(25)


# ===== ENTRY COMMAND =====
def start_deviation(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📄 *Deviation Report Generator*\n\n"
        "Let's begin.\n"
        "Enter *Deviation ID* (e.g., DEV-001):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data["dev"] = {}
    return DEV_ID


# ===== QUESTION FLOW =====
def dev_id(update, context):
    context.user_data["dev"]["deviation_id"] = update.message.text.strip()
    update.message.reply_text("Enter *Date Reported* (DD-MM-YYYY):")
    return DEV_DATE


def dev_date(update, context):
    context.user_data["dev"]["date_reported"] = update.message.text.strip()
    update.message.reply_text("Enter *Reported By*:")
    return DEV_BY


def dev_by(update, context):
    context.user_data["dev"]["reported_by"] = update.message.text.strip()
    update.message.reply_text("Enter *Department*:")
    return DEV_DEPT


def dev_dept(update, context):
    context.user_data["dev"]["department"] = update.message.text.strip()
    update.message.reply_text("Enter *Product Name* (or NA):")
    return DEV_PRODUCT


def dev_product(update, context):
    context.user_data["dev"]["product_name"] = update.message.text.strip()
    update.message.reply_text("Enter *Batch No.* (or NA):")
    return DEV_BATCH


def dev_batch(update, context):
    context.user_data["dev"]["batch_no"] = update.message.text.strip()
    update.message.reply_text("Enter *Material Name* (if applicable):")
    return DEV_MATERIAL


def dev_material(update, context):
    context.user_data["dev"]["material_name"] = update.message.text.strip()
    update.message.reply_text("Enter *Deviation Type*: Planned / Unplanned")
    return DEV_TYPE


def dev_type(update, context):
    context.user_data["dev"]["deviation_type"] = update.message.text.strip()
    update.message.reply_text("Enter *Deviation Category*: Critical / Major / Minor")
    return DEV_CATEGORY


def dev_category(update, context):
    context.user_data["dev"]["deviation_category"] = update.message.text.strip()
    update.message.reply_text("Enter *Date of Occurrence*:")
    return DEV_DATE_OCCUR


def dev_date_occur(update, context):
    context.user_data["dev"]["date_of_occurrence"] = update.message.text.strip()
    update.message.reply_text("Enter *Location* of deviation:")
    return DEV_LOCATION


def dev_location(update, context):
    context.user_data["dev"]["location"] = update.message.text.strip()
    update.message.reply_text("Describe the *Deviation* in detail:")
    return DEV_DESC


def dev_desc(update, context):
    context.user_data["dev"]["description"] = update.message.text.strip()
    update.message.reply_text("Enter *Immediate Corrective Action*:")
    return DEV_IMMEDIATE


def dev_immediate(update, context):
    context.user_data["dev"]["immediate_action"] = update.message.text.strip()
    update.message.reply_text("Enter *Investigation Summary*:")
    return DEV_INVESTIGATION


def dev_investigation(update, context):
    context.user_data["dev"]["investigation_summary"] = update.message.text.strip()
    update.message.reply_text("Enter *Root Cause*:")
    return DEV_ROOT_CAUSE


def dev_root_cause(update, context):
    context.user_data["dev"]["root_cause"] = update.message.text.strip()
    update.message.reply_text("Enter *Tools Used* (e.g. 5-Why, Fishbone):")
    return DEV_TOOLS


def dev_tools(update, context):
    tools = [t.strip() for t in update.message.text.split(",")]
    context.user_data["dev"]["selected_tools"] = tools
    update.message.reply_text("Enter *Risk Assessment*:")
    return DEV_RISK


def dev_risk(update, context):
    context.user_data["dev"]["risk_assessment"] = update.message.text.strip()
    update.message.reply_text("Impact on *Product / Patient / Quality*:")
    return DEV_IMPACT_PRODUCT


def dev_impact_product(update, context):
    context.user_data["dev"]["impact_on_product"] = update.message.text.strip()
    update.message.reply_text("Impact on *Compliance / Regulatory*:")
    return DEV_IMPACT_COMPLIANCE


def dev_impact_compliance(update, context):
    context.user_data["dev"]["impact_on_compliance"] = update.message.text.strip()
    update.message.reply_text("Impact on *Timeline / Cost*:")
    return DEV_IMPACT_TIME


def dev_impact_time(update, context):
    context.user_data["dev"]["impact_on_timeline_cost"] = update.message.text.strip()
    update.message.reply_text("Enter *Corrective Actions* (comma separated):")
    return DEV_CA


def dev_ca(update, context):
    context.user_data["dev"]["corrective_actions"] = [
        c.strip() for c in update.message.text.split(",")
    ]
    update.message.reply_text("Enter *Preventive Actions* (comma separated):")
    return DEV_PA


def dev_pa(update, context):
    context.user_data["dev"]["preventive_actions"] = [
        p.strip() for p in update.message.text.split(",")
    ]
    update.message.reply_text("Enter *Responsible Person*:")
    return DEV_RESPONSIBLE


def dev_responsible(update, context):
    context.user_data["dev"]["responsible_person"] = update.message.text.strip()
    update.message.reply_text("Enter *Target Completion Date*:")
    return DEV_TARGET_DATE


def dev_target_date(update, context):
    context.user_data["dev"]["target_completion_date"] = update.message.text.strip()
    update.message.reply_text("Enter *Effectiveness Check Plan*:")
    return DEV_EFFECTIVENESS


def dev_effectiveness(update, context):
    context.user_data["dev"]["effectiveness_check_plan"] = update.message.text.strip()

    data = DeviationInput(**context.user_data["dev"])
    html = generate_deviation_html(data)

    bio = BytesIO(html.encode("utf-8"))
    bio.name = f"{data.deviation_id}.html"

    update.message.reply_document(
        document=bio,
        filename=bio.name,
        caption="✅ Deviation Report Generated",
    )

    return ConversationHandler.END


# ===== CONVERSATION HANDLER =====
deviation_conv = ConversationHandler(
    entry_points=[
        CommandHandler("deviation", start_deviation),
        # Triggered by menu button "📄 Deviation"
        MessageHandler(Filters.regex(r"^📄 Deviation$"), start_deviation),
    ],
    states={
        DEV_ID: [MessageHandler(Filters.text & ~Filters.command, dev_id)],
        DEV_DATE: [MessageHandler(Filters.text & ~Filters.command, dev_date)],
        DEV_BY: [MessageHandler(Filters.text & ~Filters.command, dev_by)],
        DEV_DEPT: [MessageHandler(Filters.text & ~Filters.command, dev_dept)],
        DEV_PRODUCT: [MessageHandler(Filters.text & ~Filters.command, dev_product)],
        DEV_BATCH: [MessageHandler(Filters.text & ~Filters.command, dev_batch)],
        DEV_MATERIAL: [MessageHandler(Filters.text & ~Filters.command, dev_material)],
        DEV_TYPE: [MessageHandler(Filters.text & ~Filters.command, dev_type)],
        DEV_CATEGORY: [MessageHandler(Filters.text & ~Filters.command, dev_category)],
        DEV_DATE_OCCUR: [MessageHandler(Filters.text & ~Filters.command, dev_date_occur)],
        DEV_LOCATION: [MessageHandler(Filters.text & ~Filters.command, dev_location)],
        DEV_DESC: [MessageHandler(Filters.text & ~Filters.command, dev_desc)],
        DEV_IMMEDIATE: [MessageHandler(Filters.text & ~Filters.command, dev_immediate)],
        DEV_INVESTIGATION: [MessageHandler(Filters.text & ~Filters.command, dev_investigation)],
        DEV_ROOT_CAUSE: [MessageHandler(Filters.text & ~Filters.command, dev_root_cause)],
        DEV_TOOLS: [MessageHandler(Filters.text & ~Filters.command, dev_tools)],
        DEV_RISK: [MessageHandler(Filters.text & ~Filters.command, dev_risk)],
        DEV_IMPACT_PRODUCT: [MessageHandler(Filters.text & ~Filters.command, dev_impact_product)],
        DEV_IMPACT_COMPLIANCE: [MessageHandler(Filters.text & ~Filters.command, dev_impact_compliance)],
        DEV_IMPACT_TIME: [MessageHandler(Filters.text & ~Filters.command, dev_impact_time)],
        DEV_CA: [MessageHandler(Filters.text & ~Filters.command, dev_ca)],
        DEV_PA: [MessageHandler(Filters.text & ~Filters.command, dev_pa)],
        DEV_RESPONSIBLE: [MessageHandler(Filters.text & ~Filters.command, dev_responsible)],
        DEV_TARGET_DATE: [MessageHandler(Filters.text & ~Filters.command, dev_target_date)],
        DEV_EFFECTIVENESS: [MessageHandler(Filters.text & ~Filters.command, dev_effectiveness)],
    },
    fallbacks=[],
    per_user=True,
)
