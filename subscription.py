from typing import Tuple
from database import get_or_create_user, update_user_messages
from config import FREE_MESSAGES, PREMIUM_PRICE_INR, PAYMENT_INSTRUCTIONS


def ensure_user(chat_id: int, username: str, full_name: str):
    """Creates or fetches user from DB."""
    return get_or_create_user(chat_id, username, full_name)


def can_user_ask(user_row) -> Tuple[bool, str]:
    """
    Returns:
        (allowed: bool, message: str)
    """
    # Premium users = unlimited
    if user_row["is_premium"]:
        return True, ""

    # Free messages remain
    if user_row["free_messages"] > 0:
        return True, ""

    # No free messages left → send manual payment instructions
    msg = (
        "🚫 *Your free message limit is over.*\n\n"
        f"Upgrade to *Lifetime Pro* for just ₹{PREMIUM_PRICE_INR}.\n\n"
        f"{PAYMENT_INSTRUCTIONS}\n"
        "After the payment, upload your payment screenshot here.\n"
        "Admin will verify & activate your lifetime access. 🔓"
    )

    return False, msg


def consume_message(user_row):
    """Reduces free message count unless premium."""
    if user_row["is_premium"]:
        return

    if user_row["free_messages"] > 0:
        update_user_messages(user_row["id"], -1)


def subscription_status_text(user_row) -> str:
    """Human-readable subscription info."""
    if user_row["is_premium"]:
        return "🌟 *You are a Lifetime Pro user!* Unlimited access is active. 🔓"

    return (
        f"📊 *Subscription Status: Free User*\n"
        f"Remaining free messages: *{user_row['free_messages']}*\n\n"
        "To unlock unlimited access:\n"
        f"💳 Pay: ₹{PREMIUM_PRICE_INR}\n\n"
        f"{PAYMENT_INSTRUCTIONS}\n"
        "After the payment, upload your screenshot.\n"
        "Admin will activate your lifetime plan."
    )
