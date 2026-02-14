"""
CIRCUIT_BREAKER - Self-Healing Protocol for Sovereign Hive
==========================================================
Detects failure loops, blocks stuck missions, and triggers recovery.

Part of hive_commons — MidOS shared infrastructure.

CRITERIOS DE AUTO-RECUPERACION:
1. Si una mision falla N veces consecutivas -> BLOCK y pasar a siguiente
2. Si todas las misiones fallan -> PHOENIX PROTOCOL (reset limpio)
3. Si sistema idle por X tiempo -> Auto-generar mision segura
4. Si consensus nunca llega -> Timeout + degradar a T2 (auto-approve)
"""
import json
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import structlog

# Use hive_commons config for paths
from .config import (
    L1_ROOT, L1_LOGS,
    ensure_env
)

ensure_env()

log = structlog.get_logger("hive_commons.circuit_breaker")

# Paths derived from config
STATE_FILE = L1_ROOT / "knowledge" / "SYSTEM" / "circuit_breaker_state.json"
LOG_FILE = L1_LOGS / "neural_stream.jsonl"

# THRESHOLDS (CRITERIOS)
MAX_CONSECUTIVE_FAILURES = 3      # Bloquear mision despues de N fallos
CONSENSUS_TIMEOUT_SECONDS = 120   # Timeout para esperar consenso
IDLE_THRESHOLD_SECONDS = 300      # Tiempo sin actividad para auto-generar
PHOENIX_THRESHOLD = 5             # Misiones bloqueadas para activar Phoenix


class CircuitBreaker:
    """
    Circuit Breaker Pattern para Sovereign Hive.
    Monitorea fallos, bloquea loops, y activa recuperacion automatica.
    """

    def __init__(self):
        self.state_file = STATE_FILE
        self.state = self._load_state()
        self.sword = None  # Lazy load Claude Sword

    def _get_sword(self):
        """Claude Sword was in src.cortex (removed). Returns None."""
        return self.sword

    def _load_state(self) -> Dict:
        """Carga estado persistente."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "mission_failures": {},
            "blocked_missions": [],
            "last_activity": time.time(),
            "phoenix_activations": 0,
            "total_recoveries": 0
        }

    def _save_state(self):
        """Persiste estado."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding='utf-8')

    def _log(self, event: str, message: str, details: dict = None):
        """Log al neural stream."""
        entry = {
            "timestamp": time.time(),
            "event": event,
            "message": message,
            "details": details or {},
            "component": "CIRCUIT_BREAKER"
        }
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            log.info(event.lower(), message=message, **details or {})
        except Exception as e:
            log.error("log_failed", error=str(e))

    def record_failure(self, mission_id: str, reason: str = "timeout") -> bool:
        """
        Registra un fallo de mision.
        Returns: True si la mision debe ser bloqueada.
        """
        if mission_id not in self.state["mission_failures"]:
            self.state["mission_failures"][mission_id] = 0

        self.state["mission_failures"][mission_id] += 1
        count = self.state["mission_failures"][mission_id]

        self._log("FAILURE_RECORDED", f"Mission {mission_id} failed ({count}/{MAX_CONSECUTIVE_FAILURES})",
                  {"reason": reason, "count": count})

        if count >= MAX_CONSECUTIVE_FAILURES:
            sword = self._get_sword()
            if sword:
                judgment = sword.judge_mission(mission_id, {
                    "failures": count,
                    "elapsed_seconds": 0,
                    "last_error": reason,
                    "mission_type": self._get_base_mission_id(mission_id)
                })

                decision = judgment.get("decision", "ABORT")
                if decision == "ABORT":
                    self._block_mission(mission_id, reason)
                    return True
                elif decision == "PAUSE":
                    self.state["mission_failures"][mission_id] = max(0, count - 1)
                    self._save_state()
                    return False
            else:
                self._block_mission(mission_id, reason)
                return True

        self._save_state()
        return False

    def record_success(self, mission_id: str):
        """Registra exito - resetea contador de fallos."""
        if mission_id in self.state["mission_failures"]:
            del self.state["mission_failures"][mission_id]
        self.state["last_activity"] = time.time()
        self._save_state()
        self._log("SUCCESS_RECORDED", f"Mission {mission_id} succeeded, counter reset")

    def _block_mission(self, mission_id: str, reason: str):
        """Bloquea una mision permanentemente."""
        if mission_id not in self.state["blocked_missions"]:
            self.state["blocked_missions"].append(mission_id)

        if mission_id in self.state["mission_failures"]:
            del self.state["mission_failures"][mission_id]

        self._save_state()
        self._log("MISSION_BLOCKED", f"Mission {mission_id} blocked after repeated failures",
                  {"reason": reason, "total_blocked": len(self.state["blocked_missions"])})

        if len(self.state["blocked_missions"]) >= PHOENIX_THRESHOLD:
            self._activate_phoenix()

    def is_blocked(self, mission_id: str) -> bool:
        """Verifica si una mision esta bloqueada."""
        base_id = self._get_base_mission_id(mission_id)
        return any(base_id in blocked for blocked in self.state["blocked_missions"])

    def _get_base_mission_id(self, mission_id: str) -> str:
        """Extrae el ID base sin timestamp."""
        parts = mission_id.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
        return mission_id

    def _activate_phoenix(self):
        """PHOENIX PROTOCOL: Reset completo del sistema de misiones."""
        self._log("PHOENIX_ACTIVATED", "Too many blocked missions. Initiating self-healing.")

        self._clean_proposal_queues()
        self._reset_consensus_state()

        old_blocked = self.state["blocked_missions"].copy()
        self.state["blocked_missions"] = []
        self.state["mission_failures"] = {}
        self.state["phoenix_activations"] += 1
        self.state["total_recoveries"] += 1

        self._inject_safe_mission()
        self._save_state()

        self._log("PHOENIX_COMPLETE", f"System recovered. Cleared {len(old_blocked)} blocked missions.",
                  {"phoenix_count": self.state["phoenix_activations"]})

    def _clean_proposal_queues(self):
        """Limpia propuestas pendientes que estan causando loops."""
        dirs_to_clean = [
            L1_ROOT / "synapse" / "proposals",
        ]

        cleaned = 0
        for d in dirs_to_clean:
            if d.exists():
                for f in d.glob("PROPOSAL_ARS_*.md"):
                    try:
                        archive = d.parent / "archive" / "phoenix_cleaned"
                        archive.mkdir(parents=True, exist_ok=True)
                        f.rename(archive / f"{int(time.time())}_{f.name}")
                        cleaned += 1
                    except OSError:
                        pass

        self._log("QUEUE_CLEANED", f"Moved {cleaned} stuck proposals to archive")

    def _reset_consensus_state(self):
        """Limpia acuerdos pendientes que nunca llegaran a consenso."""
        consensus_file = L1_ROOT / "synapse" / "CONSENSUS_STATE.json"
        if consensus_file.exists():
            try:
                state = json.loads(consensus_file.read_text(encoding='utf-8'))
                pending = [k for k, v in state.get("agreements", {}).items()
                          if v.get("status") == "PENDING"]
                state["agreements"] = {}
                consensus_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
                self._log("CONSENSUS_RESET", f"Cleared {len(pending)} pending agreements")
            except (json.JSONDecodeError, OSError):
                pass

    def _inject_safe_mission(self):
        """Inyecta una mision segura para reiniciar el ciclo."""
        safe_directive = {
            "id": f"PHOENIX_RESTART_{int(time.time())}",
            "source": "T0_SOVEREIGN",
            "target": "L1_MIDOS",
            "type": "RESEARCH_CYCLE",
            "priority": "NORMAL",
            "payload": {
                "mode": "SINGLE",
                "description": "Phoenix Recovery - Safe restart with status check"
            },
            "timestamp": int(time.time())
        }

        inbox = L1_ROOT / "knowledge" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        directive_file = inbox / f"directive_phoenix_{int(time.time())}.json"
        directive_file.write_text(json.dumps(safe_directive, indent=2), encoding='utf-8')

        self._log("SAFE_MISSION_INJECTED", "Phoenix recovery directive sent to inbox")

    def check_idle_and_recover(self) -> bool:
        """Verifica si el sistema esta idle y necesita auto-generar trabajo."""
        idle_time = time.time() - self.state["last_activity"]

        if idle_time > IDLE_THRESHOLD_SECONDS:
            self._log("IDLE_DETECTED", f"System idle for {int(idle_time)}s. Generating work.")
            self._generate_idle_mission()
            self.state["last_activity"] = time.time()
            self._save_state()
            return True

        return False

    def _generate_idle_mission(self):
        """Genera una mision basada en el estado actual del sistema."""
        description = "Routine system health and status verification"

        directive = {
            "id": f"IDLE_RECOVERY_{int(time.time())}",
            "source": "T0_SOVEREIGN",
            "target": "L1_MIDOS",
            "type": "USER_COMMAND",
            "priority": "NORMAL",
            "payload": {
                "action": description,
                "content": description,
                "mission_type": "SYSTEM_HEALTH"
            },
            "timestamp": int(time.time())
        }

        inbox = L1_ROOT / "knowledge" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        directive_file = inbox / f"CMD_idle_recovery_{int(time.time())}.json"
        directive_file.write_text(json.dumps(directive, indent=2), encoding='utf-8')

        self._log("IDLE_MISSION_GENERATED", "Generated SYSTEM_HEALTH mission")

    def check_consensus_timeout(self, proposal_id: str, created_at: float) -> str:
        """Verifica si un proposal ha excedido el timeout de consenso."""
        elapsed = time.time() - created_at

        if elapsed < CONSENSUS_TIMEOUT_SECONDS:
            return "WAIT"

        failure_count = self.state["mission_failures"].get(proposal_id, 0)

        if failure_count >= MAX_CONSECUTIVE_FAILURES - 1:
            return "BLOCK"
        else:
            self._log("CONSENSUS_DEGRADED", f"Proposal {proposal_id} timed out, degrading to T2",
                      {"elapsed": elapsed, "failures": failure_count})
            return "DEGRADE"

    def run_monitoring_cycle(self):
        """Ciclo de monitoreo para integrar con main_hive.py"""
        self.check_idle_and_recover()
        self._scan_recent_failures()

        if len(self.state["blocked_missions"]) >= PHOENIX_THRESHOLD:
            self._activate_phoenix()

    def _scan_recent_failures(self):
        """Escanea logs recientes buscando patrones de fallo."""
        if not LOG_FILE.exists():
            return

        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-100:]

            for line in lines:
                try:
                    entry = json.loads(line)
                    if "ARS SAFETY" in entry.get("message", "") and "abortada" in entry.get("message", ""):
                        msg = entry["message"]
                        if "Mision '" in msg:
                            start = msg.find("'") + 1
                            end = msg.find("'", start)
                            mission_id = msg[start:end]

                            if time.time() - entry.get("timestamp", 0) < 300:
                                self.record_failure(mission_id, "consensus_timeout")
                except (json.JSONDecodeError, KeyError):
                    continue
        except OSError:
            pass


# Singleton
_breaker: Optional[CircuitBreaker] = None

def get_breaker() -> CircuitBreaker:
    """Obtiene instancia singleton del circuit breaker."""
    global _breaker
    if _breaker is None:
        _breaker = CircuitBreaker()
    return _breaker

# Alias for backward compatibility
get_circuit_breaker = get_breaker


if __name__ == "__main__":
    cb = get_breaker()
    print(f"State: {json.dumps(cb.state, indent=2)}")
    cb.run_monitoring_cycle()
