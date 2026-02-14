"""
HIVE PROTOCOL - The Language of Thought
========================================
Defines the strictly typed schema for the "Glass Box" Neural Stream.
Every event in the system must conform to this protocol.
"""

import time
import uuid
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

class NeuralEventType(str, Enum):
    """
    Types of events in the Neural Stream.
    Used for UI filtering and coloring.
    """
    # Lifecycle
    BOOT = "BOOT"
    SHUTDOWN = "SHUTDOWN"
    
    # Research / Reasoning (Glass Box)
    RESEARCH_INIT = "RESEARCH_INIT"       # 🚀 Mission Start
    THOUGHT = "THOUGHT"                   # 🤔 Internal Monologue
    PLAN = "PLAN"                         # 📋 Strategy/Steps
    ACTION = "ACTION"                     # ⚡ Tool Execution / External Call
    OBSERVATION = "OBSERVATION"           # 👁️ Result from Action
    SYNTHESIS = "SYNTHESIS"               # 🧪 Compiling results
    RESULT = "RESULT"                     # ✅ Final Deliverable
    
    # State
    ERROR = "ERROR"                       # ❌ Critical Failure
    WARNING = "WARNING"                   # ⚠️ Non-critical Issue
    INFO = "INFO"                         # ℹ️ General Info

@dataclass
class NeuralEvent:
    """
    A single atom of thought or action in the Hive.
    Serialized to JSONL in the Neural Stream.
    """
    type: NeuralEventType
    agent: str                  # Who generated this? (e.g. "ResearchAgent", "Hive")
    payload: Dict[str, Any]     # The actual content
    
    # Metadata (Auto-filled)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    mission_id: Optional[str] = None  # To group events by research task
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps({
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type.value,
            "agent": self.agent,
            "mission_id": self.mission_id,
            "payload": self.payload
        }, ensure_ascii=False)

    @staticmethod
    def from_json(json_str: str) -> 'NeuralEvent':
        """Deserialize from valid JSON string."""
        data = json.loads(json_str)
        return NeuralEvent(
            type=NeuralEventType(data.get("type", "INFO")),
            agent=data.get("agent", "Unknown"),
            payload=data.get("payload", {}),
            id=data.get("id"),
            timestamp=data.get("timestamp"),
            mission_id=data.get("mission_id")
        )
