# Nova Voice Assistant

Nova is a Python desktop voice assistant with a live neural-network visualizer, word-synchronized speech, and locally saved chat history. It uses Groq's chat API for responses and `pyttsx3` for system text-to-speech.

## Features

- Animated blue neural-network background and voice waveform
- Displays each word as the speech engine speaks it
- Start new conversations and browse or reopen saved chats
- Keeps conversation history on the local machine
- Configurable Groq model through an environment variable

## Requirements

- Windows 10 or later (primary target)
- Python 3.10 or later with Tk support
- A Groq API key and an internet connection
- An available system speech voice and audio output

## Setup

Clone the repository and open PowerShell in the project directory. Create a virtual environment and install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the `py` command is unavailable, create the environment with your Python executable instead:

```powershell
python -m venv .venv
```

## Configure And Run

Create an API key in your Groq account. Set it in the same PowerShell window used to run Nova. Do not put API keys in source files or commit them to GitHub.

```powershell
$env:GROQ_API_KEY = 'YOUR_GROQ_API_KEY'
.\.venv\Scripts\python.exe .\nova_assistant.py
```

The environment variable lasts for the current terminal session. Set it again when opening a new terminal.

Nova defaults to `openai/gpt-oss-120b`. To use another model available to your account, set `GROQ_MODEL` before launching:

```powershell
$env:GROQ_MODEL = 'your-groq-model-id'
.\.venv\Scripts\python.exe .\nova_assistant.py
```

## Use The App

- Enter a message at the bottom and press Enter or select **SEND**.
- Watch the current spoken word in the center of the animated display.
- Select **CHAT HISTORY** to preview saved conversations, then select **OPEN CHAT** to continue one.
- Select **NEW CHAT** to start a separate conversation.

## Chat Storage And Privacy

On Windows, conversations are saved as JSON in `%APPDATA%\Nova\chat_history.json`. The file is stored locally in plain text and is not encrypted. Delete it to remove saved chats. Avoid entering sensitive information you do not want stored on the device.

## Troubleshooting

- **API key error:** Verify `GROQ_API_KEY` is set in the terminal launching Nova and that the key is active. Revoke any key that has been shared or committed.
- **Model not found:** Confirm `GROQ_MODEL` is a model available to your Groq account. Remove an old override with `Remove-Item Env:GROQ_MODEL` to use the default.
- **Cloudflare error 1010:** Nova displays the Cloudflare Ray ID when available. If the error continues, contact Groq support and include that ID.
- **No speech:** Reinstall dependencies with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and check that Windows has an available speech voice and audio output device.
- **Python command not found:** Install Python or select an installed interpreter in VS Code. The virtual-environment commands above use `py` or your Python executable directly.
