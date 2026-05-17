import json, os, re
from pathlib import Path
from huggingface_hub import InferenceClient

SUPPORTED_EXTENSIONS = {".py", ".html", ".js", ".css"}
MAX_LINES_PER_FILE = 100


def _collect_codebase(site_path):
    root = Path(site_path)
    sections = []
    if not root.exists():
        return "[site_path not found]"
    for fpath in sorted(root.rglob("*")):
        if fpath.suffix not in SUPPORTED_EXTENSIONS:
            continue
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
            truncated = lines[:MAX_LINES_PER_FILE]
            note = "  # truncated" if len(lines) > MAX_LINES_PER_FILE else ""
            rel = fpath.relative_to(root)
            sections.append("### " + str(rel) + note + "\n" + "\n".join(truncated))
        except OSError as exc:
            sections.append("### " + str(fpath) + " [READ ERROR: " + str(exc) + "]")
    return "\n\n".join(sections) if sections else "[no supported files found]"


def _build_prompt(search_results, hack_results, site_path, task_mode, max_chars=6000):
    file_contents = _collect_codebase(site_path)
    return (
        "You are a senior DevSecOps engineer.\n"
        "TASK MODE: " + task_mode + "\n"
        "SEARCH ENV ERRORS: " + json.dumps(search_results.get("errors", []), indent=2) + "\n"
        "HACK ENV VULNERABILITIES: " + json.dumps(hack_results.get("vulnerabilities", []), indent=2) + "\n"
        "CURRENT CODEBASE:\n" + file_contents[:4000] + "\n\n"
        "Write patches fixing BOTH UI errors AND security vulnerabilities.\n"
        "For LEGACY mode: also fix Python 2 syntax, raw SQL, hardcoded credentials, old jQuery.\n"
        "For AI_CHATBOT mode: also harden the /chat endpoint and add input validation.\n"
        "Return ONLY raw JSON. No explanation. No markdown. No backticks.\n"
        '{"patches": [{"file": str, "action": "replace", "old_code": str, "new_code": str}], "reasoning": str, "confidence": float}'
    )


def _parse_response(raw):
    cleaned = re.sub(r"^```json\s*", "", raw.strip())
    cleaned = re.sub(r"```$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except Exception:
        return {"patches": [], "error": "parse_failed", "raw": raw[:500]}


class HealAgent:
    def __init__(self, model_name="Qwen/Qwen2.5-Coder-7B-Instruct"):
        from unsloth import FastLanguageModel
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=2048,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(self.model)

    def generate_patch(self, search_results, hack_results, site_path, task_mode):
        import torch
        prompt = _build_prompt(search_results, hack_results, site_path, task_mode)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        raw = self.tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return _parse_response(raw)

    def apply_patch(self, patch_dict, site_path):
        applied = 0
        for patch in patch_dict.get("patches", []):
            fpath = Path(site_path) / patch["file"]
            try:
                content = fpath.read_text(encoding="utf-8")
                if patch["old_code"] in content:
                    content = content.replace(patch["old_code"], patch["new_code"], 1)
                    fpath.write_text(content, encoding="utf-8")
                    applied += 1
            except OSError:
                continue
        return applied > 0


class FallbackHealAgent:
    def __init__(self, model_name="Qwen/Qwen2.5-72B-Instruct", provider="novita"):
        self.model_name = model_name
        self.client = InferenceClient(
            provider=provider,
            api_key=os.environ["HF_TOKEN"],
        )

    def generate_patch(self, search_results, hack_results, site_path, task_mode):
        prompt = _build_prompt(search_results, hack_results, site_path, task_mode)
        try:
            result = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            raw = result.choices[0].message.content
        except Exception as exc:
            return {"patches": [], "error": str(exc), "raw": ""}
        return _parse_response(raw)

    def apply_patch(self, patch_dict, site_path):
        applied = 0
        for patch in patch_dict.get("patches", []):
            fpath = Path(site_path) / patch["file"]
            try:
                content = fpath.read_text(encoding="utf-8")
                if patch["old_code"] in content:
                    content = content.replace(patch["old_code"], patch["new_code"], 1)
                    fpath.write_text(content, encoding="utf-8")
                    applied += 1
            except OSError:
                continue
        return applied > 0


if __name__ == "__main__":
    agent = FallbackHealAgent()

    sample_search = {
        "errors": [
            {"route": "/", "type": "HTTP_500", "message": "Server error",
             "severity": "CRITICAL", "weight": 3}
        ],
        "total_score": 3,
    }
    sample_hack = {
        "vulnerabilities": [
            {"type": "SQL_INJECTION", "payload": "admin OR 1=1",
             "severity": "CRITICAL", "endpoint": "/login", "success": True}
        ],
        "total_score": 3,
    }

    result = agent.generate_patch(sample_search, sample_hack, "sites/medium", "STANDARD")
    print(json.dumps(result, indent=2))





