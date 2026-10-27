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

Create an API key in your Groq account. Copy the example config and enter your key in `config.json`:

```powershell
Copy-Item .\config.example.json .\config.json
notepad .\config.json
.\.venv\Scripts\python.exe .\nova_assistant.py
```

Set the `groq_api_key` value in the JSON file. The file is excluded by `.gitignore`; never commit it or share it. Nova also accepts `GROQ_API_KEY`, which takes precedence over the config file.

Nova defaults to `openai/gpt-oss-120b`. To use another model available to your account, set `GROQ_MODEL` before launching:

```powershell
$env:GROQ_MODEL = 'your-groq-model-id'
.\.venv\Scripts\python.exe .\nova_assistant.py
```

## Build A Standalone Windows App

Install PyInstaller into the project environment and build a single-file, windowed executable:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name standalone --collect-all pyttsx3 --collect-all comtypes .\nova_assistant.py
Copy-Item .\config.json .\dist\config.json -Force
.\dist\standalone.exe
```

The build is written to `dist\standalone.exe`. Keep `config.json` beside the executable. It is read at runtime and is not embedded in the executable, so the same build can use a different key without rebuilding. Do not publish the config file.

## Use The App

- Enter a message at the bottom and press Enter or select **SEND**.
- Watch the current spoken word in the center of the animated display.
- Select **CHAT HISTORY** to preview saved conversations, then select **OPEN CHAT** to continue one.
- Select **NEW CHAT** to start a separate conversation.

## Chat Storage And Privacy

On Windows, conversations are saved as JSON in `%APPDATA%\Nova\chat_history.json`. The file is stored locally in plain text and is not encrypted. Delete it to remove saved chats. Avoid entering sensitive information you do not want stored on the device.

## Troubleshooting

- **API key error:** Check `groq_api_key` in `config.json`, or verify `GROQ_API_KEY` is set in the launching terminal. Revoke any key that has been shared or committed.
- **Model not found:** Confirm `GROQ_MODEL` is a model available to your Groq account. Remove an old override with `Remove-Item Env:GROQ_MODEL` to use the default.
- **Cloudflare error 1010:** Nova displays the Cloudflare Ray ID when available. If the error continues, contact Groq support and include that ID.
- **No speech:** Reinstall dependencies with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and check that Windows has an available speech voice and audio output device.
- **Python command not found:** Install Python or select an installed interpreter in VS Code. The virtual-environment commands above use `py` or your Python executable directly.
