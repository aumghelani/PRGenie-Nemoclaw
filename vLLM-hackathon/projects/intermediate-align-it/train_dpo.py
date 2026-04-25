"""
Align It — DPO training on Llama 3.1 8B with LoRA.

Uses TRL's DPOTrainer with PEFT LoRA adapters for memory-efficient training.
LoRA means we only train ~0.5% of the model's parameters, so this fits
comfortably on 2x A100.

Usage:
    python3 train_dpo.py
    python3 train_dpo.py --beta 0.1 --epochs 1 --lr 5e-5

Expected time: 20-40 minutes on 2x A100 (depending on dataset size)
"""

import argparse
import json
import os

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import DPOConfig, DPOTrainer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PREFERENCE_FILE = os.path.join(SCRIPT_DIR, "preference_data.jsonl")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "aligned-model")
MODEL_PATH = "/models/llama-3.1-8b-instruct"


def load_preference_data() -> Dataset:
    """Load preference pairs from JSONL."""
    if not os.path.exists(PREFERENCE_FILE):
        print(f"ERROR: {PREFERENCE_FILE} not found.")
        print("Run 'python3 generate_preferences.py' first.")
        raise SystemExit(1)

    records = []
    with open(PREFERENCE_FILE) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records)} preference pairs")

    # Convert to DPO format
    dataset = Dataset.from_dict({
        "prompt": [r["prompt"] for r in records],
        "chosen": [r["chosen"] for r in records],
        "rejected": [r["rejected"] for r in records],
    })

    return dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--beta", type=float, default=0.1,
                        help="DPO beta parameter (alignment strength)")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--lora-r", type=int, default=16,
                        help="LoRA rank (higher = more capacity but more VRAM)")
    args = parser.parse_args()

    print("=" * 55)
    print("  Align It — DPO Training with LoRA")
    print(f"  Base model: {MODEL_PATH}")
    print(f"  Beta: {args.beta}")
    print(f"  LoRA rank: {args.lora_r}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 55)

    # Load dataset
    dataset = load_preference_data()
    split = dataset.train_test_split(test_size=0.1, seed=42)
    print(f"Train: {len(split['train'])} | Eval: {len(split['test'])}")

    # Load model and tokenizer
    print(f"\nLoading base model: {MODEL_PATH}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    # LoRA configuration
    # Only adapts attention projection layers — small but effective
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_r * 2,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        task_type="CAUSAL_LM",
    )

    # DPO training configuration
    training_args = DPOConfig(
        output_dir=OUTPUT_DIR,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        beta=args.beta,
        max_length=args.max_length,
        max_prompt_length=args.max_length // 2,
        eval_strategy="steps",
        eval_steps=25,
        save_strategy="epoch",
        logging_steps=5,
        bf16=True,
        gradient_checkpointing=True,
        report_to="none",
        remove_unused_columns=False,
    )

    # Create trainer
    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # DPOTrainer creates implicit reference with LoRA
        args=training_args,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        tokenizer=tokenizer,
        peft_config=peft_config,
    )

    # Train
    print("\nStarting DPO training...")
    trainer.train()

    # Save the LoRA adapter (small — typically <100 MB)
    print(f"\nSaving LoRA adapter to: {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    # Print adapter size
    adapter_size = sum(
        os.path.getsize(os.path.join(OUTPUT_DIR, f))
        for f in os.listdir(OUTPUT_DIR)
        if os.path.isfile(os.path.join(OUTPUT_DIR, f))
    )
    print(f"Adapter size: {adapter_size / 1024 / 1024:.1f} MB")
    print(f"(vs ~16 GB for the full model — {adapter_size / 16e9 * 100:.2f}% of full size)")

    print("\nNext steps:")
    print("  bash serve_aligned.sh        # Serve base + aligned models")
    print("  python3 evaluate_alignment.py # Compare before and after")


if __name__ == "__main__":
    main()
