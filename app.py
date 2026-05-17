import gradio as gr
import json

DEMO = {
    'observation': {
        'episode': 1, 'task_mode': 'STANDARD', 'difficulty': 'medium',
        'search_errors': [{'route': '/login', 'type': 'HTTP_500', 'message': 'Division by zero', 'severity': 'CRITICAL', 'weight': 3}],
        'hack_vulnerabilities': [{'type': 'SQL_INJECTION', 'payload': "admin' OR '1'='1", 'severity': 'CRITICAL', 'endpoint': '/login', 'success': True}],
        'step': 0
    },
    'patch': {
        'patches': [{'file': 'app.py', 'action': 'replace',
            'old_code': "query = f\"SELECT * FROM users WHERE username='{username}'\"",
            'new_code': "cursor.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))"}],
        'reasoning': 'Fixed SQL injection with parameterized query. Added error handling for division by zero.',
        'confidence': 0.95
    },
    'reward': 22.0,
    'revert_type': 'none'
}

def run_episode(task_mode, difficulty):
    obs = json.dumps(DEMO['observation'], indent=2)
    patch = json.dumps(DEMO['patch'], indent=2)
    reward = f"+{DEMO['reward']}"
    revert = DEMO['revert_type']
    rubric = '''Rubric Scores:
+ zero_errors:     +10 (all UI errors fixed)
+ vuln_reduction:  +7  (security score improved)
+ all_routes_200:  +5  (all routes return 200)
- step_penalty:    -1  (per step)
= Total Reward:    +22.0'''
    return obs, patch, reward, revert, rubric

with gr.Blocks(title='OriginEnv', theme=gr.themes.Monochrome()) as demo:
    gr.Markdown('# 🛡️ OriginEnv v3.0')
    gr.Markdown('### RL Environment for Self-Healing DevSecOps')
    gr.Markdown('> Training LLMs to simultaneously fix broken UIs, patch security vulnerabilities, and defend against chatbot attacks.')

    with gr.Row():
        task_mode = gr.Dropdown(['STANDARD', 'LEGACY', 'AI_CHATBOT'], value='STANDARD', label='Task Mode')
        difficulty = gr.Dropdown(['easy', 'medium', 'hard'], value='medium', label='Difficulty')
        run_btn = gr.Button('▶ Run Episode', variant='primary')

    with gr.Row():
        obs_box = gr.Textbox(label='🔍 Agent Observation (Search + Hack Results)', lines=15)
        patch_box = gr.Textbox(label='🔧 Agent Action (Generated Patch)', lines=15)

    with gr.Row():
        reward_box = gr.Textbox(label='🏆 Reward', scale=1)
        revert_box = gr.Textbox(label='↩️ Revert Type', scale=1)
        rubric_box = gr.Textbox(label='📊 Rubric Breakdown', lines=7, scale=2)

    gr.Markdown('## 📈 Training Results')
    with gr.Row():
        gr.Image('reward_curve.png', label='Reward Curve — 20 Episodes')
        gr.Image('training_curve.png', label='GRPO Training — 125% Improvement')
    with gr.Row():
        gr.Image('revert_curve.png', label='Reward by Difficulty')
        gr.Image('comparison_curve.png', label='0.5B vs 1.5B Comparison')

    gr.Markdown('## 🎯 Reward Function (15-item Rubric)')
    gr.Dataframe(
        value=[
            ['zero_vulns', '+15', 'All security vulnerabilities fixed'],
            ['vuln_reduction', '+7', 'Security score improved'],
            ['critical_fix', '+8/vuln', 'Critical vulnerability removed'],
            ['zero_errors', '+10', 'All UI errors fixed'],
            ['error_reduction', '+5', 'UI error score improved'],
            ['all_routes_200', '+5', 'All routes return 200'],
            ['chatbot_protected', '+6', 'All chatbot attacks blocked'],
            ['chatbot_improved', '+3', 'Fewer chatbot attacks succeeded'],
            ['system_prompt_patched', '+5', 'System prompt hardened'],
            ['legacy_pattern_removed', '+3/pattern', 'Legacy code removed'],
            ['no_progress', '-5', 'No improvement this step'],
            ['step_penalty', '-1', 'Per step efficiency penalty'],
            ['standard_revert', '-10', 'Bad patch — reverted'],
            ['softlock', '-8', 'Too many bad patches'],
            ['delete', '-15', 'Site deleted'],
        ],
        headers=['Rubric Item', 'Reward', 'Description'],
        interactive=False
    )

    run_btn.click(run_episode, inputs=[task_mode, difficulty],
                  outputs=[obs_box, patch_box, reward_box, revert_box, rubric_box])

demo.launch()
