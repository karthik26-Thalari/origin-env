from typing import Optional, Any
from pydantic import BaseModel

class OriginAction(BaseModel):
    patches: list = []
    task_mode: str = 'STANDARD'

class OriginObservation(BaseModel):
    episode: int = 0
    step: int = 0
    task_mode: str = 'STANDARD'
    difficulty: str = 'easy'
    search_errors: list = []
    hack_vulnerabilities: list = []
    reward: float = 0.0
    done: bool = False
    revert_type: str = 'none'
    message: str = ''
    message_length: int = 0
    echoed_message: str = ''
    metadata: Optional[dict] = None
