#!/bin/bash

echo "Running SFT experiments"
echo "Running SFT experiments" >> /home/wzhangeb/lancet/slm/sft.log

# Default values
SEQ_LENGTH=4800
LR=5e-5
TRAIN_BATCH=1
EVAL_BATCH=1
GRAD_ACCUM=8
EPOCHS=2
WEIGHT_DECAY=0.01
OUTPUT_DIR="./results_sft"
LORA_R=8
LORA_ALPHA=32
LORA_DROPOUT=0.1
DATASET_PATH="dialog_dataset_audio.json"
EVAL_SPLIT=0.05

# Strategy settings
EVAL_STRATEGY="steps"  # Use steps instead of epoch
SAVE_STRATEGY="steps"  # Use steps instead of epoch
EVAL_STEPS=500         # Evaluate every 100 steps
SAVE_STEPS=30        # Save every 1000 steps

echo "Group 1: Running both 8B and 7B models in parallel"

# Deepseek Llama-8B on GPU 0
MODEL_TAG="Llama-8B"
python /home/wzhangeb/lancet/slm/sft.py \
  --model_tag "$MODEL_TAG" \
  --seq_length $SEQ_LENGTH \
  --gpu_ids "0" \
  --learning_rate $LR \
  --train_batch_size $TRAIN_BATCH \
  --eval_batch_size $EVAL_BATCH \
  --gradient_accumulation $GRAD_ACCUM \
  --epochs $EPOCHS \
  --weight_decay $WEIGHT_DECAY \
  --output_dir "${OUTPUT_DIR}_deepseek_${MODEL_TAG}_gpu0" \
  --eval_strategy $EVAL_STRATEGY \
  --save_strategy $SAVE_STRATEGY \
  --eval_steps $EVAL_STEPS \
  --save_steps $SAVE_STEPS \
  --lora_r $LORA_R \
  --lora_alpha $LORA_ALPHA \
  --lora_dropout $LORA_DROPOUT \
  --dataset_path "$DATASET_PATH" \
  --eval_split $EVAL_SPLIT > logs_deepseek_${MODEL_TAG}_gpu0.log