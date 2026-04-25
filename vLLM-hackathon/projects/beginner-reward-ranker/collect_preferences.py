"""
Reward Ranker — Preference Collection App.

Generates two responses to the same prompt (using different temperatures)
and lets you pick the better one. Preferences are saved to a JSONL file
that can be used to train a reward model.

Prerequisites:
    bash /workspace/start_vllm_server.sh

Usage:
    python3 collect_preferences.py
    # Open http://localhost:7860
"""

import json
import os
import random
import time

import gradio as gr
import httpx

VLLM_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
MODEL = "/models/llama-3.1-8b-instruct"
PREFERENCES_FILE = os.path.join(os.path.dirname(__file__), "preferences.jsonl")
PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "sample_prompts.json")

# Load prompts
with open(PROMPTS_FILE) as f:
    ALL_PROMPTS = json.load(f)["prompts"]


def generate_response(prompt: str, temperature: float) -> str:
    """Generate a single response from vLLM."""
    try:
        r = httpx.post(
            f"{VLLM_URL}/chat/completions",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
                "temperature": temperature,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except httpx.ConnectError:
        return "ERROR: Cannot connect to vLLM. Run: bash /workspace/start_vllm_server.sh"
    except Exception as e:
        return f"ERROR: {e}"


def generate_pair():
    """Generate two responses with different temperatures and randomize order."""
    prompt_data = random.choice(ALL_PROMPTS)
    prompt = prompt_data["text"]

    # Use different temperatures to get noticeably different responses
    # Low temp = focused/safe, High temp = creative/risky
    response_low = generate_response(prompt, temperature=0.3)
    response_high = generate_response(prompt, temperature=1.0)

    # Randomize which side is which (avoid position bias)
    responses = [(response_low, 0.3), (response_high, 1.0)]
    random.shuffle(responses)

    return (
        prompt,
        responses[0][0],  # Response A
        responses[1][0],  # Response B
        json.dumps({      # Hidden metadata
            "prompt": prompt,
            "category": prompt_data["category"],
            "a_temp": responses[0][1],
            "b_temp": responses[1][1],
            "a_text": responses[0][0],
            "b_text": responses[1][0],
        }),
    )


def save_preference(choice: str, metadata_json: str):
    """Save a preference to the JSONL file."""
    meta = json.loads(metadata_json)

    if choice == "A is better":
        chosen, rejected = meta["a_text"], meta["b_text"]
    else:
        chosen, rejected = meta["b_text"], meta["a_text"]

    record = {
        "prompt": meta["prompt"],
        "category": meta["category"],
        "chosen": chosen,
        "rejected": rejected,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    with open(PREFERENCES_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    # Count total preferences
    with open(PREFERENCES_FILE) as f:
        count = sum(1 for _ in f)

    return f"Saved! Total preferences collected: **{count}**"


# Count existing preferences
existing_count = 0
if os.path.exists(PREFERENCES_FILE):
    with open(PREFERENCES_FILE) as f:
        existing_count = sum(1 for _ in f)

# --- Gradio UI ---
with gr.Blocks(title="Reward Ranker", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Reward Ranker — Collect Human Preferences")
    gr.Markdown(
        "Two responses to the same prompt. **Pick the better one.** "
        "Your choices train a reward model that learns what 'good' means.\n\n"
        f"*Preferences collected so far: {existing_count}*"
    )

    # Hidden state
    metadata = gr.Textbox(visible=False)

    prompt_display = gr.Textbox(label="Prompt", interactive=False, lines=2)

    with gr.Row():
        response_a = gr.Textbox(label="Response A", interactive=False, lines=10)
        response_b = gr.Textbox(label="Response B", interactive=False, lines=10)

    with gr.Row():
        btn_a = gr.Button("A is better", variant="primary")
        btn_b = gr.Button("B is better", variant="primary")

    status = gr.Markdown("")
    new_pair_btn = gr.Button("Generate New Pair", variant="secondary")

    # Wire up events
    def on_new_pair():
        prompt, a, b, meta = generate_pair()
        return prompt, a, b, meta, ""

    def on_pick_a(meta):
        msg = save_preference("A is better", meta)
        prompt, a, b, new_meta, _ = on_new_pair()
        return msg, prompt, a, b, new_meta

    def on_pick_b(meta):
        msg = save_preference("B is better", meta)
        prompt, a, b, new_meta, _ = on_new_pair()
        return msg, prompt, a, b, new_meta

    new_pair_btn.click(
        on_new_pair,
        outputs=[prompt_display, response_a, response_b, metadata, status],
    )
    btn_a.click(
        on_pick_a, inputs=[metadata],
        outputs=[status, prompt_display, response_a, response_b, metadata],
    )
    btn_b.click(
        on_pick_b, inputs=[metadata],
        outputs=[status, prompt_display, response_a, response_b, metadata],
    )

    # Auto-generate first pair on load
    demo.load(
        on_new_pair,
        outputs=[prompt_display, response_a, response_b, metadata, status],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
