"""
redis_feedback_graph_updater.py

This script listens to a Redis Pub/Sub channel called 'feedback_channel' for agent feedback messages.
Each feedback message is expected to be a JSON object describing an action to perform on a knowledge graph
stored in a local JSON file (brain_graph.json). Supported actions include adding nodes, adding edges,
updating nodes, and deleting nodes. The script ensures the graph file is always valid JSON by loading,
modifying, and saving it safely.


"""

import redis
import json

# Path to the knowledge graph JSON file
# TODO: Replace with relative path
GRAPH_FILE = "path_to_brain_graph.json_file"

def load_graph():
    """
    Load the knowledge graph from disk.
    If the file does not exist or contains invalid JSON, return a fresh graph structure.
    """
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"nodes": [], "edges": []}

def save_graph(graph):
    """
    Save the knowledge graph back to disk in valid JSON format with indentation.
    """
    with open(GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)

def apply_feedback(graph, feedback):
    """
    Apply a feedback action to the graph.
    Supported actions:
      - add_node: add a new node
      - add_edge: add a new edge
      - update_node: update an existing node by ID
      - delete_node: remove a node by ID
    """
    action = feedback.get("action")

    if action == "add_node" and "node" in feedback:
        graph["nodes"].append(feedback["node"])

    elif action == "add_edge" and "edge" in feedback:
        graph["edges"].append(feedback["edge"])

    elif action == "update_node" and "node" in feedback:
        for n in graph["nodes"]:
            if n["id"] == feedback["node"]["id"]:
                n.update(feedback["node"])

    elif action == "delete_node" and "node" in feedback:
        graph["nodes"] = [n for n in graph["nodes"] if n["id"] != feedback["node"]["id"]]

    # Additional actions can be added here as needed

    return graph

def listen_feedback():
    """
    Connect to Redis, subscribe to the 'feedback_channel', and listen for feedback messages.
    Each message is parsed as JSON and applied to the knowledge graph.
    """
    r = redis.Redis(host="localhost", port=6379, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe("feedback_channel")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                feedback = json.loads(message["data"])
                graph = load_graph()
                graph = apply_feedback(graph, feedback)
                save_graph(graph)
                print("✅ Graph updated with feedback:", feedback)
            except Exception as e:
                print("⚠️ Invalid feedback:", e)

if __name__ == "__main__":
    # Start listening for feedback messages
    listen_feedback()