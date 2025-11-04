import os
import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import copy
import hashlib


@dataclass
class Task:
    """Represents a single API task with enhanced tracking"""
    task_name: str
    function: str
    request: Dict[str, Any]
    response: Any = ""
    agent_call_required: bool = False
    status: str = "pending"  # pending, in_progress, completed, failed
    error: Optional[str] = None
    execution_time: Optional[float] = None
    subtasks: List['Task'] = field(default_factory=list)
    
    # Enhanced fields
    task_id: str = field(default="")
    parent_task_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    cached: bool = False
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = self._generate_task_id()
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        timestamp = datetime.now().isoformat()
        content = f"{self.function}_{json.dumps(self.request, sort_keys=True)}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_dict(self):
        result = {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'function': self.function,
            'request': self.request,
            'response': self.response,
            'agent_call_required': self.agent_call_required,
            'status': self.status,
            'error': self.error,
            'execution_time': self.execution_time,
            'priority': self.priority,
            'cached': self.cached,
        }
        if self.subtasks:
            result['subtasks'] = [task.to_dict() for task in self.subtasks]
        return result


@dataclass
class TaskIteration:
    """Represents one iteration of task execution"""
    iteration_number: int
    timestamp: str
    tasks: Dict[str, List[Task]]
    execution_summary: Dict[str, Any]
    agent_decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'iteration_number': self.iteration_number,
            'timestamp': self.timestamp,
            'tasks': {
                category: [task.to_dict() for task in task_list]
                for category, task_list in self.tasks.items()
            },
            'execution_summary': self.execution_summary,
            'agent_decisions': self.agent_decisions
        }
