"""
NEURAL STREAM - The Nervous System
==================================
File-based Event Bus (NDJSON).
Provides thread-safe writing and efficient reading for the Dashboard.
"""

import os
import json
import time
from pathlib import Path
from typing import List, Generator, Optional
from .hive_protocol import NeuralEvent

class NeuralStreamConfig:
    # Defaults; should be set by hive_commons.config
    STREAM_PATH = Path("logs/neural_stream.jsonl")

def configure_stream_path(path: Path):
    NeuralStreamConfig.STREAM_PATH = path

class NeuralStreamWriter:
    """
    Write-only interface for Agents to append events to the stream.
    Designed to be robust and crash-proof.
    """
    def __init__(self, agent_name: str, mission_id: Optional[str] = None):
        self.agent_name = agent_name
        self.mission_id = mission_id
        self._ensure_dir()

    def _ensure_dir(self):
        if NeuralStreamConfig.STREAM_PATH.parent:
            NeuralStreamConfig.STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)

    def push(self, event_type, payload: dict) -> NeuralEvent:
        """Create and push an event in one go."""
        event = NeuralEvent(
            type=event_type,
            agent=self.agent_name,
            mission_id=self.mission_id,
            payload=payload
        )
        self.write(event)
        return event

    def write(self, event: NeuralEvent):
        """Append event to the JSONL file."""
        try:
            # Atomic append (os.open with O_APPEND is atomic on POSIX, usually fine on Windows for small logs)
            # For high concurrency on Windows we might need a lock, but for L1 Lite Mode, 
            # standard append is sufficient. 
            # We use 'utf-8' explicitly.
            with open(NeuralStreamConfig.STREAM_PATH, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            # Fallback: Don't crash the agent if logging fails
            print(f"!! CRITICAL: Failed to write to Neural Stream: {e}")

class NeuralStreamReader:
    """
    Read-only interface for Dashboard/UI.
    Optimized for tailing large files.
    """
    def __init__(self, path: Path = None):
        self.path = path or NeuralStreamConfig.STREAM_PATH

    def tail(self, lines: int = 50) -> List[NeuralEvent]:
        """
        Efficiently read the last N lines of the stream.
        """
        if not self.path.exists():
            return []

        # TODO: Implement true reverse reading for huge files if needed.
        # For now, reading all lines is okay for files < 10MB.
        # If file grows, we add log rotation or seek logic.
        
        events = []
        try:
            # Simple implementation for < 50MB logs
            with open(self.path, "r", encoding="utf-8") as f:
                # Read all lines is expensive if huge, but robust for now.
                # Optimization: Seek to end and read backwards? 
                # Let's stick to standard readlines for Phase 1 MVP.
                all_lines = f.readlines()
                
                # Take last N
                target_lines = all_lines[-lines:] if lines > 0 else []
                
                for line in target_lines:
                    line = line.strip()
                    if not line: continue
                    try:
                        events.append(NeuralEvent.from_json(line))
                    except json.JSONDecodeError:
                        continue # Skip corrupted lines
        except Exception as e:
            print(f"Stream Read Error: {e}")
            
        return events

    def get_events_since(self, timestamp: float) -> List[NeuralEvent]:
        """Return events newer than a timestamp."""
        # This is inefficient for huge files (O(N)), but sufficient for the Dashboard 
        # since we only care about the vivid "Now".
        events = self.tail(200) # Look back 200 events
        return [e for e in events if e.timestamp > timestamp]
