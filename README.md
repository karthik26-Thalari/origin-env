---
title: OriginEnv
emoji: 🛡️
colorFrom: red
colorTo: blue
sdk: gradio
pinned: true
---

# 🛡️ OriginEnv — RL Environment for Self-Healing DevSecOps

> **OpenEnv Hackathon Submission** — Training LLMs to simultaneously fix broken UIs, patch security vulnerabilities, and defend against AI chatbot attacks on live Flask web applications.

---

## Links

| Resource | Link |
|---|---|
















































































| 🤗 HuggingFace Space |https://huggingface.co/spaces/Destiny04/origin-env|
| 📓 Colab Notebook |https://colab.research.google.com/drive/1t9BYCPsLUPScRUmnCSp8EPzKTBJusVhZ?usp=sharing|
| 📝 HF Blog Post | https://huggingface.co/spaces/Destiny04/origin-env-blog |

---

## Why This Environment?

Frontier AI models can now discover zero-days autonomously and turn them into exploits in hours. Meanwhile:

- **$4.45M** average data breach cost (IBM 2024)
- **40%** of AI-generated code suggestions contain security vulnerabilities (GitHub 2024)
- **97%** multi-turn jailbreak success rate on undefended chatbots (Hagendorff et al. 2026)

Existing RL benchmarks test agents on games or toy tasks. No environment trains LLMs to handle what a real production engineer faces: **simultaneous UI failures, security breaches, and AI chatbot attacks — all at once.** OriginEnv does.

---

## Environment Overview

| Property | Value |
|---|---|
| Difficulty levels | 3 (Easy → Medium → Hard) |
| Task modes | 3 (STANDARD, LEGACY, AI_CHATBOT) |
| Action space | Structured JSON patch (file, old_code, new_code) |
| Observation space | Merged UI errors + security vulnerabilities JSON |
| Reward range | −50 to +51 |
| Rubric items | 15 composable reward events |
| Max steps per episode | 20 |
| Recovery mechanisms | 4 (Snapshot, Standard Revert, Softlock, Golden State) |
| OpenEnv compliant | Yes — validated ✅ |

---

## What the Agent Does

OriginEnv is an OpenEnv-compliant RL environment where an LLM agent:

- **Sees**: A merged JSON observation of UI errors (from Playwright/requests browser scanner) and active security attacks (SQL injection, XSS, path traversal, auth bypass, chatbot jailbreaks)
- **Does**: Generates structured code patches to fix both UI and security issues simultaneously on a **live Flask server**
- **Gets rewarded for**: Fixing vulnerabilities (+15), removing errors (+10), blocking chatbot attacks (+6)
- **Gets penalized for**: Bad patches (−10), no progress (−5), softlocks (−8)

### Three Task Modes

| Mode | What the agent must fix |
|---|---|
| STANDARD | UI errors + security vulnerabilities |
| LEGACY | Python 2 syntax + raw SQL + hardcoded credentials + old jQuery |
| AI_CHATBOT | /chat endpoint hardening + jailbreak defense + input validation |

---

## Environment Architecture

```
OriginEnv
├── Palkia    - The SearchEnv           — Playwright browser scanner (UI errors, 404s, JS crashes, CSS)
├── Giratina  - The HackEnv             — Security attacker (SQL injection, XSS, path traversal, auth bypass, CSRF)
├── Marshadow - The ChatbotHackEnv      — Jailbreak attacker (direct, roleplay, multi-turn, phishing)
├── Dialga    - The HealAgent           — LLM patch generator (Qwen2.5-72B via HuggingFace novita API)
├── Celebi    - The RevertSystem        — Snapshot, standard revert, softlock, golden state restore
└── Rayquaza  - The EntryGuard          — Intrusion detection + /trident/status dashboard endpoint
```

### Curriculum Learning

| Episodes | Difficulty Pool |
| 1-20 | Easy + Medium + Hard |

### Recovery System

| Mechanism | Triggers when |
|---|---|
| Snapshot | Every episode reset |
| Standard Revert | Patch causes regression (reward < 0), first 3 times |
| Softlock | Too many bad patches — loads golden state |
| Delete & Restore | Site completely wiped — full golden state restore |

---

## Reward Function

OriginEnv uses a **15-item composable rubric** — rich, informative signal that is hard to game:

### Positive Rewards

| Event | Reward |
|---|---|
| All vulnerabilities fixed | +15 |
| Security score improved | +7 |
| Critical vulnerability removed | +8 per vuln |
| All UI errors fixed | +10 |
| UI error score improved | +5 |
| All routes return 200 | +5 |
| All chatbot attacks blocked | +6 |
| Fewer chatbot attacks succeeded | +3 |
| System prompt hardened | +5 |
| Legacy pattern removed | +3 per pattern |

### Negative Rewards

| Event | Reward |
|---|---|
| No progress this step | −5 |
| Step efficiency penalty | −1 |
| Standard revert triggered | −10 |
| Softlock triggered | −8 |
| Delete triggered | −15 |

---

## Results

### Environment Training — 20 Episodes (All Difficulties)

![Reward Curve](reward_curve.png)
*Episode rewards across Easy (green, +42), Medium (orange, +24), and Hard (red, +24). Zero reverts across all 20 episodes — agent never made things worse.*

![Revert Curve](revert_curve.png)
*Average reward per difficulty. Agent maintained positive rewards across all difficulty levels.*

### Unsloth GRPO Fine-tuning — 0.5B vs 1.5B

![Training Curve](training_curve.png)
*Qwen2.5-0.5B fine-tuned with GRPO using OriginEnv rewards. Reward improved from 2.5 → 5.625 — a **125% improvement** in 10 steps.*

![Comparison Curve](comparison_curve.png)
*0.5B outperformed 1.5B on OriginEnv — demonstrating that domain-specific structured reasoning matters more than raw model capacity.*

| Model | Avg Reward | Peak Reward | Improvement |
|---|---|---|---|
| Qwen2.5-0.5B | 3.19 | 5.625 | **+125%** |
| Qwen2.5-1.5B | 2.70 | 4.750 | +81% |

---

## The 3 Sites

### sites/easy — Basic Broken Flask App
- **Bugs**: Missing CSS, broken images, console errors, XSS via /form
- **Vulnerabilities**: XSS reflection, missing input sanitization
- **Chatbot**: No input validation, vulnerable to direct jailbreaks

### sites/medium — Medium Difficulty Flask App
- **Bugs**: Division by zero on /api/data, broken JS fetch, broken sessions
- **Vulnerabilities**: SQL injection on /login, hardcoded SECRET_KEY, Python 2 prints, raw SQL INSERT
- **Chatbot**: No system prompt, no turn limits

### sites/hard — Hard Difficulty Flask App
- **Bugs**: Undefined template variable, JS ReferenceError, broken session lifetime
- **Vulnerabilities**: Auth bypass via ?admin=true, path traversal on /api/export, missing CSRF, raw SQL in 3 places, old jQuery
- **Chatbot**: Vulnerable to 3-turn roleplay jailbreaks

---

## Hackathon Theme Alignment

- **Primary: Theme 5 (Wild Card)** — Novel environment training LLMs for simultaneous DevSecOps tasks. No existing benchmark covers UI repair + security patching + jailbreak defense simultaneously.
- **Secondary: Theme 3.1 (World Modeling / Professional Tasks)** — Real browser, real HTTP attacks, real code changes. Every interaction touches a live Flask server.
- **Also qualifies: Theme 1 (Multi-Agent)** — Three specialist agents (SearchEnv, HackEnv, HealAgent) cooperate to produce the training signal.

---

## Setup

### Option 1: HuggingFace Space

Visit the live Space: **YOUR_HF_SPACE_URL**

### Option 2: Local (Python)

```bash
git clone https://github.com/YOUR_USERNAME/origin-env
cd origin-env
pip install openenv-core flask requests beautifulsoup4 huggingface_hub
export HF_TOKEN=hf_your_token
python origin_env.py
```

### Run Tests

```bash
pytest tests/ -v
# 13/13 tests passing
```

### OpenEnv Validation

```bash
cd origin_env_pkg
openenv validate
# [OK] origin_env_pkg: Ready for multi-mode deployment
```

---

## Project Structure

```
origin-env/
├── origin_env.py          ← Main RL environment (ROOT)
├── origin_env_pkg/        ← OpenEnv compliant FastAPI server
├── envs/
│   ├── search_env.py      ← Playwright UI scanner
│   ├── hack_env.py        ← Security attack engine (5 attack types)
│   ├── heal_agent.py      ← LLM patch generator (Qwen2.5-72B)
│   ├── revert_system.py   ← Snapshot & 4-mode recovery
│   └── entry_guard.py     ← Intrusion detection middleware
├── sites/                 ← Easy, Medium, Hard broken Flask apps
│   ├── easy/              ← Broken site
│   ├── easy_golden/       ← Perfect fixed reference
│   ├── medium/
│   ├── medium_golden/
│   ├── hard/
│   └── hard_golden/
├── tests/                 ← 13 pytest tests (all passing)
├── openenv.yaml           ← OpenEnv manifest
├── pyproject.toml         ← Package config
├── reward_curve.png
├── revert_curve.png
├── training_curve.png
└── comparison_curve.png
```