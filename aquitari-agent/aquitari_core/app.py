"""
Aquitari Vita Agent 

This script builds a Flet-based desktop/mobile application that tracks daily budget,
spending, sleep hours, and provides a simple chat interface connected to external
N8N webhooks. It includes:
- Persistent local state management (JSON file + spending log).
- Daily reset logic for budget/spending.
- Synchronization of state with N8N workflows.
- Interactive UI with gauges, sliders, text inputs, and chat interface.
- Simple visualization of health indicators (budget, focus, chill, sleep).
"""

import flet as ft
import requests
import json
import datetime
import os
import asyncio   # NEW: import asyncio so you can use create_task and sleep

# --- CONFIGURATION ---
N8N_WEBHOOK = ""  # Unified webhook for state + chat
# TODO: Replace with relative path
STATE_FILE = "PATH_TO_brain-api_data/app_state.json"
SPENDING_LOG = "PATH_TO_brain-api_data/spending_log.txt"


class AquitariApp:
    def __init__(self):
        # Load saved state from local JSON file (or initialize defaults if none exists)
        self.load_local_data()
        # Check if a new day has started and reset spending/budget health if needed
        self.check_new_day()
        # Schedule a delayed wake-up sync task when the app starts
        self.wakeup_task = asyncio.create_task(self.delayed_wakeup())

    async def delayed_wakeup(self):
        # Wait for 10 seconds before sending state to n8n if no user interaction
        await asyncio.sleep(10)
        self.sync_state_to_n8n(message="empty")

    def user_interacted(self):
        # Cancel delayed wake-up if the user interacts before it fires
        if self.wakeup_task and not self.wakeup_task.done():
            self.wakeup_task.cancel()

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

    def sync_state_to_n8n(self, message="empty"):
        # Send current state + message (or "empty") to N8N webhook
        payload = {
            "chat": {
                "message": message,
                "budget": self.data["daily_budget"],
                "spent": self.data["total_spent"],
                "sleep": self.data["sleep_hours"],
                "new_day": self.data.get("is_new_day", False),
                "focus_level": self.data.get("focus_level", 0.5),
                "chill_level": self.data.get("chill_level", 0.5),
                "budget_health": self.data.get("budget_health", 1.0),
            }
        }
        try:
            requests.post(N8N_WEBHOOK, json=payload, timeout=5)
            self.data["is_new_day"] = False
        except:
            print("Sync: N8N unreachable")


def main(page: ft.Page):
    # Initialize app logic
    app_logic = AquitariApp()

    # --- PAGE SETTINGS ---
    page.title = "Aquitari Vita Agent"
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
    budget_gauge = create_gauge("Budget Health", app_logic.data["budget_health"])
    focus_gauge = create_gauge("Focus Level", app_logic.data["focus_level"], color="#D5E0F2")
    chill_gauge = create_gauge("Chill Level", app_logic.data["chill_level"], color="#F2D5D5")
    sleep_gauge = create_gauge("Sleep Hours", app_logic.data["sleep_hours"] / 10)

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
        app_logic.data["sleep_hours"] = float(sleep_slider.value)
        sleep_gauge.controls[0].controls[0].value = sleep_slider.value / 10
        app_logic.user_interacted()
        app_logic.sync_state_to_n8n(message="empty")
        page.update()

    def set_budget(e):
        try:
            app_logic.data["daily_budget"] = float(budget_input.value or 0)
            app_logic.save_local_data()
            app_logic.user_interacted()
            app_logic.sync_state_to_n8n(message="empty")
            page.snack_bar = ft.SnackBar(ft.Text("Budget Updated!"))
            page.snack_bar.open = True
            page.update()
        except:
            pass

    def add_spending(e):
        try:
            val = float(spending_input.value or 0)
            app_logic.data["total_spent"] += val
            with open(SPENDING_LOG, "a") as f:
                f.write(f"{datetime.datetime.now()}: ${val}\n")
            if app_logic.data["daily_budget"] > 0:
                health = 1 - (app_logic.data["total_spent"] / app_logic.data["daily_budget"])
                app_logic.data["budget_health"] = max(0.0, min(1.0, health))
                budget_gauge.controls[0].controls[0].value = app_logic.data["budget_health"]
            app_logic.save_local_data()
            app_logic.user_interacted()
            app_logic.sync_state_to_n8n(message="empty")
            spending_input.value = ""
            page.update()
        except:
            page.update()

    # --- CHAT INTERFACE ---
    chat_history = ft.ListView(expand=True, spacing=10, auto_scroll=True)

    def on_message_send(e):
        if not chat_input.value:
            return
        user_msg = chat_input.value
# Display user message in chat history
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(user_msg, color="black"),
                alignment=ft.alignment.Alignment(1, 0),
                padding=12,
                bgcolor="#FFE5D9",
                border_radius=15
            )
        )
        chat_input.value = ""
        page.update()
        app_logic.user_interacted()

        try:
            
            # Build payload with user message + state snapshot
            payload = {
                "chat": {
                    "message": user_msg,
                    "budget": app_logic.data["daily_budget"],
                    "spent": app_logic.data["total_spent"],
                    "sleep": app_logic.data["sleep_hours"],
                    "new_day": app_logic.data.get("is_new_day", False),
                    "focus_level": app_logic.data.get("focus_level", 0.5),
                    "chill_level": app_logic.data.get("chill_level", 0.5),
                    "budget_health": app_logic.data.get("budget_health", 1.0),
                }
            }
            res = requests.post(N8N_WEBHOOK, json=payload, timeout=5)
            data = res.json()

            # Display agent reply (left-aligned bubble)
            chat_history.controls.append(
                ft.Container(
                    content=ft.Text(data.get("reply", "...")),
                    alignment=ft.alignment.center_left,
                    padding=12,
                    bgcolor="white",
                    border_radius=15,
                    border=ft.border.all(1, "#FFE5D9"),
                )
            )

            # Update gauges if response includes focus/chill values
            if "focus" in data:
                focus_gauge.controls[0].controls[0].value = data["focus"]
                app_logic.data["focus_level"] = data["focus"]
            if "chill" in data:
                chill_gauge.controls[0].controls[0].value = data["chill"]
                app_logic.data["chill_level"] = data["chill"]

            # Sync updated focus/chill to n8n backend
            app_logic.sync_state_to_n8n(message="empty")

        except:
            # Handle unreachable agent gracefully
            chat_history.controls.append(
                ft.Text("Agent unreachable.", color="red", size=10)
            )
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
                                    ft.ElevatedButton("Set", on_click=set_budget),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            ft.Column(
                                [
                                    spending_input,
                                    ft.ElevatedButton("Add", on_click=add_spending),
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
    ft.run(main)