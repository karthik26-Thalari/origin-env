import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from uuid import uuid4
from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State
try:
    from ..models import OriginAction, OriginObservation
except ImportError:
    from models import OriginAction, OriginObservation
from origin_env import OriginEnv as _OriginEnv

class OriginEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = False
    def __init__(self):
        self._env = _OriginEnv(use_fallback_agent=True)
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._last_obs = {}

    def reset(self) -> OriginObservation:
        self._state = State(episode_id=str(uuid4()), step_count=0)
        obs = self._env.reset()
        self._last_obs = obs
        return OriginObservation(
            episode=obs.get('episode', 0),
            step=obs.get('step', 0),
            task_mode=obs.get('task_mode', 'STANDARD'),
            difficulty=obs.get('difficulty', 'easy'),
            search_errors=obs.get('search_errors', []),
            hack_vulnerabilities=obs.get('hack_vulnerabilities', []),
            reward=0.0,
            done=False,
            echoed_message='OriginEnv ready!',
        )

    def step(self, action: OriginAction) -> OriginObservation:
        self._state.step_count += 1
        action_dict = {'patches': action.patches}
        obs, reward, done, info = self._env.step(action_dict)
        return OriginObservation(
            episode=obs.get('episode', 0),
            step=obs.get('step', 0),
            task_mode=obs.get('task_mode', 'STANDARD'),
            difficulty=obs.get('difficulty', 'easy'),
            search_errors=obs.get('search_errors', []),
            hack_vulnerabilities=obs.get('hack_vulnerabilities', []),
            reward=float(reward),
            done=done,
            revert_type=info.get('revert_type', 'none'),
            echoed_message=f'Step {self._state.step_count} reward={reward}',
        )

    @property
    def state(self) -> State:
        return self._state
