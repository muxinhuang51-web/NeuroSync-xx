import argparse
import multiprocessing as mp
from tqdm import tqdm
import time
from debate_based_generation import fake_MAGS, MultiAgentCodeGenSimulator

def worker(idx):
    """Worker function that creates a fake_MAGS instance and runs one conversation turn"""
    try:
        agent = MultiAgentCodeGenSimulator(
            main_task="创建一个Python程序处理已有mp3音频，识别其中的语音内容并将其转换为文本格式输出，同时对识别出的关键词进行情感分析。",
            dialog_save_dir="dialog_history_run_audio",
            user_index=idx
        )
        result = agent.run_simulation()
        return idx
    except Exception as e:
        print(f"Error in worker {idx}: {e}")
        # 返回一个特殊的值表示失败，或者记录日志后返回 None
        return None

def run_parallel(total_executions, parallel_count):
    """
    Run fake_MAGS instances in parallel batches
    
    Args:
        total_executions (int): Total number of agents to create and run
        parallel_count (int): Number of parallel processes to run
    """
    print(f"Starting parallel execution of {total_executions} tasks with {parallel_count} workers")
    
    # Calculate number of batches needed
    indices = list(range(total_executions))
    num_batches = (total_executions + parallel_count - 1) // parallel_count
    
    # Create a pool of workers
    pool = mp.Pool(processes=parallel_count)
    
    # Process in batches
    for batch_idx in range(num_batches):
        start_idx = batch_idx * parallel_count
        end_idx = min(start_idx + parallel_count, total_executions)
        batch_indices = indices[start_idx:end_idx]
        
        print(f"\nBatch {batch_idx + 1}/{num_batches}: Processing indices {start_idx} to {end_idx-1}")
        
        # Submit batch jobs to the pool
        results = []
        for idx in tqdm(batch_indices):
            results.append(pool.apply_async(worker, (idx,)))
            
        # Wait for all jobs in this batch to complete
        for r in results:
            r.get()
            
        print(f"Completed batch {batch_idx + 1}/{num_batches}")
    
    # Clean up
    pool.close()
    pool.join()
    print(f"All {total_executions} executions completed successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fake_MAGS agents in parallel")
    parser.add_argument("--total", type=int, default=100, 
                        help="Total number of agents to create and run")
    parser.add_argument("--parallel", type=int, default=5,
                        help="Number of parallel processes to run")
    
    args = parser.parse_args()
    
    start_time = time.time()
    run_parallel(args.total, args.parallel)
    end_time = time.time()
    
    print(f"Execution completed in {end_time - start_time:.2f} seconds")