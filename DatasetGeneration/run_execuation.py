import argparse
import multiprocessing as mp
from tqdm import tqdm
import time
import os
import sys
import glob
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dataset.graph_build import InteractionProcessor

def worker(file_path, raw_data_folder, output_base_folder):
    """
    Worker function that creates an InteractionProcessor instance and processes interactions
    
    Args:
        file_path: Path to the user JSON file
        raw_data_folder: Folder containing raw data from generation
        output_base_folder: Base folder for processed graphs
    """
    # Extract user index from filename
    filename = os.path.basename(file_path)
    match = re.search(r'user_(\d+)\.json', filename)
    if not match:
        return file_path, False, "Invalid filename format"
    
    idx = int(match.group(1))
    
    # Create a unique output folder for this user index
    output_folder = os.path.join(output_base_folder, f"user_{idx}")
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        processor = InteractionProcessor(raw_data_folder, output_folder)
        processor.process_interactions(user_index=idx)
        return file_path, True, None
    except Exception as e:
        return file_path, False, str(e)

def run_parallel(raw_data_folder, output_folder, parallel_count=5):
    """
    Run InteractionProcessor instances in parallel batches
    
    Args:
        raw_data_folder (str): Folder containing raw dialog data from generation
        output_folder (str): Base folder for storing processed graph data
        parallel_count (int): Fixed number of parallel processes to use
    """
    # Get all user files directly
    file_pattern = os.path.join(raw_data_folder, "user_*.json")
    files = glob.glob(file_pattern)
    
    print(f"Found {len(files)} files to process")
    print(f"Starting parallel execution with {parallel_count} workers")
    print(f"Reading from: {raw_data_folder}")
    print(f"Writing to: {output_folder}")
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Calculate number of batches needed
    num_batches = (len(files) + parallel_count - 1) // parallel_count
    
    # Create a pool of workers
    pool = mp.Pool(processes=parallel_count)
    
    # Process in batches
    for batch_idx in range(num_batches):
        start_idx = batch_idx * parallel_count
        end_idx = min(start_idx + parallel_count, len(files))
        batch_files = files[start_idx:end_idx]
        
        batch_file_names = [os.path.basename(f) for f in batch_files]
        print(f"\nBatch {batch_idx + 1}/{num_batches}: Processing files {batch_file_names}")
        
        # Submit batch jobs to the pool
        results = []
        for file_path in batch_files:
            results.append(pool.apply_async(worker, (file_path, raw_data_folder, output_folder)))
        
        # Wait for all jobs in this batch to complete
        for r in tqdm(results):
            file_path, success, error = r.get()
            if success:
                print(f"{os.path.basename(file_path)} processing completed successfully")
            else:
                print(f"{os.path.basename(file_path)} processing failed with error: {error}")
            
        print(f"Completed batch {batch_idx + 1}/{num_batches}")
    
    # Clean up
    pool.close()
    pool.join()
    print(f"All {len(files)} files processed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run InteractionProcessor in parallel")
    parser.add_argument("--parallel", type=int, default=10,
                        help="Fixed number of worker processes to use (default: 5)")
    parser.add_argument("--input", type=str, default="/home/wzhangeb/lancet/DatasetGeneration/dialog_history_run_CHN",
                        help="Folder containing raw dialog data from generation")
    parser.add_argument("--output", type=str, default="/home/wzhangeb/lancet/DatasetGeneration/processed_interactions_CHN_1",
                        help="Base folder for processed graph data output")
    
    args = parser.parse_args()
    
    start_time = time.time()
    run_parallel(args.input, args.output, args.parallel)
    end_time = time.time()
    
    print(f"Execution completed in {end_time - start_time:.2f} seconds")