"""
graph_auto_linker.py
--------------------

Description:
    This script loads a knowledge graph from a JSON file, analyzes node similarity
    using two methods:
        1. TF-IDF vectorization + cosine similarity (baseline transparency).
        2. SentenceTransformer embeddings + cosine similarity (semantic inference).
    For embedding-based candidate pairs, instead of assigning a generic relation,
    the script sends the pair to a webhook (relation classifier agent) to determine
    the most accurate relation type. If the agent fails or returns invalid JSON,
    the script falls back to a default relation "UNKNOWN_RELATION".

Usage:
    - Place your graph JSON file at the desired location.
    - Update the GRAPH_PATH variable below to point to your file.
    - Run the script: python graph_auto_linker.py
    - The script will update the graph with inferred edges and overwrite the file.

Notes:
    - Threshold controls how strict the similarity check is (default: 0.35).
    - Webhook URL must be reachable; otherwise, fallback relation is used.
"""

import json
import requests
import os
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util

# ✅ Get the root folder of brain-api (we move up from app_scripts to its parent)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔧 Path to your graph JSON file inside brain-api/data
GRAPH_PATH = os.path.join(BASE_DIR, "data", "brain_graph.json")

# Load embedding model once (lightweight, fast)
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# ✅ Load environment variables from the project-relative .env file
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

# ✅ Read sensitive values from .env
WEBHOOK_URL = os.getenv("N8N_WEBHOOK2")   # Unified webhook
# 👇 Debug: check if the variables are actually loaded
print("Webhook URL from env:", WEBHOOK_URL)

def load_graph(filename):
    """Load the graph JSON file."""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_graph(graph, filename):
    """Save the updated graph back to JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)


def build_text_representation(node):
    """Combine node id and attributes into a text string for similarity."""
    parts = [node.get("id", ""), node.get("description", "")]
    attrs = node.get("attributes", {})
    for k, v in attrs.items():
        if isinstance(v, list):
            parts.extend(v)
        else:
            parts.append(str(v))
    return " ".join(parts)


def edge_exists(edges, source, target, relation):
    """Check if an edge already exists in the graph."""
    return any(
        e.get("source") == source and e.get("target") == target and e.get("relation") == relation
        for e in edges
    )


def clean_agent_output(text: str) -> str:
    """Remove backticks, language hints, and whitespace from agent output."""
    # Strip triple backticks and language markers like ```json
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
    # Remove leading 'json' or similar markers
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return text


def ask_agent_relation(source, target, source_desc, target_desc):
    """Send candidate pair to webhook and return relation or fallback."""
    payload = {
        "source": source,
        "target": target,
        "question": f"What is the relation between {source} and {target}?",
        "source_description": source_desc,
        "target_description": target_desc,
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)

        # 🔎 Debug: show raw response text
        print(f"🔎 Raw webhook response for {source} ↔ {target}: {response.text}")

        data = response.json()

        # Case 1: agent returns clean JSON
        if isinstance(data, dict) and "relation" in data:
            return data["relation"]

        # Case 2: agent wraps JSON inside "output"
        if isinstance(data, dict) and "output" in data:
            try:
                inner_text = clean_agent_output(data["output"])
                inner = json.loads(inner_text)
                if "relation" in inner:
                    return inner["relation"]
            except Exception as e:
                print(f"⚠️ Failed to parse inner output: {e}")

        # Case 3: agent returns a list with "output"
        if isinstance(data, list) and len(data) > 0 and "output" in data[0]:
            try:
                inner_text = clean_agent_output(data[0]["output"])
                inner = json.loads(inner_text)
                if "relation" in inner:
                    return inner["relation"]
            except Exception as e:
                print(f"⚠️ Failed to parse inner output in list: {e}")

        print(f"⚠️ Invalid agent response for {source} ↔ {target}, fallback used.")
        return "UNKNOWN_RELATION"

    except Exception as e:
        print(f"⚠️ Webhook error for {source} ↔ {target}: {e}, fallback used.")
        return "UNKNOWN_RELATION"


def auto_link_tfidf(graph, threshold=0.35):
    """Baseline keyword similarity using TF-IDF."""
    nodes = graph.get("nodes", [])
    edges = graph.setdefault("edges", [])

    corpus = [build_text_representation(node) for node in nodes]
    ids = [node["id"] for node in nodes]

    vectorizer = TfidfVectorizer().fit_transform(corpus)
    similarity_matrix = cosine_similarity(vectorizer)

    new_edges = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            sim = similarity_matrix[i][j]
            if sim >= threshold:
                if not edge_exists(edges, ids[i], ids[j], "RELATED_TFIDF"):
                    edge = {
                        "source": ids[i],
                        "target": ids[j],
                        "relation": "RELATED_TFIDF"
                    }
                    edges.append(edge)
                    new_edges += 1
                    print(f"🟢 [TF-IDF] {ids[i]} ↔ {ids[j]} (similarity={sim:.2f})")

    print(f"📊 TF-IDF edges added: {new_edges}")
    return graph


def auto_link_embeddings(graph, threshold=0.35):
    """Semantic similarity using SentenceTransformer embeddings + agent webhook."""
    nodes = graph.get("nodes", [])
    edges = graph.setdefault("edges", [])

    corpus = [build_text_representation(node) for node in nodes]
    ids = [node["id"] for node in nodes]

    embeddings = EMBED_MODEL.encode(corpus, convert_to_tensor=True)
    similarity_matrix = util.cos_sim(embeddings, embeddings)

    new_edges = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            sim = similarity_matrix[i][j].item()
            if sim >= threshold:
                relation = ask_agent_relation(
                    ids[i], ids[j],
                    nodes[i].get("description", ""), nodes[j].get("description", "")
                )
                if not edge_exists(edges, ids[i], ids[j], relation):
                    edge = {
                        "source": ids[i],
                        "target": ids[j],
                        "relation": relation
                    }
                    edges.append(edge)
                    new_edges += 1
                    print(f"🤖 [Embedding] {ids[i]} ↔ {ids[j]} (relation={relation}, similarity={sim:.2f})")

    print(f"📊 Embedding edges added: {new_edges}")
    return graph


if __name__ == "__main__":
    graph = load_graph(GRAPH_PATH)

    # Run both methods
    graph = auto_link_tfidf(graph, threshold=0.35)
    graph = auto_link_embeddings(graph, threshold=0.35)

    save_graph(graph, GRAPH_PATH)
    print("✅ Graph updated with enriched relations (TF-IDF + Agent).")