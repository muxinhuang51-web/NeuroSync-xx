# Run the execution script with specified parameters
# echo "Starting Eng dataset processing..."
# python run_execuation.py --input "/home/wzhangeb/lancet/DatasetGeneration/dialog_history_run" --output "/home/wzhangeb/lancet/DatasetGeneration/processed_interactions_eng"

# Run the generation script with specified parameters
echo "Starting dataset generation..."
python run_generation.py --total 300 --parallel 5

# Run the execution script with specified parameters
echo "Starting dataset processing..."
python run_execuation.py --input "/home/wzhangeb/lancet/DatasetGeneration/dialog_history_run_audio" --output "/home/wzhangeb/lancet/DatasetGeneration/processed_interactions_audio"

echo "Dataset generation and processing complete!"