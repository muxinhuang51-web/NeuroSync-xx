import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from nasatlx import baseline_data, lancet_data

# Define dimension names in English
dimensions = ['Mental Demand', 'Physical Demand', 'Temporal Demand', 
              'Failed Performance', 'Effort', 'Frustration']

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
        (0, 1), (0, 2), (0, 4), (0, 3), (0, 5),
        (1, 2), (1, 4), (1, 3), (1, 5),
        (2, 4), (2, 3), (2, 5),
        (4, 3), (4, 5),
        (3, 5)
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
    avg_ratings[3] = 20 - avg_ratings[3]
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

# Create figure with fixed size
fig = plt.figure(figsize=(14, 8))

# Create custom subplot layout
left_plot = plt.subplot2grid((1, 4), (0, 0), colspan=3)
right_plot = fig.add_axes([0.75, 0.11, 0.2, 0.3])  # [left, bottom, width, height]

# Left plot - dimension ratings with weight-encoded bar width
x = np.arange(len(dimensions))

# Define colors clearly
baseline_color = '#6BAED6'  # Distinct blue
lancet_color = '#FB8072'    # Distinct salmon/red

# Calculate bar widths based on weights
max_width = 0.35
width_multiplier = 6.0
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
    
    left_plot.bar(x[i] + b_offset, b_rating, width=b_width, 
           color=baseline_color, edgecolor='black', linewidth=1)
    left_plot.bar(x[i] + l_offset, l_rating, width=l_width, 
           color=lancet_color, edgecolor='black', linewidth=1)

# # Custom legend
# left_plot.bar([], [], color=baseline_color, edgecolor='black', label='Baseline')
# left_plot.bar([], [], color=lancet_color, edgecolor='black', label='Lancet')
# left_plot.legend(loc='upper right')
# Create dummy patches for the legend to ensure colors match exactly

from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=baseline_color, edgecolor='black', label='Baseline'),
    Patch(facecolor=lancet_color, edgecolor='black', label='Lancet')
]
left_plot.legend(handles=legend_elements, loc='upper right')

# Create dimension labels with weight percentages
dimension_labels = []
avg_weights = (baseline_results['normalized_weights'] + lancet_results['normalized_weights']) / 2
for i, dim in enumerate(dimensions):
    weight_pct = avg_weights[i] * 100
    dimension_labels.append(f"{dim}\n(weight: {weight_pct:.1f}%)")

left_plot.set_title('Dimension Ratings Comparison (Width = Weight)', fontsize=16)
left_plot.set_xticks(x)
left_plot.set_xticklabels(dimension_labels, rotation=45, ha='right', fontsize=10)
left_plot.set_ylabel('Rating (1-20)', fontsize=14)
left_plot.set_ylim(0, 21)
left_plot.grid(axis='y', linestyle='--', alpha=0.7)

# Add difference annotations
for i, (b_score, l_score) in enumerate(zip(baseline_results['avg_ratings'], 
                                       lancet_results['avg_ratings'])):
    diff = b_score - l_score
    color = 'green' if diff > 0 else 'red'
    left_plot.text(i, max(b_score, l_score) + 0.5, f'Diff: {abs(diff):.1f}', 
            ha='center', color=color, fontweight='bold')

# Right plot - weighted total scores (half height)
scores = [baseline_results['avg_weighted_score'], lancet_results['avg_weighted_score']]
right_plot.bar(['Baseline', 'Lancet'], scores, color=[baseline_color, lancet_color], 
       edgecolor='black', linewidth=1)

right_plot.set_title('Weighted Score', fontsize=16)
right_plot.set_ylabel('Score', fontsize=14)
right_plot.grid(axis='y', linestyle='--', alpha=0.7)
right_plot.set_ylim(0, 15)

# Add score annotations
for i, score in enumerate(scores):
    right_plot.text(i, score + 0.2, f'{score:.2f}', ha='center', fontsize=14, fontweight='bold')

plt.savefig('nasa_tlx_comparison.png', dpi=300, bbox_inches='tight')