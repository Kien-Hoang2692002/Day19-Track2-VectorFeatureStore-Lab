from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import re


@dataclass
class MemoryChunk:
    text: str
    user_id: str
    tokens: set[str]


class HybridMemoryAgent:
    """Minimal hybrid-memory POC with in-memory vector + feature stores."""

    def __init__(self) -> None:
        self.vector_store: List[MemoryChunk] = []
        self.feature_store: Dict[str, Dict[str, object]] = {}
        self.synonyms = {
            "kubernetes": ["k8s", "container", "containers", "orchestration"],
            "autoscaling": ["tự", "động", "mở", "rộng", "hạ", "tầng", "scale"],
            "cloud": ["đám", "mây", "ha", "tang", "infrastructure"],
            "security": ["bao", "mật", "bảo", "mật", "compliance", "iam", "zero", "trust"],
            "ai": ["llm", "rag", "agent", "embedding"],
        }

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Add a new piece of episodic memory for this user."""
        chunks = self._chunk_text(text)
        for chunk in chunks:
            self.vector_store.append(
                MemoryChunk(text=chunk, user_id=user_id, tokens=self._tokenize(chunk))
            )
        self._bootstrap_profile_if_needed(user_id)
        self._update_topic_affinity(text, user_id)

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Retrieve top-K memories + user profile features -> assembled context."""
        self._bootstrap_profile_if_needed(user_id)
        self._push_recent_query(query, user_id)
        profile = self.feature_store[user_id]
        memories = self._hybrid_search(query, user_id, top_k=3)

        topic_affinity = profile["topic_affinity"]
        top_topic = max(topic_affinity, key=topic_affinity.get)
        top_memories = memories or ["Không có episodic memory đủ liên quan."]

        lines = [
            f"User: {user_id}",
            f"Preferred language: {profile['preferred_language']}",
            f"Reading speed: {profile['reading_speed_wpm']} wpm",
            f"Top topic affinity: {top_topic}={topic_affinity[top_topic]:.2f}",
            f"Recent activity (last hour view): {', '.join(profile['queries_last_hour']) or 'none'}",
            f"Fatigue signal: {profile['fatigue_signal']}",
            "Top memories:",
        ]
        lines.extend(f"- {memory}" for memory in top_memories)
        return "\n".join(lines)

    def _chunk_text(self, text: str, max_words: int = 28) -> List[str]:
        words = text.split()
        if len(words) <= max_words:
            return [text.strip()]
        chunks = []
        step = max_words - 6
        for start in range(0, len(words), step):
            chunk = " ".join(words[start : start + max_words]).strip()
            if chunk:
                chunks.append(chunk)
        return chunks

    def _tokenize(self, text: str) -> set[str]:
        normalized = self._normalize(text)
        tokens = set(normalized.split())
        expanded = set(tokens)
        for canonical, aliases in self.synonyms.items():
            alias_set = {self._normalize(alias) for alias in aliases}
            if canonical in tokens or tokens & alias_set:
                expanded.add(canonical)
                expanded |= alias_set
        return {token for token in expanded if token}

    def _normalize(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^0-9a-zA-ZÀ-ỹ\s]", " ", text)
        text = text.replace("đ", "d")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _bootstrap_profile_if_needed(self, user_id: str) -> None:
        if user_id in self.feature_store:
            return
        self.feature_store[user_id] = {
            "preferred_language": "mix",
            "reading_speed_wpm": 220,
            "topic_affinity": {"cloud": 0.55, "ai": 0.30, "security": 0.25},
            "active_hour_bucket": "late_night",
            "queries_last_hour": [],
            "fatigue_signal": False,
        }

    def _update_topic_affinity(self, text: str, user_id: str) -> None:
        profile = self.feature_store[user_id]
        tokens = self._tokenize(text)
        affinity = profile["topic_affinity"]
        for topic in affinity:
            related = {topic} | {self._normalize(x) for x in self.synonyms.get(topic, [])}
            if tokens & related:
                affinity[topic] = min(1.0, affinity[topic] + 0.12)

    def _push_recent_query(self, query: str, user_id: str) -> None:
        profile = self.feature_store[user_id]
        recent = profile["queries_last_hour"]
        recent.append(query)
        if len(recent) > 5:
            del recent[0]
        profile["fatigue_signal"] = len(query.split()) > 7 and profile["active_hour_bucket"] == "late_night"

    def _hybrid_search(self, query: str, user_id: str, top_k: int = 3) -> List[str]:
        q_tokens = self._tokenize(query)
        scored: List[tuple[float, str]] = []
        for memory in self.vector_store:
            if memory.user_id != user_id:
                continue
            overlap = len(q_tokens & memory.tokens)
            if overlap == 0:
                continue
            density = overlap / max(len(q_tokens), 1)
            score = overlap + density
            scored.append((score, memory.text))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in scored[:top_k]]
