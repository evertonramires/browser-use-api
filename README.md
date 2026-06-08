# Browser-Use API (Telegram Integrated)

An autonomous browser automation service that can execute complex tasks on the web and communicate directly with you via Telegram. Built on top of the powerful [browser-use](https://github.com/browser-use/browser-use) framework.

## Features

- **Autonomous Agent**: Tell the agent what you want to do, and it will navigate, click, extract, and solve the task.
- **Telegram Native**: Send your tasks as simple Telegram messages and get status updates and results straight to your chat.
- **Human-in-the-Loop (HITL)**: If the agent gets stuck or encounters a CAPTCHA/2FA, it will pause and message you on Telegram to ask for help!
- **Screenshots on Demand**: Ask the agent to send you a screenshot of what it's currently seeing, and it will beam the image right to your phone.

---

## Getting Started

This project relies on `uv` for fast Python dependency management.

### 1. Prerequisites

Make sure you have `uv` installed.
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Installation

Clone the repository and install the dependencies.
```bash
git clone https://github.com/evertonramires/browser-use-api.git
cd browser-use-api

# Create the virtual environment and install dependencies
uv venv
uv sync
```

### 3. Configuration

Copy the example environment file and configure your keys.
```bash
cp .env.example .env
```

Open `.env` and configure the following essential variables:

```env
# Required for the LLM driving the agent
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ENDPOINT=https://api.openai.com/v1  # Optional: For proxying or alternative providers

# Required for Telegram Integration
ENABLE_TELEGRAM=true
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_personal_chat_id_here
```

*(You can get a Telegram Bot Token by messaging `@BotFather` on Telegram. To get your Chat ID, message `@userinfobot`)*

---

## Usage

### Starting the Server

Start the FastAPI application and the background Telegram polling thread:

```bash
uv run python main.py
```

### Interacting via Telegram

1. **Send a Task**: Just send a message to your Telegram bot.
   - Example: *"Go to amazon.com, search for mechanical keyboards, and send me the price of the top result."*
2. **Watch it Work**: The agent will immediately start processing your request. You'll receive a `🚀 Started task` notification.
3. **Request Screenshots**: 
   - Example: *"Open bbc news and send me a screenshot."*
   - The agent will navigate there, capture the viewport, and send the image directly to the chat!
4. **Help the Agent**: If the agent hits a roadblock (e.g., a login page requiring an SMS code), it will send you a message like:
   - *"🙋 Agent needs your help: Please provide the 6-digit code sent to your phone."*
   - Just reply to the bot with the code, and the agent will resume its task!
5. **Get Results**: Once the task is complete, the agent will send a `✅ Task completed!` message along with the final extracted data.

---

## Architecture overview

- **`main.py`**: The FastAPI entry point. It manages background task execution and hosts the Telegram polling loop.
- **`telegram_connector.py`**: A dependency-free (pure `urllib`) module that handles fetching updates and sending text/photo messages to the Telegram API.
- **`browser_use/`**: The core automation framework containing the agent intelligence, browser bindings, and custom tools (like `ask_human` and `send_screenshot_to_human`).
