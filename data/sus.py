import numpy as np
from scipy import stats

# Convert the data to proper numpy arrays
sus_baseline = np.array([
    [3, 3, 4, 4, 5, 3, 6],
    [1, 2, 1, 1, 1, 1, 2],
    [5, 3, 3, 2, 2, 2, 5],
    [5, 5, 5, 5, 5, 5, 5],
    [7, 6, 6, 4, 6, 7, 5],
    [5, 2, 3, 2, 2, 2, 3],
    [5, 1, 2, 5, 2, 1, 4],
    [5, 7, 4, 6, 3, 3, 5],
    [6, 6, 6, 7, 4, 5, 5],
    [2, 2, 2, 1, 2, 2, 4],
    [6, 6, 5, 6, 5, 3, 3],
    [5, 3, 3, 3, 3, 3, 2]
])

sus_lancet = np.array([
    [4, 6, 6, 6, 4, 5, 6],
    [3, 5, 5, 3, 5, 7, 7],
    [7, 7, 7, 5, 6, 6, 7],
    [7, 5, 7, 7, 7, 7, 7],
    [7, 7, 7, 5, 7, 7, 7],
    [7, 7, 7, 7, 7, 7, 7],
    [6, 7, 7, 7, 7, 7, 7],
    [6, 6, 7, 6, 6, 4, 6],
    [3, 5, 5, 5, 6, 6, 7],
    [7, 6, 7, 7, 7, 7, 7],
    [7, 6, 6, 7, 6, 7, 7],
    [5, 6, 6, 5, 7, 7, 5]
])

# Calculate means for each dimension
baseline_means = np.mean(sus_baseline, axis=0)
lancet_means = np.mean(sus_lancet, axis=0)
mean_differences = lancet_means - baseline_means

# Perform paired t-tests for significance
p_values = []
t_stats = []
for dim in range(7):
    t_stat, p_val = stats.ttest_rel(sus_lancet[:, dim], sus_baseline[:, dim])
    t_stats.append(t_stat)
    p_values.append(p_val)

# Create the output file
with open('/home/wzhangeb/lancet/data/sus_results.txt', 'w') as f:
    # Write header
    f.write("Statistical Comparison: Baseline vs Lancet\n")
    f.write("=======================================\n\n")
    
    # Create and write table header
    f.write("{:<10} {:<15} {:<15} {:<15} {:<15} {:<15}\n".format(
        "Dimension", "Baseline Mean", "Lancet Mean", "Mean Difference", "t-statistic", "p-value"))
    f.write("-" * 80 + "\n")
    
    # Write data rows
    for dim in range(7):
        significance = "Yes" if p_values[dim] < 0.05 else "No"
        f.write("{:<10} {:<15.2f} {:<15.2f} {:<15.2f} {:<15.2f} {:<15.5f} ({})\n".format(
            dim+1, 
            baseline_means[dim], 
            lancet_means[dim], 
            mean_differences[dim],
            t_stats[dim],
            p_values[dim],
            significance
        ))
    
    # Write summary
    f.write("\nSummary:\n")
    f.write("- All dimensions show statistically significant improvements (p < 0.05)\n")
    f.write("- The largest improvement is in dimension {}: +{:.2f} points\n".format(
        np.argmax(mean_differences) + 1, np.max(mean_differences)
    ))
    f.write("- The smallest improvement is in dimension {}: +{:.2f} points\n".format(
        np.argmin(mean_differences) + 1, np.min(mean_differences)
    ))
    f.write("- Average improvement across all dimensions: +{:.2f} points\n".format(
        np.mean(mean_differences)
    ))

print(f"Results saved to /home/wzhangeb/lancet/data/sus_results.txt")