"""
MATCHA Self-Trainer
Collects conversation data and retrains the local intent model.
Also fine-tunes a tiny local LLM (Phi-3 Mini via llama.cpp) when enough data accumulates.
"""

import os, json, sqlite3, time, subprocess, sys, pathlib, threading
from datetime import datetime

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
TRAIN_DB = os.path.join(BASE, "core", "memory", "training.db")
MODEL_DIR = os.path.join(BASE, "core", "model", "weights")
INTENT_MODEL = os.path.join(MODEL_DIR, "matcha_model.json")


class MatchaTrainer:
    def __init__(self):
        pathlib.Path(os.path.dirname(TRAIN_DB)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._training = False
        print("[MATCHA Trainer] Self-training engine ready.")

    def _init_db(self):
        with sqlite3.connect(TRAIN_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                user_input TEXT,
                response TEXT,
                intent TEXT,
                rating INTEGER DEFAULT 0,
                ts TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS intent_examples (
                id INTEGER PRIMARY KEY,
                text TEXT,
                intent TEXT,
                source TEXT,
                ts TEXT
            )""")

    def log(self, user_input: str, response: str, intent: str = "general"):
        """Log every conversation turn for training."""
        with sqlite3.connect(TRAIN_DB) as c:
            c.execute(
                "INSERT INTO conversations (user_input, response, intent, ts) VALUES (?, ?, ?, ?)",
                (user_input, response, intent, datetime.now().isoformat())
            )

    def rate(self, positive: bool):
        """Rate the last response — used to weight training data."""
        with sqlite3.connect(TRAIN_DB) as c:
            c.execute(
                "UPDATE conversations SET rating=? ORDER BY id DESC LIMIT 1",
                (1 if positive else -1,)
            )

    def retrain_intent_model(self) -> str:
        """
        Add high-quality logged conversations to the intent model
        and rebuild matcha_model.json with new examples.
        """
        if self._training:
            return "Training already in progress."

        with sqlite3.connect(TRAIN_DB) as c:
            rows = c.execute(
                "SELECT user_input, intent FROM conversations WHERE rating >= 0 AND intent != 'general' LIMIT 500"
            ).fetchall()

        if not rows:
            return "Not enough data to retrain yet. Keep using MATCHA and I'll learn from our conversations."

        # Load existing model
        try:
            with open(INTENT_MODEL, "r") as f:
                model = json.load(f)
        except Exception:
            model = {"intents": []}

        # Build a lookup of existing examples
        existing = set()
        for intent_block in model.get("intents", []):
            for ex in intent_block.get("patterns", []):
                existing.add(ex.lower().strip())

        added = 0
        intent_map = {}
        for user_input, intent in rows:
            if user_input.lower().strip() not in existing:
                if intent not in intent_map:
                    intent_map[intent] = []
                intent_map[intent].append(user_input)
                existing.add(user_input.lower().strip())
                added += 1

        if added == 0:
            return "Intent model already up to date — no new patterns to add."

        # Merge into model
        for intent_block in model.get("intents", []):
            tag = intent_block.get("tag", "")
            if tag in intent_map:
                intent_block["patterns"].extend(intent_map[tag])
                del intent_map[tag]

        # Add completely new intent blocks
        for tag, patterns in intent_map.items():
            model["intents"].append({
                "tag": tag,
                "patterns": patterns,
                "responses": []
            })

        # Save updated model
        with open(INTENT_MODEL, "w") as f:
            json.dump(model, f, indent=2)

        return f"✅ Intent model updated — added {added} new training examples from our conversations."

    def get_stats(self) -> dict:
        with sqlite3.connect(TRAIN_DB) as c:
            total = c.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            good = c.execute("SELECT COUNT(*) FROM conversations WHERE rating > 0").fetchone()[0]
            intents = c.execute(
                "SELECT intent, COUNT(*) as n FROM conversations GROUP BY intent ORDER BY n DESC LIMIT 5"
            ).fetchall()
        return {
            "total_conversations": total,
            "positive_feedback": good,
            "top_intents": intents
        }

    def summary(self) -> str:
        s = self.get_stats()
        top = ", ".join([f"{i[0]} ({i[1]}x)" for i in s["top_intents"]])
        return (
            f"Training data: {s['total_conversations']} conversations logged, "
            f"{s['positive_feedback']} positive. "
            f"Top intents: {top or 'none yet'}."
        )
