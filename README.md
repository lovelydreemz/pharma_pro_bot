
# Pharma Pro Telegram Bot

This project is a 24x7 pharma assistant Telegram bot with:

- Pharma Q&A using your own PDF reference library
- SOP Generator mode
- Regulatory Alerts mode
- Voice input mode (plug your own transcription API)
- Train-your-bot by uploading PDFs (admin approval workflow)
- Subscription system (150 free messages, then ₹100 lifetime via Paytm / manual verification)

## Structure

- `bot.py` – main Telegram bot
- `config.py` – all configuration (tokens, UPI, AI settings)
- `database.py` – SQLite database + FTS search
- `subscription.py` – free quota + lifetime Pro logic
- `ai_engine.py` – connects to your LLM (DeepSeek, OpenAI, etc.)
- `pdf_ingest.py` – PDF reading & chunking
- `pdf_approval.py` – pending → approved workflow
- `regulatory_alerts.py` – alerts storage & listing
- `voice_handler.py` – placeholder for voice-to-text integration
- `requirements.txt` – Python dependencies

Folders:
- `data/` – SQLite DB file
- `books/` – approved PDFs
- `pending_pdfs/` – PDFs waiting for admin approval
- `alerts/` – optional static files for alerts

## Quick Start

1. Create a new bot via BotFather and copy the token.
2. Edit `config.py`:
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_IDS` – your Telegram numeric user id(s)
   - `PAYTM_UPI_ID`, `PAYTM_QR_LINK`
   - `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL_NAME`
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the bot:

   ```bash
   python bot.py
   ```

5. Open Telegram, search your bot and send `/start`.

## Payment Flow (Manual Verification)

- User gets 150 free messages.
- After that, bot shows UPI details for paying ₹100 Lifetime Pro.
- User sends payment screenshot / reference number.
- Admin verifies payment and runs:

  ```text
  /activate_user <chat_id>
  ```

- Bot updates DB and notifies user that Lifetime Pro is active.

## PDF Training Flow

- User chooses "📤 Upload PDF" in menu or `/uploadpdf`.
- User sends PDF document.
- Bot saves it to `pending_pdfs/` and records an entry with status `pending`.
- Admin runs `/pending_pdfs` to see list and `/approve_pdf <id>` to approve.
- On approval, system:
  - Moves PDF to `books/`
  - Extracts text and indexes into SQLite FTS
  - Marks document as `approved`

All Q&A will then use that approved content as context.

## Voice Input

- User chooses "🎙 Voice Q&A" or `/voice`.
- Sends voice message.
- `voice_handler.transcribe_voice()` should call your actual transcription API.
- The text is then sent to the Answer Engine just like a normal question.

## Notes

- This code is a starting point and can be extended with:
  - More granular roles (QA, QC, RA, Production, Engineering)
  - Detailed logging and analytics
  - Web dashboard for admins
