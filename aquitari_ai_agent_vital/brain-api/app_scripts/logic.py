"""
AQUITARI REASONING ENGINE - LOGICAL CORE
----------------------------------------
Description:
This script acts as the 'Neural Map' of the agent. It transforms a static 
JSON Knowledge Graph into an active reasoning system using NetworkX.

Capabilities:
1. Graph Construction: Converts JSON entities and relations into a Directed Graph (DiGraph).
2. Deterministic Diagnosis: Predicts behavioral risks based on biological inputs.
3. Pathfinding: Automatically detects if a user state leads to 'Safe Mode' triggers.
4. Explainability: Traces the logic steps taken so the agent can explain its "Why".
5. Auto-Reload: Monitors the Knowledge Graph JSON for changes and reloads automatically.

File: app/logic.py
"""

import json
import os
import logging
import networkx as nx
from typing import List, Dict, Any
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# -------- LOGGING CONFIGURATION --------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Aquitari_Brain")

# -------- DIRECTORY CONFIGURATION --------
# ✅ Get the root folder of brain-api (parent of app_scripts)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔧 Path to your graph JSON file inside brain-api/data
KG_FILE = os.path.join(BASE_DIR, "data", "brain_graph.json")


class AquitariBrain:
    """
    The core reasoning engine for Aquitari. 
    Uses a Directed Graph (NetworkX) to map how biological states 
    (like low sleep) lead to financial risks and trigger safety protocols.
    """

    def __init__(self, kg_path: str = KG_FILE):
        """
        Initializes the brain:
        - Loads the knowledge graph.
        - Starts the file watcher for auto-reload.
        """
        self.kg_path = kg_path
        self.G = nx.DiGraph()
        self._load_knowledge_graph()
        self._start_file_watcher()

    def _load_knowledge_graph(self):
        """Load the JSON knowledge graph into the NetworkX graph."""
        if not os.path.exists(self.kg_path):
            logger.error(f"CRITICAL: Knowledge Graph file not found at {self.kg_path}")
            return

        try:
            with open(self.kg_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            system_id = data.get("system_id", "unknown")
            version = data.get("metadata", {}).get("version", "0.0")
            logger.info(f"Loading Brain: {system_id} (v{version})")

            # Clear existing graph to avoid duplicates
            self.G.clear()

            # Add nodes from JSON
            for node in data.get("nodes", []):
                self.G.add_node(
                    node["id"], 
                    type=node.get("type"), 
                    description=node.get("description")
                )

            # Add edges from JSON
            for edge in data.get("edges", []):
                self.G.add_edge(
                    edge["source"], 
                    edge["target"], 
                    relation=edge.get("relation")
                )

            logger.info(f"Brain Online: {self.G.number_of_nodes()} nodes loaded.")

        except json.JSONDecodeError:
            logger.error("CRITICAL: JSON file is corrupted or formatted incorrectly.")
        except Exception as e:
            logger.error(f"Failed to initialize brain: {str(e)}")

    # -------- REASONING METHODS --------
    def diagnose(self, state_id: str) -> Dict[str, Any]:
        """Analyzes a state and predicts risks and safety triggers."""
        if state_id not in self.G:
            logger.warning(f"Query received for unknown state: {state_id}")
            return {
                "error": f"State '{state_id}' is not mapped in the Knowledge Graph.", 
                "activates_safe_mode": False
            }

        # Identify direct downstream risks
        risks = []
        for successor in self.G.successors(state_id):
            relation = self.G.edges[state_id, successor].get("relation")
            risks.append({"risk": successor, "relation": relation})

        # Evaluate if this state activates safe_mode
        activates_safe_mode = False
        try:
            if self.G.has_node("safe_mode") and nx.has_path(self.G, state_id, "safe_mode"):
                activates_safe_mode = True
        except Exception:
            pass 

        return {
            "current_state": state_id,
            "predicted_risks": risks,
            "activates_safe_mode": activates_safe_mode,
            "reasoning_path": self._explain_reasoning(state_id)
        }

    def _explain_reasoning(self, start_node: str) -> List[str]:
        """Generates a human-readable trace of the reasoning path."""
        explanation = []
        edges = list(nx.bfs_edges(self.G, start_node, depth_limit=2))
        for u, v in edges:
            rel = self.G.edges[u, v].get("relation", "leads to")
            explanation.append(f"{u} --[{rel}]--> {v}")
        return explanation

    # -------- AUTO-RELOAD ON FILE CHANGE --------
    class _GraphChangeHandler(FileSystemEventHandler):
        """Internal handler to watch for JSON file modifications."""
        def __init__(self, brain_instance):
            self.brain = brain_instance

        def on_modified(self, event):
            # Only reload the specific brain_graph.json
            if event.src_path.endswith("brain_graph.json"):
                logger.info(f"Detected change in {event.src_path}, reloading Knowledge Graph...")
                self.brain._load_knowledge_graph()

    def _start_file_watcher(self):
        """Starts a background thread to monitor the JSON file for changes."""
        event_handler = self._GraphChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, os.path.dirname(self.kg_path), recursive=False)
        observer_thread = Thread(target=observer.start, daemon=True)
        observer_thread.start()
        logger.info("Started auto-reload file watcher for Knowledge Graph.")

# -------- LOCAL UNIT TEST --------
if __name__ == "__main__":
    aquitari = AquitariBrain()
    print("\n--- [DEBUG] TESTING BRAIN DIAGNOSIS: 'low_rest' ---")
    result = aquitari.diagnose("low_rest")
    print(json.dumps(result, indent=2))
