"""
NoetixAgent Memory — persistent memory with FTS-style search (inspired by Hermes).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger("noetix.memory")


class MemoryEntry:
    def __init__(self, content: str, tags: List[str] = None, timestamp: str = None):
        self.content = content
        self.tags = tags or []
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {"content": self.content, "tags": self.tags, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: Dict) -> "MemoryEntry":
        return cls(content=d["content"], tags=d.get("tags", []), timestamp=d.get("timestamp"))


class MemoryManager:
    def __init__(self, memory_dir: Path, max_entries: int = 500):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "memory.json"
        self.max_entries = max_entries
        self._entries: List[MemoryEntry] = []
        self._load()

    def _load(self):
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())
                self._entries = [MemoryEntry.from_dict(e) for e in data]
            except Exception as e:
                logger.warning(f"Memory load error: {e}")

    def _save(self):
        try:
            self.memory_file.write_text(
                json.dumps([e.to_dict() for e in self._entries], indent=2)
            )
        except Exception as e:
            logger.warning(f"Memory save error: {e}")

    def add(self, content: str, tags: List[str] = None):
        if not content or len(content.strip()) < 10:
            return
        entry = MemoryEntry(content=content.strip()[:500], tags=tags or [])
        self._entries.append(entry)
        # Prune
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
        self._save()

    def search(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        query_lower = query.lower()
        scored = []
        for entry in self._entries:
            score = sum(
                1 for word in query_lower.split()
                if word in entry.content.lower()
            )
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def get_context(self, max_entries: int = 10) -> str:
        if not self._entries:
            return ""
        recent = self._entries[-max_entries:]
        lines = []
        for e in recent:
            ts = e.timestamp[:16] if e.timestamp else ""
            lines.append(f"[{ts}] {e.content[:200]}")
        return "\n".join(lines)

    def clear(self):
        self._entries.clear()
        self._save()

    def save_skill(self, skill_name: str, content: str):
        """Persist a learned skill to disk."""
        skills_dir = self.memory_dir / "skills"
        skills_dir.mkdir(exist_ok=True)
        (skills_dir / f"{skill_name}.md").write_text(content)

    def load_skill(self, skill_name: str) -> Optional[str]:
        path = self.memory_dir / "skills" / f"{skill_name}.md"
        return path.read_text() if path.exists() else None
