"""
redis_feedback_graph_updater.py
-------------------------------

This script listens to a Redis Pub/Sub channel called 'feedback_channel' for agent feedback messages.
Each feedback message is expected to be a JSON object describing one or more actions to perform on a
knowledge graph stored in a local JSON file (brain_graph.json). Supported actions include adding nodes,
adding edges, updating nodes, deleting nodes, and deleting edges. The script ensures the graph file is
always valid JSON by loading, modifying, and saving it safely.

⚠️ Note: This uses Redis Pub/Sub. Messages are delivered in real-time but are not stored if the script
is offline. For guaranteed reliability, consider switching to a Redis list queue (RPUSH/BLPOP).

Additionally:
    After each modification, the script calls `graph_auto_linker.py` to enrich the graph by automatically
    adding inferred edges between nodes based on semantic similarity.
"""

import redis
import json
import subprocess   # ✅ Used to call the auto-linker script
import os
from dotenv import load_dotenv


# ✅ Get the root folder of brain-api (parent of app_scripts)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ✅ Load environment variables from the project-relative .env file
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

# ✅ Redis connection settings (read from .env for flexibility)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")   # default: localhost
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))     # default: 6379
REDIS_DB   = int(os.getenv("REDIS_DB", 0))          # default: 0

# 🔧 Path to the knowledge graph JSON file inside brain-api/data
GRAPH_FILE = os.path.join(BASE_DIR, "data", "brain_graph.json")

# 🔧 Path to the auto-linker script inside brain-api/app_scripts
AUTO_LINKER_SCRIPT = os.path.join(BASE_DIR, "app_scripts", "graph_auto_linker.py")
def load_graph():
    """Load the knowledge graph from disk. If invalid, return a fresh graph structure."""
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"nodes": [], "edges": []}


def save_graph(graph):
    """Save the knowledge graph back to disk in valid JSON format with indentation."""
    with open(GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)


def apply_single_action(graph, feedback):
    """Apply a single feedback action to the graph."""
    action = feedback.get("action")

    if action == "add_node" and "node" in feedback:
        node = feedback["node"]
        if not any(n["id"] == node["id"] for n in graph["nodes"]):
            graph["nodes"].append(node)
            print(f"🟢 Node added: {node['id']}")

    elif action == "add_edge" and "edge" in feedback:
        edge = feedback["edge"]
        sources = [n["id"] for n in graph["nodes"]]
        if edge["source"] in sources and edge["target"] in sources:
            if not any(
                e.get("source") == edge["source"] and
                e.get("target") == edge["target"] and
                e.get("relation") == edge["relation"]
                for e in graph["edges"]
            ):
                graph["edges"].append(edge)
                print(f"🔗 Edge added: {edge['source']} → {edge['target']} ({edge['relation']})")
        else:
            print(f"⚠️ Edge skipped (missing nodes): {edge}")

    elif action == "update_node" and "node" in feedback:
        for n in graph["nodes"]:
            if n["id"] == feedback["node"]["id"]:
                n.update(feedback["node"])
                print(f"✏️ Node updated: {n['id']}")

    elif action == "delete_node" and "node" in feedback:
        node_id = feedback["node"]["id"]
        graph["nodes"] = [n for n in graph["nodes"] if n["id"] != node_id]
        graph["edges"] = [
            e for e in graph["edges"]
            if e.get("source") != node_id and e.get("target") != node_id
        ]
        print(f"🗑️ Node deleted: {node_id}")

    elif action == "delete_edge" and "edge" in feedback:
        edge = feedback["edge"]
        before = len(graph["edges"])
        graph["edges"] = [
            e for e in graph["edges"]
            if not (
                e.get("source") == edge.get("source") and
                e.get("target") == edge.get("target") and
                e.get("relation") == edge.get("relation")
            )
        ]
        if len(graph["edges"]) < before:
            print(f"🗑️ Edge deleted: {edge['source']} → {edge['target']} ({edge['relation']})")
        else:
            print(f"⚠️ Edge not found for deletion: {edge}")

    return graph


def apply_feedback(graph, feedback):
    """Apply feedback to the graph (single or grouped actions)."""
    if "actions" in feedback and isinstance(feedback["actions"], list):
        for action_item in feedback["actions"]:
            try:
                graph = apply_single_action(graph, action_item)
            except Exception as e:
                print(f"⚠️ Failed action: {action_item} → {e}")
    else:
        try:
            graph = apply_single_action(graph, feedback)
        except Exception as e:
            print(f"⚠️ Failed action: {feedback} → {e}")
    return graph


def run_auto_linker():
    """Call the auto-linker script to enrich the graph."""
    try:
        subprocess.run(["python", AUTO_LINKER_SCRIPT], check=True)
        print("🤖 Auto-linker executed successfully.")
    except Exception as e:
        print(f"⚠️ Auto-linker failed: {e}")


def listen_feedback():
    """Listen to Redis channel and apply feedback messages continuously."""
        # ✅ Create Redis client using variables
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    # 👇 Debug: check if Redis settings are loaded correctly
    print(f"Redis connected to {REDIS_HOST}:{REDIS_PORT}, DB={REDIS_DB}")

    pubsub = r.pubsub()
    pubsub.subscribe("feedback_channel")

    print("🚀 Listening on Redis channel: feedback_channel")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                feedback = json.loads(message["data"])
                graph = load_graph()
                graph = apply_feedback(graph, feedback)
                save_graph(graph)
                print("✅ Graph file updated.")

                # 🔧 Call auto-linker after every modification
                run_auto_linker()

            except Exception as e:
                print("⚠️ Invalid feedback:", e)


if __name__ == "__main__":
    # This will keep running until you manually stop it (Ctrl+C)
    listen_feedback()