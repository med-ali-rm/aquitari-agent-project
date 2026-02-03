import flet as ft
import asyncio
import datetime
import json
import os
import requests
import threading
import uuid
import datetime
import opik
import uuid, datetime
from datetime import datetime as dt
from dotenv import load_dotenv
from models import extract_json_from_output


# --- CONFIG ---

# ✅ Get the root folder of brain-api (we move up from app_scripts to its parent)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ✅ Path to the app state file inside brain-api/data
STATE_FILE = os.path.join(BASE_DIR, "data", "app_state.json")

# ✅ Path to the spending log file inside brain-api/data
SPENDING_LOG = os.path.join(BASE_DIR, "data", "spending_log.txt")

# ✅ Load environment variables from the project-relative .env file
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

# ✅ Read sensitive values from .env
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK")   # Unified webhook for state + chat
OPK_API_KEY = os.getenv("OPK_API_KEY")   # Opik API key

# 👇 Debug: check if the variables are actually loaded
print("Webhook URL from env:", N8N_WEBHOOK)
print("Opik API KEY from env:", OPK_API_KEY)

# Configure Opik (make sure OPK_API_KEY is set in your environment)
opik.configure()

# Generate workflow and chat thread IDs once per app run
SESSION_THREAD_ID = f"session-{uuid.uuid4()}-{datetime.date.today()}"
SESSION_THREAD_ID_CHAT = f"{SESSION_THREAD_ID}-chat"   # 👈 chat-specific ID
os.environ["OPIK_PROJECT_NAME"] = "Chat"

class ConversationTracker:
    @opik.track
    def process_conversation_turn(self, user_message, agent_response):
        return {
            "user_message": user_message,
            "agent_response": agent_response,
            "timestamp": dt.now().isoformat()
        }

    def chat_turn(self, user_message, agent_response):
        return self.process_conversation_turn(
            user_message,
            agent_response,
            opik_args={
                "project_name": "Chat",
                "trace": {
                    "name": "conversation_turn",
                    "input": {"user": user_message},
                    "output": {"agent": agent_response},
                    "thread_id": SESSION_THREAD_ID_CHAT  # 👈 use the chat ID here
                    
                }
            }
        )
        
# Create an instance of ConversationTracker
tracker = ConversationTracker()


# --- APP LOGIC CLASS ---
class AquitariApp:
    def __init__(self, page, chat_history, focus_gauge, chill_gauge):
        # Store UI references so we can update them later
        self.page = page
        self.chat_history = chat_history
        self.focus_gauge = focus_gauge
        self.chill_gauge = chill_gauge

        # Load saved state from local JSON file (or initialize defaults if none exists)
        self.load_local_data()
        # Check if a new day has started and reset spending/budget health if needed
        self.check_new_day()
        # Schedule a delayed wake-up sync task when the app starts
        self.wakeup_task = asyncio.create_task(self.delayed_wakeup(event_type="wakeup_event"))
        # Track debounce sync
        self.debounce_task = None
        # Track if app is in sleep mode
        self.sleep_mode = False

    async def delayed_wakeup(self,event_type="state_update"):
        # Wait for 10 seconds before sending state to n8n if no user interaction
        await asyncio.sleep(10)
        # Only send if not already in sleep mode
        if not self.sleep_mode:
            self.sync_state_to_n8n(message="empty",event_type=event_type)   # Send one state snapshot
            self.sleep_mode = True                    # Enter sleep mode after one sync

    def schedule_sync(self, message="empty", delay=15,event_type="wakeup_event"):
        # Schedule a sync after short inactivity (debounce)
        if self.sleep_mode:
            return
        # Cancel any pending debounce task (reset timer if user keeps interacting)
        if self.debounce_task and not self.debounce_task.done():
            self.debounce_task.cancel()
        # Schedule a new debounce sync
        self.debounce_task = asyncio.create_task(self._debounced_sync(message, delay,event_type))

    async def _debounced_sync(self, message, delay,event_type):
        # Wait for inactivity before firing sync
        await asyncio.sleep(delay)
        self.sync_state_to_n8n(message=message,event_type=event_type)
        self.sleep_mode = True   # After one sync, enter sleep mode

    def user_interacted(self):
        # Cancel delayed wake-up if user interacts before it fires
        if self.wakeup_task and not self.wakeup_task.done():
            self.wakeup_task.cancel()
        # Wake up if app was in sleep mode
        if self.sleep_mode:
            self.sleep_mode = False
            # Instead of sending immediately, schedule a sync with debounce
           # self.schedule_sync(message="empty", delay=10,event_type="state_update")

    def load_local_data(self):
        # Load state from file if it exists, otherwise initialize defaults
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                self.data = json.load(f)
            # Ensure new keys exist even if old file doesn't have them
            if "focus_level" not in self.data:
                self.data["focus_level"] = 0.5
            if "chill_level" not in self.data:
                self.data["chill_level"] = 0.5
            if "budget_health" not in self.data:
                self.data["budget_health"] = 1.0
        else:
            self.data = {
                "daily_budget": 0.0,
                "total_spent": 0.0,
                "sleep_hours": 8.0,
                "last_activity": datetime.datetime.now().isoformat(),
                "is_new_day": True,
                "focus_level": 0.5,
                "chill_level": 0.5,
                "budget_health": 1.0,
            }

    def save_local_data(self):
        # Update last activity timestamp and save state to file
        self.data["last_activity"] = datetime.datetime.now().isoformat()
        with open(STATE_FILE, "w") as f:
            json.dump(self.data, f)

    def check_new_day(self):
        # Determine if a new day has started based on last activity
        last_time = datetime.datetime.fromisoformat(self.data["last_activity"])
        now = datetime.datetime.now()
        time_diff = (now - last_time).total_seconds() / 3600
        # Reset spending if it's a new day or early morning after inactivity
        if (time_diff > 2 and now.hour < 6) or (last_time.date() < now.date()):
            self.data["total_spent"] = 0.0
            self.data["budget_health"] = 1.0
            self.data["is_new_day"] = True
            if os.path.exists(SPENDING_LOG):
                os.remove(SPENDING_LOG)
            self.save_local_data()

    def sync_state_to_n8n(self, message="empty", event_type="state_update"):
    
        payload = {
        "thread_id": SESSION_THREAD_ID,  # ✅ Always the same for this run
        "chat": {
            "message": message,
            "budget": self.data["daily_budget"],
            "spent": self.data["total_spent"],
            "sleep": self.data["sleep_hours"],
            "new_day": self.data.get("is_new_day", False),
            "focus_level": self.data.get("focus_level", 0.5),
            "chill_level": self.data.get("chill_level", 0.5),
            "budget_health": self.data.get("budget_health", 1.0),
            "event_type": event_type,  # ✅ Added to mark this as a wake-up/state sync
        }
    }

        try:
            placeholder = ft.Container(
                content=ft.Text("..."),
                alignment=ft.alignment.Alignment(-1, 0),
                padding=12,
                bgcolor="white",
                border_radius=15,
                border=ft.Border.all(1, "#FFE5D9"),
            )
            self.chat_history.controls.append(placeholder)
            self.page.update()

            res = requests.post(N8N_WEBHOOK, json=payload, timeout=60)

            try:
                data = res.json()
                print("Raw JSON response:", data)
            except Exception:
                print("Invalid JSON:", res.text)
                data = {"reply": "I didn’t get it, please try again."}

            parsed = {}
            raw_output = None

            if isinstance(data, list) and "output" in data[0]:
                raw_output = data[0]["output"]
            elif isinstance(data, dict) and "output" in data:
                raw_output = data["output"]
            elif isinstance(data, dict) and "reply" in data:
                parsed = data

            if raw_output:
                # ✅ Use the robust extractor function for all messy cases
                parsed = extract_json_from_output(raw_output)

            if not parsed.get("reply"):
                parsed["reply"] = "I didn’t get it, please try again."

            placeholder.content = ft.Text(parsed["reply"])

            # ✅ Log this user ↔ agent exchange to Opik under the current chat thread
            tracker.chat_turn(message, parsed["reply"])

            if "focus" in parsed:
                self.focus_gauge.controls[0].controls[0].value = parsed["focus"]
                self.data["focus_level"] = parsed["focus"]
            if "chill" in parsed:
                self.chill_gauge.controls[0].controls[0].value = parsed["chill"]
                self.data["chill_level"] = parsed["chill"]

            self.data["is_new_day"] = False
            self.page.update()

            # ✅ Only one send, then sleep
            self.sleep_mode = True

        except Exception as e:
            placeholder.content = ft.Text("Agent unreachable.", color="red", size=10)
            self.page.update()
            print("Sync error:", e)





# --- MAIN FUNCTION ---
def main(page: ft.Page):
    # --- CHAT INTERFACE ---
    chat_history = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    # --- PAGE SETTINGS ---
    page.title = "Aquitari Vital Agent"
    page.bgcolor = "#F4F7F9"
    page.window.width = 420
    page.window.height = 850
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- UI GAUGE BUILDER ---
    def create_gauge(label, value, color="#A8C6BC"):
        ring = ft.ProgressRing(value=value, stroke_width=8, color=color, bgcolor="#F2E0D5")
        return ft.Column(
            [
                ft.Stack(
                    [
                        ring,
                        ft.Container(content=ft.Text("", size=10), alignment=ft.Alignment(0, 0)),
                    ],
                    width=65,
                    height=65,
                ),
                ft.Text(label, size=11, color="#34495E", weight=ft.FontWeight.BOLD),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # Gauges for different metrics
    budget_gauge = create_gauge("Budget Health", 1.0)
    focus_gauge = create_gauge("Focus Level", 0.5, color="#D5E0F2")
    chill_gauge = create_gauge("Chill Level", 0.5, color="#F2D5D5")
    sleep_gauge = create_gauge("Sleep Hours", 0.8)

    # Initialize app logic with UI references
    app_logic = AquitariApp(page, chat_history, focus_gauge, chill_gauge)

    # --- INPUTS ---
    sleep_slider = ft.Slider(
        min=4, max=10, divisions=6, label="{value}h", value=app_logic.data["sleep_hours"],
        active_color="#A8C6BC", on_change=lambda e: update_sleep(e),
    )
    budget_input = ft.TextField(label="Daily Budget", value=str(app_logic.data["daily_budget"]),
                                prefix=ft.Text("$ "), width=140, border_radius=10)
    
    spending_input = ft.TextField(label="Actual Spending", prefix=ft.Text("$ "), width=140, border_radius=10)

    # --- LOGIC HANDLERS ---
    def update_sleep(e):
        # Update local state when user moves sleep slider
        app_logic.data["sleep_hours"] = float(sleep_slider.value)
        sleep_gauge.controls[0].controls[0].value = sleep_slider.value / 10
        app_logic.user_interacted()                 # Wake up if in sleep mode
        app_logic.schedule_sync(message="empty",event_type="state_update")    # Debounced sync (fires once after inactivity)
        page.update()

    def set_budget(e):
        try:
            # Update daily budget from input field
            app_logic.data["daily_budget"] = float(budget_input.value or 0)
            app_logic.save_local_data()
            app_logic.user_interacted()                 # Wake up if in sleep mode
            app_logic.schedule_sync(message="empty",event_type="state_update")    # Debounced sync
            page.snack_bar = ft.SnackBar(ft.Text("Budget Updated!"))
            page.snack_bar.open = True
            page.update()
        except:
            pass

    def add_spending(e):
        try:
            # Add spending entry and recalc budget health
            val = float(spending_input.value or 0)
            app_logic.data["total_spent"] += val
            with open(SPENDING_LOG, "a") as f:
                f.write(f"{datetime.datetime.now()}: ${val}\n")
            if app_logic.data["daily_budget"] > 0:
                health = 1 - (app_logic.data["total_spent"] / app_logic.data["daily_budget"])
                app_logic.data["budget_health"] = max(0.0, min(1.0, health))
                budget_gauge.controls[0].controls[0].value = app_logic.data["budget_health"]
            app_logic.save_local_data()
            app_logic.user_interacted()                 # Wake up if in sleep mode
            app_logic.schedule_sync(message="empty",event_type="state_update")    # Debounced sync
            spending_input.value = ""
            page.update()
        except:
            page.update()

    # --- CHAT INTERFACE ---


    def on_message_send(e):
        # If input field is empty, do nothing
        if not chat_input.value:
            return
        user_msg = chat_input.value

        # Display user message in chat history (right-aligned bubble)
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(user_msg, color="black"),
                alignment=ft.alignment.Alignment(1, 0),  # right-center
                padding=12,
                bgcolor="#FFE5D9",
                border_radius=15
            )
        )
        chat_input.value = ""   # Clear input field after sending
        page.update()
        app_logic.user_interacted()   # Wake up if app was in sleep mode

        try:
            # Build payload with user message + current state snapshot
            payload = {
                "thread_id": SESSION_THREAD_ID,
                "chat": {
                    "message": user_msg,
                    "budget": app_logic.data["daily_budget"],
                    "spent": app_logic.data["total_spent"],
                    "sleep": app_logic.data["sleep_hours"],
                    "new_day": app_logic.data.get("is_new_day", False),
                    "focus_level": app_logic.data.get("focus_level", 0.5),
                    "chill_level": app_logic.data.get("chill_level", 0.5),
                    "budget_health": app_logic.data.get("budget_health", 1.0),
                    # ✅ Always the same for this run
                }
            }

            # Show placeholder bubble with "..." while agent is thinking
            placeholder = ft.Container(
                content=ft.Text("..."),
                alignment=ft.alignment.Alignment(-1, 0),  # left-center
                padding=12,
                bgcolor="white",
                border_radius=15,
                border=ft.Border.all(1, "#FFE5D9"),
            )
            chat_history.controls.append(placeholder)
            page.update()

            # Send chat message immediately
            res = requests.post(N8N_WEBHOOK, json=payload, timeout=70)

            # Safely parse response
            try:
                data = res.json()
                print("Raw JSON response:", data)  # Debug
            except Exception:
                print("Invalid JSON:", res.text)
                data = {"reply": "I didn’t get it, please try again."}

            parsed = {}
            raw_output = None

            if isinstance(data, list) and "output" in data[0]:
                raw_output = data[0]["output"]
            elif isinstance(data, dict) and "output" in data:
                raw_output = data["output"]
            elif isinstance(data, dict) and "reply" in data:
                parsed = data

            if raw_output:
                # ✅ Use the robust extractor function for all messy cases
                parsed = extract_json_from_output(raw_output)

            if not parsed.get("reply"):
                parsed["reply"] = "I didn’t get it, please try again."

            # ✅ Update the placeholder bubble with the actual reply
            placeholder.content = ft.Text(parsed["reply"])

            # ✅ Log this user ↔ agent exchange to Opik under the current chat thread
            tracker.chat_turn(user_msg, parsed["reply"])

            # Update gauges if response includes focus/chill values
            if "focus" in parsed:
                focus_gauge.controls[0].controls[0].value = parsed["focus"]
                app_logic.data["focus_level"] = parsed["focus"]
            if "chill" in parsed:
                chill_gauge.controls[0].controls[0].value = parsed["chill"]
                app_logic.data["chill_level"] = parsed["chill"]

            # 🔄 Schedule idle sync (only once, no double send)
            if hasattr(app_logic, "idle_timer") and app_logic.idle_timer:
                app_logic.idle_timer.cancel()

            def idle_sync():
                app_logic.sync_state_to_n8n(message="empty",event_type="wakeup_event")
                app_logic.sleep_mode = True

            app_logic.idle_timer = threading.Timer(20.0, idle_sync)
            app_logic.idle_timer.start()

        except Exception as e:
            placeholder.content = ft.Text("Agent unreachable.", color="red", size=10)
            print("Sync error:", e)

        page.update()



    # Chat input field
    chat_input = ft.TextField(
        hint_text="Talk to Aquitari Agent Vita...", expand=True, on_submit=on_message_send
    )

    # --- LAYOUT ASSEMBLY ---
    page.add(
        ft.Row(
            [
                ft.Text("Aquitari", size=24, weight="bold", color="#34495E"),
                ft.Icon(icon=ft.Icons.SETTINGS, color="#34495E"),  # Settings icon
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        ft.Row(
            [budget_gauge, focus_gauge, chill_gauge, sleep_gauge],
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
        ),
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Sleep Hours", size=14, weight="bold"),
                    sleep_slider,
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    budget_input,
                                    ft.Button("Set", on_click=set_budget),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Column(
                                [
                                    spending_input,
                                    ft.Button("Add", on_click=add_spending),
                                ],
                                horizontal_alignment="center",
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    ),
                ]
            ),
            bgcolor="white",
            padding=20,
            border_radius=25,
        ),
        ft.Container(content=chat_history, height=350),  # Chat history area
        ft.Row(
            [
                chat_input,
                ft.IconButton(
                    icon=ft.Icons.SEND_ROUNDED,
                    icon_color="#A8C6BC",
                    on_click=on_message_send,  # Send chat message
                ),
            ]
        ),
    )


# THE FIX: Using the correct run/main structure for Flet 0.70+
if __name__ == "__main__":
    ft.app(target=main)