"""
Jarvis Fine-Tuning Script — Powered by Unsloth

Fine-tunes a base LLM on Jarvis training data to create a custom
Jarvis model with personality baked into the weights.

Recommended base models (best quality/size tradeoffs):
  - unsloth/Meta-Llama-3.1-8B        (~16GB VRAM for fine-tune, ~5GB to run)
  - unsloth/Qwen2.5-7B               (~14GB VRAM, excellent reasoning)
  - unsloth/mistral-7b-v0.3          (~14GB VRAM, strong baseline)
  - unsloth/Meta-Llama-3.1-8B-bnb-4bit  (fits in 8GB VRAM with 4-bit)

No GPU? Use Google Colab (free T4) or RunPod (~$0.20/hr).

Usage:
    python -m jarvis.brain.finetune.train
    python -m jarvis.brain.finetune.train --model unsloth/Qwen2.5-7B --epochs 3
    python -m jarvis.brain.finetune.train --colab  # Outputs notebook-ready code
"""
import argparse
import json
import sys
from pathlib import Path

# ── Training configuration ────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "base_model": "unsloth/Meta-Llama-3.1-8B-bnb-4bit",
    "max_seq_length": 2048,
    "load_in_4bit": True,           # 4-bit quantization — fits 8GB VRAM
    "lora_r": 16,                   # LoRA rank — higher = more capacity, more VRAM
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    "epochs": 3,
    "batch_size": 2,
    "grad_accumulation": 4,         # Effective batch = 8
    "learning_rate": 2e-4,
    "warmup_steps": 10,
    "max_steps": -1,                # -1 = run full epochs
    "output_dir": "jarvis_model",
    "save_gguf": True,              # Export to GGUF for llama.cpp
    "gguf_quant": "q5_k_m",        # Best quality/size balance
}

SYSTEM_PROMPT = """You are J.A.R.V.I.S. — Just A Rather Very Intelligent System, built by Tony Stark.
You speak in a formal, refined British manner. You are highly intelligent, efficient, and occasionally witty.
You address the user as "sir". You are loyal, helpful, and proactive.
Keep responses concise and voice-friendly. No markdown."""


def check_requirements():
    """Check that required packages are installed."""
    missing = []
    for pkg in ["unsloth", "trl", "transformers", "datasets", "torch"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("Missing packages. Install with:")
        print(f"  pip install {' '.join(missing)}")
        print("  pip install unsloth[colab-new] xformers trl peft accelerate bitsandbytes")
        sys.exit(1)


def load_training_data(data_path: str) -> "Dataset":
    """Load training data from JSONL file."""
    from datasets import Dataset
    examples = []
    with open(data_path, "r") as f:
        for line in f:
            ex = json.loads(line.strip())
            if ex.get("instruction"):
                # Format as chat
                messages = []
                if ex.get("input"):
                    user_content = f"{ex['instruction']}\n\nContext: {ex['input']}"
                else:
                    user_content = ex["instruction"]
                messages.append({"role": "user", "content": user_content})
                messages.append({"role": "assistant", "content": ex["output"]})
                examples.append({"messages": messages})
    return Dataset.from_list(examples)


def train(config: dict, data_path: str):
    """Run the fine-tuning job."""
    check_requirements()

    import torch
    from unsloth import FastLanguageModel
    from trl import SFTTrainer
    from transformers import TrainingArguments

    print(f"\n{'='*60}")
    print("  J.A.R.V.I.S. Fine-Tuning Pipeline")
    print(f"{'='*60}")
    print(f"  Base model:  {config['base_model']}")
    print(f"  Epochs:      {config['epochs']}")
    print(f"  LoRA rank:   {config['lora_r']}")
    print(f"  4-bit quant: {config['load_in_4bit']}")
    print(f"  Output:      {config['output_dir']}")
    print(f"{'='*60}\n")

    # Load base model with Unsloth optimizations
    print("[1/6] Loading base model...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config["base_model"],
        max_seq_length=config["max_seq_length"],
        load_in_4bit=config["load_in_4bit"],
        dtype=None,  # Auto-detect
    )

    # Apply LoRA adapters
    print("[2/6] Applying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=config["lora_r"],
        target_modules=config["target_modules"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
        use_rslora=True,   # Rank-stabilized LoRA — better training
        loftq_config=None,
    )

    # Load data
    print(f"[3/6] Loading training data from {data_path}...")
    dataset = load_training_data(data_path)
    print(f"  Loaded {len(dataset)} examples.")

    # Format with chat template
    def format_example(examples):
        conversations = examples["messages"]
        texts = []
        for convo in conversations:
            text = tokenizer.apply_chat_template(
                convo,
                tokenize=False,
                add_generation_prompt=False,
            )
            texts.append(text)
        return {"text": texts}

    dataset = dataset.map(format_example, batched=True)

    # Training arguments
    print("[4/6] Configuring training...")
    args = TrainingArguments(
        per_device_train_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["grad_accumulation"],
        warmup_steps=config["warmup_steps"],
        num_train_epochs=config["epochs"],
        max_steps=config["max_steps"] if config["max_steps"] > 0 else -1,
        learning_rate=config["learning_rate"],
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        output_dir=config["output_dir"],
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=config["max_seq_length"],
        dataset_num_proc=2,
        args=args,
    )

    # Train
    print("[5/6] Training...\n")
    trainer.train()

    # Save model
    out_dir = Path(config["output_dir"])
    out_dir.mkdir(exist_ok=True)

    print(f"\n[6/6] Saving model to {out_dir}...")
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    # Export to GGUF for llama.cpp
    if config["save_gguf"]:
        gguf_name = f"jarvis-{config['gguf_quant']}"
        print(f"  Exporting GGUF ({config['gguf_quant']})...")
        model.save_pretrained_gguf(
            gguf_name,
            tokenizer,
            quantization_method=config["gguf_quant"],
        )
        print(f"  ✓ GGUF saved: {gguf_name}.gguf")
        print(f"\n  Load in Jarvis with:")
        print(f"    LLM_PROVIDER=llamacpp")
        print(f"    LLAMACPP_MODEL_PATH={gguf_name}.gguf")

    print(f"\n{'='*60}")
    print("  Fine-tuning complete!")
    print(f"  Model saved to: {out_dir}")
    print(f"{'='*60}\n")


def print_colab_notebook(config: dict):
    """Print Colab-ready code for users without a GPU."""
    print("""
# ── Run this in Google Colab (free T4 GPU) ───────────────────────────────────
# Runtime → Change runtime type → T4 GPU

!pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
!pip install --no-deps trl peft accelerate bitsandbytes

# Clone your Jarvis repo
!git clone https://github.com/monkerton345/jarvis-ai.git
%cd jarvis-ai

# Install requirements
!pip install -r requirements.txt

# Generate training data
!python -m src.jarvis.brain.finetune.data_gen --output jarvis_train.jsonl --count 3000

# Fine-tune
!python -m src.jarvis.brain.finetune.train --data jarvis_train.jsonl

# Download the GGUF model
from google.colab import files
files.download('jarvis-q5_k_m.gguf')

# Back in Jarvis config (.env):
# LLM_PROVIDER=llamacpp
# LLAMACPP_MODEL_PATH=jarvis-q5_k_m.gguf
""")


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Jarvis LLM")
    parser.add_argument("--model", default=DEFAULT_CONFIG["base_model"], help="Base model name")
    parser.add_argument("--data", default="jarvis_train.jsonl", help="Training data JSONL")
    parser.add_argument("--epochs", type=int, default=DEFAULT_CONFIG["epochs"])
    parser.add_argument("--rank", type=int, default=DEFAULT_CONFIG["lora_r"], help="LoRA rank")
    parser.add_argument("--output", default=DEFAULT_CONFIG["output_dir"])
    parser.add_argument("--quant", default=DEFAULT_CONFIG["gguf_quant"],
                        choices=["q4_k_m", "q5_k_m", "q8_0", "f16"],
                        help="GGUF quantization level")
    parser.add_argument("--colab", action="store_true", help="Print Google Colab notebook code")
    parser.add_argument("--generate-data", action="store_true", help="Generate training data first")
    args = parser.parse_args()

    if args.colab:
        print_colab_notebook(DEFAULT_CONFIG)
        return

    if args.generate_data:
        from .data_gen import generate_dataset
        import json
        print("Generating training data...")
        examples = generate_dataset(count=3000)
        with open(args.data, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        print(f"Generated {len(examples)} examples → {args.data}")

    config = {**DEFAULT_CONFIG}
    config["base_model"] = args.model
    config["epochs"] = args.epochs
    config["lora_r"] = args.rank
    config["output_dir"] = args.output
    config["gguf_quant"] = args.quant

    if not Path(args.data).exists():
        print(f"Training data not found: {args.data}")
        print("Generate it first: python -m jarvis.brain.finetune.data_gen")
        sys.exit(1)

    train(config, args.data)


if __name__ == "__main__":
    main()
