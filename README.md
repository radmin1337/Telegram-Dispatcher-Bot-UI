---

![Telegram Dispatcher](https://raw.githubusercontent.com/radmin1337/Telegram-Dispatcher-Bot-UI/refs/heads/main/images/dispatcher.png)

---
# Telegram Dispatcher

**Telegram Dispatcher** is a professional, high-performance desktop client for managing Telegram Bots. Built with Python and PyQt5, it provides a pixel-perfect replica of the Telegram Desktop interface, allowing you to send and receive messages through your bot with ease.

## Features

*   **Telegram Desktop UI:** A meticulous dark-mode replica including real message bubbles, "tails," and custom-styled scrollbars.
*   **Multi-Bot Management:** Unique chat history and settings saved per individual Bot Token.
*   **Smart Bubble Logic:** Dynamic message width calculation based on text length (up to 40+ characters per line) for a clean look.
*   **Persistent Storage:** All tokens, chats, and message histories are saved locally in a `config.json` file.
*   **Chat Manager:** Manually add chats by User ID or delete existing ones directly from the sidebar.
*   **Real-time Interaction:** High-speed polling with multi-threaded architecture to prevent UI freezing.
*   **Safe Connection:** Secure authorization screen before entering the main dashboard.

## Requirements

To run this project, you need:

*   **Python 3.8+**
*   **PyQt5** (for the UI)
*   **pyTelegramBotAPI** (Telebot library)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/radmin1337/Telegram-Dispatcher-Bot-UI.git
    cd Telegram-Dispatcher-Bot-UI
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *If you don't have a requirements file yet, run:*
    ```bash
    pip install PyQt5 pyTelegramBotAPI
    ```

3.  **Run the application:**
    ```bash
    python mld.py
    ```

## How to Use

1.  **Login:** Paste your Telegram Bot Token into the authorization field and click **CONNECT**.
2.  **Dashboard:**
    *   **Incoming Messages:** Chats will automatically appear in the left sidebar when users message your bot.
    *   **Manual Control:** Use the "Add" field to manually start a chat via User ID.
    *   **Messaging:** Click on a chat to open the dialogue. Type your message and hit the arrow (➤) or press `Enter`.
3.  **Management:** Right-click or use the Delete button to clean up your chat list.

## Configuration
The app generates a `config.json` in the root directory. This file stores your bot tokens and encrypted-like structures of your chat histories, ensuring you never lose a conversation.

---
