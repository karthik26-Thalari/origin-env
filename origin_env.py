import random, csv, os, json
from openenv.env import Env
from datetime import datetime
from envs.heal_agent import HealAgent, FallbackHealAgent
from envs.search_env import SearchEnv
from envs.hack_env import HackEnv, ChatbotHackEnv
from envs.revert_system import RevertSystem


class RubricItem:
    def __init__(self, name, weight, description=""):
        self.name        = name
        self.weight      = weight
        self.description = description


class Rubric:
    def __init__(self, items):
        self.items = {item.name: item for item in items}

    def score(self, flags):
        total = 0.0
        for name, item in self.items.items():
            val = flags.get(name, False)
            if isinstance(val, bool):
                if val:
                    total += item.weight
            elif isinstance(val, (int, float)):
                total += item.weight * val
        return total


class OriginEnv(Env):

    def __init__(self, site_configs=None, task_weights=None, max_retries=5,
                 base_url="http://localhost:5000", use_fallback_agent=False):

        super().__init__(name="OriginEnv", episode_max_length=20)
        self.site_configs = site_configs or [
            {"path": "sites/easy",   "golden": "sites/easy_golden",   "difficulty": "easy"},
            {"path": "sites/medium", "golden": "sites/medium_golden", "difficulty": "medium"},
            {"path": "sites/hard",   "golden": "sites/hard_golden",   "difficulty": "hard"},
        ]
        self.task_weights  = task_weights or {"LEGACY": 0.33, "AI_CHATBOT": 0.33, "STANDARD": 0.34}
        self.max_retries   = max_retries
        self.base_url      = base_url
        self.use_fallback  = use_fallback_agent

        self.rubric = Rubric([
            RubricItem("zero_vulns",             weight=15),
            RubricItem("vuln_reduction",         weight=7),
            RubricItem("critical_fix",           weight=8),
            RubricItem("zero_errors",            weight=10),
            RubricItem("error_reduction",        weight=5),
            RubricItem("all_routes_200",         weight=5),
            RubricItem("chatbot_protected",      weight=6),
            RubricItem("chatbot_improved",       weight=3),
            RubricItem("system_prompt_patched",  weight=5),
            RubricItem("legacy_pattern_removed", weight=3),
            RubricItem("standard_revert",        weight=-10),
            RubricItem("softlock",               weight=-8),
            RubricItem("delete",                 weight=-15),
            RubricItem("no_progress",            weight=-5),
            RubricItem("step_penalty",           weight=-1),
        ])

        self.episode             = 0
        self.step_count          = 0
        self.current_site        = None
        self.current_task_mode   = None
        self.revert_count        = 0
        self.impossible_count    = 0
        self.baseline_search     = None
        self.baseline_hack       = None
        self.current_snapshot_id = None
        self.total_reward        = 0.0
        self.golden_state_loads  = 0
        self.revert_system       = None

        self._csv_file = open("rewards.csv", "w", newline="")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow([
            "episode", "step", "task_mode", "difficulty",
            "reward", "total_reward", "revert_type",
            "search_score", "hack_score", "timestamp"
        ])
        self._csv_file.flush()

        if self.use_fallback:
            self.agent = FallbackHealAgent()
        else:
            try:
                self.agent = HealAgent()
            except Exception:
                self.agent = FallbackHealAgent()

    def reset(self) -> dict:
        self.episode         += 1
        self.step_count       = 0
        self.revert_count     = 0
        self.impossible_count = 0
        self.total_reward     = 0.0

        if self.episode <= 15:
            pool = [c for c in self.site_configs if c["difficulty"] == "easy"]
        elif self.episode <= 30:
            pool = [c for c in self.site_configs if c["difficulty"] in ("easy", "medium")]
        else:
            pool = self.site_configs

        self.current_site      = random.choice(pool)
        modes                  = list(self.task_weights.keys())
        weights                = list(self.task_weights.values())
        self.current_task_mode = random.choices(modes, weights=weights, k=1)[0]

        self.revert_system       = RevertSystem(self.current_site["path"], self.current_site["golden"], self.base_url)
        self.current_snapshot_id = self.revert_system.snapshot()

        search_env           = SearchEnv(self.base_url)
        self.baseline_search = search_env.scan()

        if self.current_task_mode == "AI_CHATBOT":
            hack_env = ChatbotHackEnv(self.base_url)
        else:
            hack_env = HackEnv(self.base_url)
        self.baseline_hack = hack_env.attack()

        return {
            "episode":              self.episode,
            "task_mode":            self.current_task_mode,
            "difficulty":           self.current_site["difficulty"],
            "search_errors":        self.baseline_search.get("errors", []),
            "hack_vulnerabilities": self.baseline_hack.get("vulnerabilities", []),
            "step":                 self.step_count,
        }

    def step(self, action: dict) -> tuple:
        self.step_count += 1
        old_search = self.baseline_search
        old_hack   = self.baseline_hack

        self.agent.apply_patch(action, self.current_site["path"])

        search_env = SearchEnv(self.base_url)
        new_search = search_env.scan()

        if self.current_task_mode == "AI_CHATBOT":
            hack_env = ChatbotHackEnv(self.base_url)
        else:
            hack_env = HackEnv(self.base_url)
        new_hack = hack_env.attack()

        reward      = self.compute_reward(old_search, new_search, old_hack, new_hack, self.current_task_mode)
        reward     -= 1
        revert_type = "none"

        if reward < 0:
            if self.revert_count < 3:
                self.revert_system.standard_revert(self.current_snapshot_id)
                self.revert_count += 1
                reward     -= 10
                revert_type = "standard"
            else:
                self.revert_system.softlock("reward negative")
                self.golden_state_loads += 1
                reward     -= 8
                revert_type = "softlock"
            self.impossible_count += 1

        self.total_reward    += reward
        self.baseline_search  = new_search
        self.baseline_hack    = new_hack

        self._log_to_csv(reward, revert_type, new_search, new_hack)

        done = self.step_count >= 20 or self.impossible_count >= self.max_retries

        obs = {
            "episode":              self.episode,
            "task_mode":            self.current_task_mode,
            "difficulty":           self.current_site["difficulty"],
            "search_errors":        new_search.get("errors", []),
            "hack_vulnerabilities": new_hack.get("vulnerabilities", []),
            "step":                 self.step_count,
        }
        info = {
            "revert_type":        revert_type,
            "revert_count":       self.revert_count,
            "total_reward":       self.total_reward,
            "golden_state_loads": self.golden_state_loads,
        }
        return obs, reward, done, info

    def state(self) -> dict:
        return {
            "episode":            self.episode,
            "step_count":         self.step_count,
            "current_site":       self.current_site,
            "current_task_mode":  self.current_task_mode,
            "revert_count":       self.revert_count,
            "impossible_count":   self.impossible_count,
            "total_reward":       self.total_reward,
            "golden_state_loads": self.golden_state_loads,
            "snapshot_id":        self.current_snapshot_id,
        }

    def compute_reward(self, old_search, new_search, old_hack, new_hack,
                       task_mode, chatbot_old=None, chatbot_new=None) -> float:
        old_s = old_search.get("total_score", 0)
        new_s = new_search.get("total_score", 0)
        old_h = old_hack.get("total_score", 0)
        new_h = new_hack.get("total_score", 0)

        old_vulns  = old_hack.get("vulnerabilities", [])
        new_vulns  = new_hack.get("vulnerabilities", [])
        new_errors = new_search.get("errors", [])

        old_criticals   = [v for v in old_vulns if v.get("severity") == "CRITICAL"]
        new_criticals   = [v for v in new_vulns if v.get("severity") == "CRITICAL"]
        criticals_fixed = max(0, len(old_criticals) - len(new_criticals))

        old_chatbot_hits = len([v for v in old_vulns if v.get("type") == "CHATBOT"])
        new_chatbot_hits = len([v for v in new_vulns if v.get("type") == "CHATBOT"])

        flags = {
            "zero_vulns":             len(new_vulns) == 0,
            "vuln_reduction":         new_h < old_h,
            "critical_fix":           criticals_fixed,
            "zero_errors":            len(new_errors) == 0,
            "error_reduction":        new_s < old_s,
            "all_routes_200":         all(e.get("type") != "HTTP_500" for e in new_errors),
            "chatbot_protected":      task_mode == "AI_CHATBOT" and new_chatbot_hits == 0,
            "chatbot_improved":       task_mode == "AI_CHATBOT" and new_chatbot_hits < old_chatbot_hits,
            "system_prompt_patched":  task_mode == "AI_CHATBOT" and new_h < old_h,
            "legacy_pattern_removed": 0,
            "standard_revert":        False,
            "softlock":               False,
            "delete":                 False,
            "no_progress":            new_s >= old_s and new_h >= old_h,
            "step_penalty":           True,
        }
        return float(self.rubric.score(flags))

    def _log_to_csv(self, reward, revert_type, new_search=None, new_hack=None):
        self._csv_writer.writerow([
            self.episode,
            self.step_count,
            self.current_task_mode,
            self.current_site["difficulty"] if self.current_site else "",
            round(reward, 4),
            round(self.total_reward, 4),
            revert_type,
            new_search.get("total_score", 0) if new_search else 0,
            new_hack.get("total_score", 0)   if new_hack   else 0,
            datetime.utcnow().isoformat(),
        ])
        self._csv_file.flush()

    def __del__(self):
        try:
            self._csv_file.close()
        except Exception:
            pass





