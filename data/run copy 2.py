import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from nasatlx import baseline_data, lancet_data

# Define dimension names in English
dimensions = ['Mental Demand', 'Physical Demand', 'Temporal Demand', 
              'Performance', 'Effort', 'Frustration']

def analyze_nasa_tlx(data):
    """Analyze NASA-TLX data and return results"""
    data_array = np.array(data)
    
    # Extract ratings (first 6 columns)
    ratings = data_array[:, :6]
    
    # Extract weight comparison data (next 15 columns)
    weight_comparisons = data_array[:, 6:21]
    
    # Initialize weight counts
    weights = np.zeros((len(data), 6))
    
    # Define dimension index pairs for each comparison
    comparisons = [
        (0, 1), (0, 2), (0, 4), (0, 3), (0, 5),  # Mental vs others
        (1, 2), (1, 4), (1, 3), (1, 5),          # Physical vs others
        (2, 4), (2, 3), (2, 5),                  # Temporal vs others
        (4, 3), (4, 5),                          # Effort vs others
        (3, 5)                                    # Performance vs Frustration
    ]
    
    # Calculate weights for each user
    for user_idx, user_comparisons in enumerate(weight_comparisons):
        for comp_idx, (dim1, dim2) in enumerate(comparisons):
            if user_comparisons[comp_idx] == 1:
                weights[user_idx, dim1] += 1
            else:
                weights[user_idx, dim2] += 1
    
    # Calculate average ratings and weights
    avg_ratings = np.mean(ratings, axis=0)
    avg_weights = np.mean(weights, axis=0)
    
    # Normalize weights
    normalized_weights = avg_weights / np.sum(avg_weights)
    
    # Calculate weighted scores
    weighted_scores = np.sum(ratings * (weights / 15), axis=1)
    avg_weighted_score = np.mean(weighted_scores)
    
    return {
        'avg_ratings': avg_ratings,
        'normalized_weights': normalized_weights,
        'avg_weighted_score': avg_weighted_score,
        'weighted_scores': weighted_scores
    }

# Analyze baseline and lancet data
baseline_results = analyze_nasa_tlx(baseline_data)
lancet_results = analyze_nasa_tlx(lancet_data)

# Create comparison figure with custom grid
plt.figure(figsize=(14, 8))
gs = plt.GridSpec(1, 4, height_ratios=[1])

# Compare dimension ratings with weight-encoded bar width - use 3 of 4 columns
ax1 = plt.subplot(gs[0, :3])
x = np.arange(len(dimensions))

# Calculate bar widths based on weights - use larger multiplier for wider bars
max_width = 0.35
width_multiplier = 6.0  # Increased from 4.0 to make bars wider
baseline_widths = baseline_results['normalized_weights'] * max_width * width_multiplier
lancet_widths = lancet_results['normalized_weights'] * max_width * width_multiplier

# Draw bars with varying widths
for i, (b_rating, l_rating, b_width, l_width) in enumerate(zip(
    baseline_results['avg_ratings'], 
    lancet_results['avg_ratings'],
    baseline_widths,
    lancet_widths
)):
    # Position bars with appropriate offsets to center them
    b_offset = -b_width/2
    l_offset = l_width/2
    
    ax1.bar(x[i] + b_offset, b_rating, width=b_width, 
           color='skyblue', edgecolor='black', linewidth=1)
    ax1.bar(x[i] + l_offset, l_rating, width=l_width, 
           color='salmon', edgecolor='black', linewidth=1)

# Custom legend for bar colors
ax1.bar([], [], color='skyblue', edgecolor='black', label='Baseline')
ax1.bar([], [], color='salmon', edgecolor='black', label='Lancet')
ax1.legend(loc='upper right')

# Create dimension labels with weight percentages
dimension_labels = []
avg_weights = (baseline_results['normalized_weights'] + lancet_results['normalized_weights']) / 2
for i, dim in enumerate(dimensions):
    weight_pct = avg_weights[i] * 100
    dimension_labels.append(f"{dim}\n(weight: {weight_pct:.1f}%)")

ax1.set_title('Dimension Ratings Comparison (Width = Weight)', fontsize=16)
ax1.set_xticks(x)
ax1.set_xticklabels(dimension_labels, rotation=45, ha='right', fontsize=10)
ax1.set_ylabel('Rating (1-20)', fontsize=14)
ax1.set_ylim(0, 21)
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Add difference annotations
for i, (b_score, l_score) in enumerate(zip(baseline_results['avg_ratings'], 
                                       lancet_results['avg_ratings'])):
    diff = b_score - l_score
    color = 'green' if diff > 0 else 'red'
    ax1.text(i, max(b_score, l_score) + 0.5, f'Diff: {abs(diff):.1f}', 
            ha='center', color=color, fontweight='bold')

# Compare weighted total scores - use 1 of 4 columns and make it shorter
ax2 = plt.subplot(gs[0, 3:])
scores = [baseline_results['avg_weighted_score'], lancet_results['avg_weighted_score']]
ax2.bar(['Baseline', 'Lancet'], scores, color=['skyblue', 'salmon'], 
       edgecolor='black', linewidth=1)

ax2.set_title('Weighted Score', fontsize=16)
ax2.set_ylabel('Score', fontsize=14)
ax2.grid(axis='y', linestyle='--', alpha=0.7)
ax2.set_ylim(0, 15)  # Set a lower upper limit to make the chart appear shorter

# Add score annotations
for i, score in enumerate(scores):
    ax2.text(i, score + 0.2, f'{score:.2f}', ha='center', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('nasa_tlx_comparison.png', dpi=300)