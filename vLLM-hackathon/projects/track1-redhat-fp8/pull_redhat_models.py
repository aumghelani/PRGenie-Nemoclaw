"""
Pull a pre-quantized Red Hat AI model from Hugging Face.

Red Hat AI maintains an HF organization (`RedHatAI`) with vetted FP8 and INT4
quantizations of Llama 3.x, Mistral, Mixtral, and others — already calibrated
and published with benchmark numbers.

Usage:
    python3 pull_redhat_models.py --model RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8
    python3 pull_redhat_models.py --model RedHatAI/Meta-Llama-3.1-70B-Instruct-FP8
"""

import argparse
import os
import sys
from pathlib import Path


# Suggested models — edit if new ones are published by the event date.
SUGGESTED = {
    "8b-fp8": "RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8",
    "8b-int4": "RedHatAI/Meta-Llama-3.1-8B-Instruct-quantized.w4a16",
    "70b-fp8": "RedHatAI/Meta-Llama-3.1-70B-Instruct-FP8",
    "mistral-fp8": "RedHatAI/Mistral-7B-Instruct-v0.3-FP8",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=False,
                        help="HF repo ID (e.g. RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8) "
                             f"or shortcut from: {', '.join(SUGGESTED)}")
    parser.add_argument("--list", action="store_true",
                        help="List suggested Red Hat models and exit")
    parser.add_argument("--output-dir", default="/models",
                        help="Where to stage models (default: /models)")
    args = parser.parse_args()

    if args.list or not args.model:
        print("Suggested Red Hat AI models:")
        for k, v in SUGGESTED.items():
            print(f"  {k:<14}  →  {v}")
        print("\nPass one of the shortcuts or a full repo id via --model")
        sys.exit(0 if args.list else 1)

    repo_id = SUGGESTED.get(args.model, args.model)
    model_name = repo_id.split("/")[-1].lower()
    local_dir = Path(args.output_dir) / model_name

    from huggingface_hub import snapshot_download

    print(f"Downloading {repo_id} → {local_dir}")
    snapshot_download(
        repo_id,
        local_dir=str(local_dir),
        ignore_patterns=["*.pth", "original/**"],
    )
    print(f"\n✓ Done. Serve with:")
    print(f"  python3 -m vllm.entrypoints.openai.api_server \\")
    print(f"      --model {local_dir} --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    main()
