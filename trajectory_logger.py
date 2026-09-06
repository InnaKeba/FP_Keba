import json
import time
from typing import Dict, List, Optional

class TrajectoryLogger:
    def __init__(self, filepath: str = "trajectory.json"):
        self.filepath = filepath
        self.trajectory: List[Dict] = []

    def log_step(self, agent_name: str, node: str, action: str, output: str, tools: Optional[List] = None) -> dict:
        step = {
            'agent_name': agent_name,
            'node': node,
            'action': action[:200],
            'output': output[:300],
            'tools': tools or [],
            'timestamp': time.time(),
        }
        self.trajectory.append(step)
        return step

    def save(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trajectory, f, ensure_ascii=False, indent=2)