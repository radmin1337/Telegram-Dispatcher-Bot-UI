---

![Telegram Dispatcher](https://raw.githubusercontent.com/radmin1337/Telegram-Dispatcher-Bot-UI/refs/heads/main/images/dispatcher.png)

---

# Telegram Dispatcher

**Telegram Dispatcher** is a professional, high-performance desktop client for managing Telegram Bots. Built with Python and PyQt5, it provides a pixel-perfect replica of the Telegram Desktop interface, allowing you to control your bot, manage chats, and handle various media types with a native-feel experience.

## Features

*   **Pixel-Perfect UI:** A meticulous dark-mode replica of Telegram Desktop, featuring custom message bubbles with "tails," smooth animations, and a slim custom scrollbar.
*   **Full Media Support:** 
    *   Send and receive **Photos**, **Stickers**, and **GIFs**.
    *   Manage **Files**, **Videos**, and **Audio** messages with dedicated UI blocks.
    *   **Reveal in Explorer:** Click on any media bubble to instantly open its location in your system's file manager.
*   **Asynchronous Task Manager:** A dedicated Loading Overlay with a progress bar and "Cancel" button ensures the UI never freezes during heavy file uploads or downloads.
*   **Message Control:** Full support for **Editing** and **Deleting** sent messages directly from the context menu (Right-Click).
*   **Multi-Bot Management:** Isolated chat histories and settings for every individual Bot Token, stored securely in a local configuration.
*   **Manual Chat Control:** Manually add new conversations via User ID or remove inactive ones from your sidebar.
*   **Persistent & Smart Storage:** All conversations are saved in `config.json`. Temporary media files are cleaned up on exit and automatically re-downloaded from Telegram servers when needed.

## Requirements

To run this project, you need:

*   **Python 3.10+**
*   **PyQt5** (UI Framework)
*   **pyTelegramBotAPI** (Telegram Bot API wrapper)
*   **Requests** (For file handling)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/radmin1337/Telegram-Dispatcher-Bot-UI.git
    cd Telegram-Dispatcher-Bot-UI
    ```

2.  **Install dependencies:**
    ```bash
    pip install PyQt5 pyTelegramBotAPI requests
    ```

3.  **Run the application:**
    ```bash
    python mld.py
    ```

## How to Use

1.  **Authorization:** Enter your Bot Token on the splash screen and click **CONNECT**. The app will sync your existing chat metadata.
2.  **Messaging:** 
    *   Select a contact from the left sidebar to load the history.
    *   Use the **📎 (Paperclip)** button to send images, stickers, or documents.
    *   Type text and press `Enter` or click the **➤** arrow to send.
3.  **Management:**
    *   **Right-Click** on your messages to Edit or Delete them.
    *   **Left-Click** on files/images to open them in your computer's folders.
    *   Use the **Add/Delete** buttons in the sidebar to manage your contact list via Telegram IDs.

## Configuration
The `config.json` file stores your bot tokens and structured chat histories. It is designed to be portable—you can move it between installations to keep your data.

---
