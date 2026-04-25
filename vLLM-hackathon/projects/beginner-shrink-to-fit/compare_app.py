"""
Shrink to Fit — Side-by-side comparison Gradio app.

Sends the same prompt to both the full-precision and quantized models
and displays results side-by-side with timing.

Prerequisites:
    bash serve_both.sh   (models on ports 8000 and 8001)

Usage:
    python3 compare_app.py
    # Open http://localhost:7860
"""

import time

import gradio as gr
import httpx

FULL_URL = "http://localhost:8000/v1/chat/completions"
FULL_MODEL = "/models/llama-3.1-8b-instruct"
QUANT_URL = "http://localhost:8001/v1/chat/completions"
QUANT_MODEL = "/models/llama-3.1-8b-instruct-awq-int4"


def query_model(url: str, model: str, prompt: str, max_tokens: int) -> dict:
    """Send a chat completion request and return the response + timing."""
    start = time.perf_counter()
    try:
        r = httpx.post(
            url,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=90,
        )
        r.raise_for_status()
        elapsed = time.perf_counter() - start
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data["usage"]["completion_tokens"]
        return {
            "text": text,
            "time_s": elapsed,
            "tokens": tokens,
            "tok_per_s": tokens / elapsed if elapsed > 0 else 0,
        }
    except httpx.ConnectError:
        return {"text": "Cannot connect — is serve_both.sh running?", "time_s": 0, "tokens": 0, "tok_per_s": 0}
    except Exception as e:
        return {"text": f"Error: {e}", "time_s": 0, "tokens": 0, "tok_per_s": 0}


def compare(prompt: str, max_tokens: int):
    """Query both models and format results."""
    full = query_model(FULL_URL, FULL_MODEL, prompt, max_tokens)
    quant = query_model(QUANT_URL, QUANT_MODEL, prompt, max_tokens)

    full_info = (
        f"**Full Precision (FP16)**\n"
        f"Time: {full['time_s']:.2f}s | Tokens: {full['tokens']} | "
        f"Speed: {full['tok_per_s']:.1f} tok/s\n\n---\n\n{full['text']}"
    )
    quant_info = (
        f"**Quantized (AWQ INT4)**\n"
        f"Time: {quant['time_s']:.2f}s | Tokens: {quant['tokens']} | "
        f"Speed: {quant['tok_per_s']:.1f} tok/s\n\n---\n\n{quant['text']}"
    )

    speedup = full["time_s"] / quant["time_s"] if quant["time_s"] > 0 else 0
    summary = (
        f"Speedup: **{speedup:.2f}x** | "
        f"VRAM savings: **~75%** (16 GB -> ~4 GB)"
    )

    return full_info, quant_info, summary


EXAMPLE_PROMPTS = [
    "Explain how a hash table works in simple terms.",
    "Write a Python function that checks if a string is a valid palindrome.",
    "What are the three laws of thermodynamics? Explain each briefly.",
    "Compare and contrast REST and GraphQL APIs.",
    "Write a short poem about machine learning.",
]

with gr.Blocks(title="Shrink to Fit", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Shrink to Fit — Quantization Comparison")
    gr.Markdown(
        "Compare **full-precision** (FP16, ~16 GB) vs **quantized** (AWQ INT4, ~4 GB) "
        "Llama 3.1 8B side-by-side. Same prompt, same temperature — spot the difference!"
    )

    with gr.Row():
        prompt = gr.Textbox(
            label="Prompt",
            placeholder="Enter a prompt to compare...",
            lines=2,
            scale=4,
        )
        max_tokens = gr.Slider(
            minimum=32, maximum=512, value=256, step=32,
            label="Max tokens",
        )

    btn = gr.Button("Compare", variant="primary")
    summary = gr.Markdown(label="Summary")

    with gr.Row():
        full_output = gr.Markdown(label="Full Precision")
        quant_output = gr.Markdown(label="Quantized")

    gr.Examples(examples=EXAMPLE_PROMPTS, inputs=prompt)

    btn.click(compare, inputs=[prompt, max_tokens], outputs=[full_output, quant_output, summary])
    prompt.submit(compare, inputs=[prompt, max_tokens], outputs=[full_output, quant_output, summary])


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
