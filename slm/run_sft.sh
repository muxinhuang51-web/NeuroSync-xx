#!/bin/bash

echo "Running SFT experiments"
echo "Running SFT experiments" >> /home/wzhangeb/lancet/slm/sft.log

# Default values
SEQ_LENGTH=4800
LR=5e-5
TRAIN_BATCH=1
EVAL_BATCH=1
GRAD_ACCUM=8
EPOCHS=20
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
EVAL_STEPS=50         # Evaluate every 100 steps
SAVE_STEPS=250        # Save every 1000 steps

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
  --eval_split $EVAL_SPLIT > logs_deepseek_${MODEL_TAG}_gpu0.log 2>&1 &

# Deepseek Qwen-7B on GPU 2
MODEL_TAG="Qwen-7B"
python /home/wzhangeb/lancet/slm/sft.py \
  --model_tag "$MODEL_TAG" \
  --seq_length $SEQ_LENGTH \
  --gpu_ids "2" \
  --learning_rate $LR \
  --train_batch_size $TRAIN_BATCH \
  --eval_batch_size $EVAL_BATCH \
  --gradient_accumulation $GRAD_ACCUM \
  --epochs $EPOCHS \
  --weight_decay $WEIGHT_DECAY \
  --output_dir "${OUTPUT_DIR}_deepseek_${MODEL_TAG}_gpu2" \
  --eval_strategy $EVAL_STRATEGY \
  --save_strategy $SAVE_STRATEGY \
  --eval_steps $EVAL_STEPS \
  --save_steps $SAVE_STEPS \
  --lora_r $LORA_R \
  --lora_alpha $LORA_ALPHA \
  --lora_dropout $LORA_DROPOUT \
  --dataset_path "$DATASET_PATH" \
  --eval_split $EVAL_SPLIT > logs_deepseek_${MODEL_TAG}_gpu2.log 2>&1 &

# Wait for Group 1 to complete
wait
echo "Group 1 completed"
echo "Waiting for 2 minute to allow GPU memory to clear..."
sleep 120  # Wait for 120 seconds


echo "Single 2: Running single 1.5B models"

# Deepseek Qwen-1.5B on GPU 0
MODEL_TAG="Qwen-1.5B"
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
  --eval_split $EVAL_SPLIT > logs_deepseek_${MODEL_TAG}_gpu0.log 2>&1 &

wait
echo "Group 2 completed"
echo "All SFT training completed successfully."