import json
import math
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
SYSTEM_PROMPT = (
    "You are Nova, a capable, composed voice assistant. "
    "Be natural, concise, and useful. Speak plainly and avoid markdown tables."
)


def load_api_key(config_path: Path | None = None) -> str:
    environment_key = os.getenv("GROQ_API_KEY", "").strip()
    if environment_key:
        return environment_key

    if config_path is None:
        app_directory = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        config_path = app_directory / "config.json"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    if not isinstance(config, dict):
        return ""
    api_key = config.get("groq_api_key", "")
    return api_key.strip() if isinstance(api_key, str) else ""


API_KEY = load_api_key()


class NovaAssistant:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("N.O.V.A. | Voice Interface")
        self.root.geometry("1120x760")
        self.root.minsize(860, 620)
        self.root.configure(bg="#080d19")

        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.history_path = Path(os.getenv("APPDATA", str(Path.home()))) / "Nova" / "chat_history.json"
        self.saved_chats = self._load_saved_chats()
        self.session_id = uuid4().hex
        self.session_title = "New conversation"
        self.history: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.state = "READY"
        self.busy = False
        self.api_key = API_KEY
        self.current_word = "READY WHEN YOU ARE"
        self.word_started_at = time.monotonic()
        self.started_at = time.monotonic()
        self._build_ui()
        self._set_status("READY" if self.api_key else "KEY MISSING")
        if not self.api_key:
            self.current_word = "ADD KEY TO CONFIG.JSON"

        self.root.after(50, self._poll_events)
        self._animate()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Nova.TEntry",
            fieldbackground="#111a2b",
            foreground="#e8f4ff",
            insertcolor="#73caff",
            bordercolor="#263b5b",
            lightcolor="#263b5b",
            darkcolor="#263b5b",
            padding=12,
        )
        style.configure(
            "Send.TButton",
            background="#69bfff",
            foreground="#07101d",
            padding=(18, 10),
            borderwidth=0,
            font=("Bahnschrift", 10, "bold"),
        )
        style.map("Send.TButton", background=[("disabled", "#263b5b"), ("active", "#9ad7ff")])
        style.configure(
            "History.TButton",
            background="#111a2b",
            foreground="#b9dfff",
            padding=(13, 9),
            borderwidth=1,
            font=("Bahnschrift", 9, "bold"),
        )
        style.map("History.TButton", background=[("active", "#1b2c47")])
        style.configure(
            "New.TButton",
            background="#14233a",
            foreground="#91cfff",
            padding=(13, 9),
            borderwidth=1,
            font=("Bahnschrift", 9, "bold"),
        )
        style.map("New.TButton", background=[("active", "#203756")])

        header = tk.Frame(self.root, bg="#080d19", height=72, padx=30)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header,
            text="N.O.V.A.",
            bg="#080d19",
            fg="#e8f4ff",
            font=("Bahnschrift SemiBold", 19),
        ).pack(side="left", pady=18)
        tk.Label(
            header,
            text="VOICE INTERFACE   /   NEURAL LINK",
            bg="#080d19",
            fg="#7188a8",
            font=("Bahnschrift", 9),
        ).pack(side="left", padx=(18, 0), pady=22)
        ttk.Button(header, text="CHAT HISTORY", style="History.TButton", command=self._open_history).pack(
            side="right", padx=(8, 0), pady=14
        )
        ttk.Button(header, text="NEW CHAT", style="New.TButton", command=self._new_chat).pack(
            side="right", padx=(8, 0), pady=14
        )
        self.status_label = tk.Label(
            header,
            text="SYSTEM READY",
            bg="#080d19",
            fg="#77caff",
            font=("Bahnschrift", 9, "bold"),
        )
        self.status_label.pack(side="right", pady=22)
        tk.Label(
            header,
            text="●",
            bg="#080d19",
            fg="#77caff",
            font=("Segoe UI Symbol", 10),
        ).pack(side="right", padx=(0, 9), pady=22)

        body = tk.Frame(self.root, bg="#080d19", padx=20, pady=4)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(body, bg="#080d19", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", self._draw_background)

        composer = tk.Frame(self.root, bg="#080d19", padx=24, pady=16)
        composer.grid(row=2, column=0, sticky="ew")
        composer.columnconfigure(0, weight=1)
        self.input_entry = ttk.Entry(composer, style="Nova.TEntry", font=("Bahnschrift", 11))
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.input_entry.bind("<Return>", self._submit)
        self.send_button = ttk.Button(composer, text="SEND  ↗", style="Send.TButton", command=self._submit)
        self.send_button.grid(row=0, column=1)
        self.input_entry.focus_set()

        footer = tk.Frame(self.root, bg="#080d19", padx=30, pady=0)
        footer.grid(row=3, column=0, sticky="ew")
        tk.Label(
            footer,
            text="GROQ RESPONSE CHANNEL    ·    CHATS SAVED ON THIS DEVICE",
            bg="#080d19",
            fg="#536784",
            font=("Bahnschrift", 8),
        ).pack(anchor="w", pady=(0, 12))

    def _set_status(self, status: str) -> None:
        self.state = status
        label, color = {
            "READY": ("SYSTEM READY", "#77caff"),
            "THINKING": ("PROCESSING", "#f2c879"),
            "SPEAKING": ("VOICE ACTIVE", "#8fe6ff"),
            "KEY MISSING": ("API KEY MISSING", "#ff927f"),
            "ERROR": ("LINK ERROR", "#ff927f"),
        }.get(status, (status, "#a9bdd8"))
        self.status_label.configure(text=label, fg=color)

    def _load_saved_chats(self) -> list[dict[str, object]]:
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return [chat for chat in data if isinstance(chat, dict)] if isinstance(data, list) else []

    def _save_current_chat(self) -> None:
        messages = [
            message.copy()
            for message in self.history
            if message["role"] in {"user", "assistant"}
        ]
        if not messages:
            return

        first_user_message = next(
            (message["content"].replace("\n", " ").strip() for message in messages if message["role"] == "user"),
            self.session_title,
        )
        title = first_user_message[:52] + ("…" if len(first_user_message) > 52 else "")
        record: dict[str, object] = {
            "id": self.session_id,
            "title": title or "New conversation",
            "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
            "messages": messages,
        }
        self.saved_chats = [chat for chat in self.saved_chats if chat.get("id") != self.session_id]
        self.saved_chats.insert(0, record)
        self.saved_chats = self.saved_chats[:100]

        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.history_path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(self.saved_chats, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(self.history_path)
        except OSError:
            self.current_word = "CHAT HISTORY COULD NOT BE SAVED"
            self.word_started_at = time.monotonic()
            self._set_status("ERROR")

    def _open_history(self) -> None:
        self._save_current_chat()
        window = tk.Toplevel(self.root)
        window.title("Nova | Chat History")
        window.geometry("820x480")
        window.minsize(680, 380)
        window.configure(bg="#0b1424")
        window.transient(self.root)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        tk.Label(
            window,
            text="CHAT HISTORY",
            bg="#0b1424",
            fg="#c5e8ff",
            anchor="w",
            font=("Bahnschrift", 10, "bold"),
            padx=18,
            pady=16,
        ).grid(row=0, column=0, sticky="ew")

        content = tk.Frame(window, bg="#0b1424", padx=18)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=2)
        content.columnconfigure(1, weight=3)
        content.rowconfigure(0, weight=1)

        chat_list = tk.Listbox(
            content,
            bg="#101d32",
            fg="#dcefff",
            selectbackground="#24527a",
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#203653",
            activestyle="none",
            font=("Bahnschrift", 10),
            borderwidth=0,
            exportselection=False,
        )
        chat_list.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        preview = ScrolledText(
            content,
            wrap="word",
            state="disabled",
            bg="#101827",
            fg="#dcefff",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=12,
            font=("Bahnschrift", 10),
        )
        preview.grid(row=0, column=1, sticky="nsew")
        preview.tag_configure("user", foreground="#8bcaff", font=("Bahnschrift", 9, "bold"))
        preview.tag_configure("assistant", foreground="#91e7ff", font=("Bahnschrift", 9, "bold"))

        for chat in self.saved_chats:
            title = str(chat.get("title", "Untitled conversation"))
            try:
                updated = datetime.fromisoformat(str(chat.get("updated", ""))).strftime("%b %d  %H:%M")
            except ValueError:
                updated = "Saved"
            chat_list.insert(tk.END, f"{title}\n  {updated}")

        def display_selected(_event: tk.Event | None = None) -> None:
            selection = chat_list.curselection()
            if not selection:
                return
            chat = self.saved_chats[selection[0]]
            preview.configure(state="normal")
            preview.delete("1.0", "end")
            for message in chat.get("messages", []):
                if not isinstance(message, dict):
                    continue
                role = message.get("role")
                if role not in {"user", "assistant"}:
                    continue
                preview.insert("end", f"{'YOU' if role == 'user' else 'NOVA'}\n", role)
                preview.insert("end", f"{message.get('content', '')}\n\n")
            preview.configure(state="disabled")

        def open_selected(_event: tk.Event | None = None) -> None:
            selection = chat_list.curselection()
            if not selection or self.busy:
                return
            chat = self.saved_chats[selection[0]]
            messages = chat.get("messages", [])
            restored = [
                message.copy()
                for message in messages
                if isinstance(message, dict) and message.get("role") in {"user", "assistant"}
            ]
            self.session_id = str(chat.get("id", uuid4().hex))
            self.session_title = str(chat.get("title", "Conversation"))
            self.history = [{"role": "system", "content": SYSTEM_PROMPT}, *restored]
            self.current_word = "CONVERSATION RESTORED"
            self.word_started_at = time.monotonic()
            self._set_status("READY")
            window.destroy()

        chat_list.bind("<<ListboxSelect>>", display_selected)
        chat_list.bind("<Double-Button-1>", open_selected)

        actions = tk.Frame(window, bg="#0b1424", padx=18, pady=14)
        actions.grid(row=2, column=0, sticky="ew")
        tk.Label(
            actions,
            text=f"{len(self.saved_chats)} SAVED CONVERSATIONS",
            bg="#0b1424",
            fg="#607b9e",
            font=("Bahnschrift", 8),
        ).pack(side="left", pady=8)
        ttk.Button(actions, text="OPEN CHAT", style="Send.TButton", command=open_selected).pack(side="right")
        ttk.Button(actions, text="CLOSE", style="History.TButton", command=window.destroy).pack(
            side="right", padx=(0, 8)
        )
        if self.saved_chats:
            chat_list.selection_set(0)
            display_selected()

    def _new_chat(self) -> None:
        if self.busy:
            return
        self._save_current_chat()
        self.session_id = uuid4().hex
        self.session_title = "New conversation"
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.current_word = "READY WHEN YOU ARE"
        self.word_started_at = time.monotonic()
        self._set_status("READY" if self.api_key else "KEY MISSING")
        self.input_entry.focus_set()

    def _on_close(self) -> None:
        self._save_current_chat()
        self.root.destroy()

    def _submit(self, _event: tk.Event | None = None) -> None:
        prompt = self.input_entry.get().strip()
        if not prompt or self.busy:
            return
        if not self.api_key:
            self._set_status("KEY MISSING")
            self.current_word = "ADD KEY TO CONFIG.JSON"
            return

        self.input_entry.delete(0, "end")
        self.history.append({"role": "user", "content": prompt})
        if self.session_title == "New conversation":
            self.session_title = prompt[:52]
        self._save_current_chat()
        self.current_word = "THINKING"
        self.word_started_at = time.monotonic()
        self.busy = True
        self.send_button.configure(state="disabled")
        self.input_entry.configure(state="disabled")
        self._set_status("THINKING")
        request_history = [self.history[0], *self.history[-24:]]
        threading.Thread(target=self._request_and_speak, args=(request_history,), daemon=True).start()

    def _request_and_speak(self, messages: list[dict[str, str]]) -> None:
        api_key = self.api_key
        payload = json.dumps(
            {
                "model": MODEL,
                "messages": messages,
                "temperature": 0.7,
            }
        ).encode("utf-8")
        request = Request(
            API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Nova-Voice-Assistant/1.0",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            answer = result["choices"][0]["message"]["content"].strip()
            if not answer:
                raise ValueError("The model returned an empty reply.")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            detail = detail.replace(api_key, "[redacted]")
            if error.code == 403 and "1010" in detail:
                ray_id = error.headers.get("cf-ray", "")
                detail = "Cloudflare blocked this client (error 1010)."
                if ray_id:
                    detail += f" Cloudflare Ray ID: {ray_id}."
                detail += " If it continues, contact Groq support with that Ray ID."
            self.events.put(("error", f"Groq API error ({error.code}): {detail or error.reason}"))
            self.events.put(("word", "CONNECTION ERROR"))
            self.events.put(("state", "ERROR"))
            self.events.put(("busy", "false"))
            return
        except (URLError, TimeoutError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
            self.events.put(("error", f"Could not get a reply: {error}"))
            self.events.put(("word", "CONNECTION ERROR"))
            self.events.put(("state", "ERROR"))
            self.events.put(("busy", "false"))
            return

        self.events.put(("assistant", answer))
        self.events.put(("state", "SPEAKING"))
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", 178)

            def on_word(_name: str, location: int, length: int) -> None:
                word = answer[location : location + length].strip()
                if word:
                    self.events.put(("word", word))

            engine.connect("started-word", on_word)
            engine.say(answer)
            engine.runAndWait()
            engine.stop()
        except Exception as error:
            self.events.put(("notice", f"Voice output unavailable: {error}"))
        finally:
            self.events.put(("word", "RESPONSE COMPLETE"))
            self.events.put(("state", "READY"))
            self.events.put(("busy", "false"))

    def _poll_events(self) -> None:
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break

            if kind == "assistant":
                self.history.append({"role": "assistant", "content": value})
                self._save_current_chat()
            elif kind == "word":
                self.current_word = value.upper()
                self.word_started_at = time.monotonic()
            elif kind in {"error", "notice"}:
                self.current_word = value.upper()[:64]
                self.word_started_at = time.monotonic()
            elif kind == "state":
                self._set_status(value)
            elif kind == "busy":
                self.busy = value == "true"
                self.send_button.configure(state="disabled" if self.busy else "normal")
                self.input_entry.configure(state="disabled" if self.busy else "normal")
                if not self.busy:
                    self.input_entry.focus_set()

        self.root.after(50, self._poll_events)

    def _animate(self) -> None:
        self._draw_visual()
        self.root.after(33, self._animate)

    def _draw_background(self, _event: tk.Event | None = None) -> None:
        self._draw_visual()

    def _draw_visual(self) -> None:
        canvas = self.canvas
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        canvas.delete("all")
        for band in range(48):
            progress = band / 47
            color = f"#{7 + int(progress * 7):02x}{12 + int(progress * 15):02x}{28 + int(progress * 42):02x}"
            canvas.create_rectangle(
                width * band / 48,
                0,
                width * (band + 1) / 48 + 1,
                height,
                fill=color,
                outline=color,
            )

        center_x = width * 0.5
        center_y = height * 0.48
        elapsed = time.monotonic() - self.started_at
        speaking = self.state == "SPEAKING"
        thinking = self.state == "THINKING"
        pulse = math.sin(elapsed * (7.0 if speaking else 2.0))
        intensity = 1.0 if speaking else 0.45 if thinking else 0.15
        radius = min(width, height) * 0.19

        for index in range(10, 0, -1):
            glow_radius = radius * (1.0 + index * 0.13) + pulse * intensity * 3
            blue = max(25, 82 - index * 5)
            glow_color = f"#0b{max(18, blue - 35):02x}{blue:02x}"
            canvas.create_oval(
                center_x - glow_radius,
                center_y - glow_radius,
                center_x + glow_radius,
                center_y + glow_radius,
                fill=glow_color,
                outline="",
            )

        nodes = []
        for index in range(22):
            node_x = width * (0.06 + ((index * 37) % 87) / 100) + math.sin(elapsed * 0.5 + index) * 9
            node_y = height * (0.10 + ((index * 53) % 76) / 100) + math.cos(elapsed * 0.42 + index) * 8
            nodes.append((node_x, node_y))

        for left_index, (left_x, left_y) in enumerate(nodes):
            for right_index in range(left_index + 1, len(nodes)):
                right_x, right_y = nodes[right_index]
                distance = math.hypot(right_x - left_x, right_y - left_y)
                if distance < min(width, height) * 0.23:
                    canvas.create_line(left_x, left_y, right_x, right_y, fill="#1a426d", width=1)
                    if (left_index + right_index) % 5 == int(elapsed * 3) % 5:
                        travel = (elapsed * 0.6 + left_index * 0.13) % 1
                        dot_x = left_x + (right_x - left_x) * travel
                        dot_y = left_y + (right_y - left_y) * travel
                        canvas.create_oval(dot_x - 2, dot_y - 2, dot_x + 2, dot_y + 2, fill="#93e1ff", outline="")

        for index, (node_x, node_y) in enumerate(nodes):
            node_radius = 2 + abs(math.sin(elapsed * 1.7 + index)) * (2.0 if speaking else 0.8)
            canvas.create_oval(
                node_x - node_radius,
                node_y - node_radius,
                node_x + node_radius,
                node_y + node_radius,
                fill="#91d8ff" if index % 4 == 0 else "#4485bd",
                outline="",
            )

        for ring in range(5, 0, -1):
            ring_radius = radius * ring * 0.39 * (1 + pulse * 0.024 * intensity)
            ring_fill = ("#0b192c", "#0d213a", "#0f2c4b", "#12385d", "#164675")[5 - ring]
            canvas.create_oval(
                center_x - ring_radius,
                center_y - ring_radius,
                center_x + ring_radius,
                center_y + ring_radius,
                fill=ring_fill,
                outline="#3d9bd7" if ring == 5 else ring_fill,
                width=2 if ring == 5 else 1,
            )

        for index in range(88):
            angle = 2 * math.pi * index / 88 + elapsed * (0.34 if speaking else 0.025)
            wave = abs(math.sin(index * 0.53 + elapsed * (8.5 if speaking else 1.8)))
            bar_length = 3 + wave * (34 if speaking else 8 if thinking else 2)
            inner = radius * 0.82
            outer = inner + bar_length
            canvas.create_line(
                center_x + math.cos(angle) * inner,
                center_y + math.sin(angle) * inner,
                center_x + math.cos(angle) * outer,
                center_y + math.sin(angle) * outer,
                fill="#a8e8ff" if index % 6 == 0 else "#54b7ff",
                width=2 if index % 3 == 0 else 1,
                capstyle="round",
            )

        word_font_size = max(16, min(30, int(width * 0.028)))
        canvas.create_text(
            center_x,
            center_y - radius * 0.11,
            text=self.current_word,
            fill="#f0fbff" if speaking else "#c2e2ff",
            width=min(width * 0.5, 640),
            justify="center",
            font=("Bahnschrift SemiBold", word_font_size, "bold"),
        )
        canvas.create_text(
            center_x,
            center_y + radius * 0.23,
            text={
                "READY": "VOICE LINK STANDBY",
                "THINKING": "FORMULATING RESPONSE",
                "SPEAKING": "LIVE VOICE TRANSCRIPTION",
                "KEY MISSING": "CREDENTIAL REQUIRED",
                "ERROR": "VOICE LINK INTERRUPTED",
            }.get(self.state, "VOICE LINK STANDBY"),
            fill="#78b8e7",
            font=("Bahnschrift", 8, "bold"),
        )

        glow_x = center_x + math.sin(elapsed * 0.7) * radius * 0.16
        glow_y = center_y + math.cos(elapsed * 0.52) * radius * 0.16
        canvas.create_oval(
            glow_x - 4,
            glow_y - 4,
            glow_x + 4,
            glow_y + 4,
            fill="#e8fbff",
            outline="#77d2ff",
            width=2,
        )


def main() -> None:
    root = tk.Tk()
    NovaAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()