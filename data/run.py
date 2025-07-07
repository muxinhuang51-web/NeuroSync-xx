import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
from nasatlx import baseline_data, lancet_data
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

# Define dimension names in English
dimensions = ['Mental', 'Physical', 'Temporal', 
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
    
    # Calculate quartiles for each dimension
    quartiles = np.zeros((2, 6, 2))  # [baseline/lancet, dimension, lower/upper quartile]
    for i in range(6):
        dim_data = ratings[:, i]
        if i == 3:  # Adjust Failed Performance
            dim_data = 20 - dim_data
        quartiles[0, i, 0] = np.percentile(dim_data, 25)  # Lower quartile
        quartiles[0, i, 1] = np.percentile(dim_data, 75)  # Upper quartile
    
    return {
        'avg_ratings': avg_ratings,
        'normalized_weights': normalized_weights,
        'avg_weighted_score': avg_weighted_score,
        'weighted_scores': weighted_scores,
        'raw_ratings': ratings,
        'quartiles': quartiles
    }

# Analyze baseline and lancet data
baseline_results = analyze_nasa_tlx(baseline_data)
lancet_results = analyze_nasa_tlx(lancet_data)

# Function to find outliers using IQR method
def find_outliers(data):
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = []
    outlier_indices = []
    
    for i, val in enumerate(data):
        if val < lower_bound or val > upper_bound:
            outliers.append(val)
            outlier_indices.append(i)
    
    return outliers, outlier_indices

# Calculate quartiles for both datasets and find outliers
baseline_quartiles = []
lancet_quartiles = []
baseline_outliers = []
lancet_outliers = []

for i in range(len(dimensions)):
    # Get raw ratings for this dimension
    baseline_dim = baseline_results['raw_ratings'][:, i].copy()
    lancet_dim = lancet_results['raw_ratings'][:, i].copy()
    
    # For "Failed Performance" dimension, we need to correct the values
    if i == 3:
        baseline_dim = 20 - baseline_dim
        lancet_dim = 20 - lancet_dim
    
    # Calculate quartiles
    baseline_lower = np.percentile(baseline_dim, 25)
    baseline_upper = np.percentile(baseline_dim, 75)
    lancet_lower = np.percentile(lancet_dim, 25)
    lancet_upper = np.percentile(lancet_dim, 75)
    
    baseline_quartiles.append((baseline_lower, baseline_upper))
    lancet_quartiles.append((lancet_lower, lancet_upper))
    
    # Find outliers
    b_outliers, _ = find_outliers(baseline_dim)
    l_outliers, _ = find_outliers(lancet_dim)
    baseline_outliers.append(b_outliers)
    lancet_outliers.append(l_outliers)

# Perform t-tests for each dimension
t_test_results = []
for i in range(len(dimensions)):
    # Get raw ratings for this dimension
    baseline_dim = baseline_results['raw_ratings'][:, i]
    lancet_dim = lancet_results['raw_ratings'][:, i]
    
    # For "Failed Performance" dimension, we need to correct the values
    if i == 3:
        baseline_dim = 20 - baseline_dim
        lancet_dim = 20 - lancet_dim
    
    # Calculate t-test
    t_stat, p_value = stats.ttest_ind(baseline_dim, lancet_dim)
    t_test_results.append((t_stat, p_value))

# Create figure with fixed size
fig = plt.figure(figsize=(12.5, 7))

# Create custom subplot layout
left_plot = plt.subplot2grid((1, 4), (0, 0), colspan=3)
right_plot = fig.add_axes([0.75, 0.11, 0.2, 0.3])  # [left, bottom, width, height]
# Reduce the height of the weight plot from 0.3 to 0.25 and adjust position
weight_plot = fig.add_axes([0.75, 0.6, 0.2, 0.25])  # [left, bottom, width, height]

# Left plot - dimension ratings with uniform bar width
x = np.arange(len(dimensions))

# Define colors clearly
baseline_color = '#FAA254'  # Distinct blue
lancet_color = '#4AA5D9'    # Distinct salmon/red (for NeuroSync)
quartile_color = '#888888'  # Gray color for quartile lines
outlier_color = '#FF5733'   # Orange-red for outliers

# Set uniform bar widths
bar_width = 0.35

# Draw bars with uniform widths and add quartile lines
for i, (b_rating, l_rating) in enumerate(zip(
    baseline_results['avg_ratings'], 
    lancet_results['avg_ratings']
)):
    # Position bars with appropriate offsets to center them
    b_pos = x[i] - bar_width/2
    l_pos = x[i] + bar_width/2
    
    # Draw bars
    left_plot.bar(b_pos, b_rating, width=bar_width, 
           color=baseline_color, edgecolor='black', linewidth=1)
    left_plot.bar(l_pos, l_rating, width=bar_width, 
           color=lancet_color, edgecolor='black', linewidth=1)
    
    # Add quartile lines for baseline
    b_lower, b_upper = baseline_quartiles[i]
    
    # Draw horizontal quartile lines
    left_plot.plot(
        [b_pos - bar_width*0.3, b_pos + bar_width*0.3], 
        [b_lower, b_lower], 
        color=quartile_color, linewidth=0.8
    )
    left_plot.plot(
        [b_pos - bar_width*0.3, b_pos + bar_width*0.3], 
        [b_upper, b_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Connect quartiles with vertical line
    left_plot.plot(
        [b_pos, b_pos], 
        [b_lower, b_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Add quartile lines for NeuroSync
    l_lower, l_upper = lancet_quartiles[i]
    
    # Draw horizontal quartile lines
    left_plot.plot(
        [l_pos - bar_width*0.3, l_pos + bar_width*0.3], 
        [l_lower, l_lower], 
        color=quartile_color, linewidth=0.8
    )
    left_plot.plot(
        [l_pos - bar_width*0.3, l_pos + bar_width*0.3], 
        [l_upper, l_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Connect quartiles with vertical line
    left_plot.plot(
        [l_pos, l_pos], 
        [l_lower, l_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Plot outliers with star markers
    if baseline_outliers[i]:
        for outlier in baseline_outliers[i]:
            left_plot.plot(b_pos, outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)
    
    if lancet_outliers[i]:
        for outlier in lancet_outliers[i]:
            left_plot.plot(l_pos, outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)

# Create two separate legend elements
# 1. System legend (right side)
system_legend_elements = [
    Patch(facecolor=baseline_color, edgecolor='black', label='Baseline'),
    Patch(facecolor=lancet_color, edgecolor='black', label='NeuroSync'),
    Line2D([0], [0], marker='*', color='none', markerfacecolor='r', 
           markeredgecolor='black', markersize=10, label='Outlier')
]

# # 2. Significance legend (left side) - organized in two rows
# significance_legend_elements = [
#     Line2D([0], [0], marker='', color='none', label='† p<0.1        * p<0.05'),
#     Line2D([0], [0], marker='', color='none', label='** p<0.01      *** p<0.001')
# ]

# # Add both legends separately
# first_legend = left_plot.legend(handles=significance_legend_elements, loc='upper left', framealpha=0.9, title='Significance', fontsize=12)
# left_plot.add_artist(first_legend)  # Add the first legend back
left_plot.legend(handles=system_legend_elements, loc='upper right', framealpha=0.9, title='System', fontsize=12)

# Create dimension labels with sequence numbers
dimension_labels = []
for i, dim in enumerate(dimensions):
    dimension_labels.append(f"{i+1}. {dim}")

left_plot.set_title('Dimension Ratings Comparison', fontsize=16)
left_plot.set_xticks(x)
left_plot.set_xticklabels(dimension_labels, rotation=45, ha='right', fontsize=15)
left_plot.set_ylabel('Rating (1-20)', fontsize=18)
left_plot.set_ylim(0, 21)
left_plot.grid(axis='y', linestyle='--', alpha=0.7)

# Add difference annotations with significance markers
for i, ((b_score, l_score), (_, p_val)) in enumerate(zip(
    zip(baseline_results['avg_ratings'], lancet_results['avg_ratings']),
    t_test_results
)):
    diff = b_score - l_score
    color = 'green' if diff > 0 else 'red'
    
    # Add significance markers
    sig_marker = ''
    if p_val < 0.001:
        sig_marker = ' ***'
    elif p_val < 0.01:
        sig_marker = ' **'
    elif p_val < 0.05:
        sig_marker = ' *'
    elif p_val < 0.1:
        sig_marker = ' †'
    
    left_plot.text(i, max(b_score, l_score) + 0.5, 
            f'Diff: {abs(diff):.1f}{sig_marker}', 
            ha='center', color=color, fontsize=14, fontweight='bold')

# Right bottom plot - weighted total scores
scores = [baseline_results['avg_weighted_score'], lancet_results['avg_weighted_score']]
right_plot.bar(['Baseline', 'NeuroSync'], scores, color=[baseline_color, lancet_color], 
       edgecolor='black', linewidth=1)

right_plot.set_title('Weighted Score', fontsize=16)
# right_plot.set_ylabel('Score', fontsize=16)
right_plot.grid(axis='y', linestyle='--', alpha=0.7)
right_plot.set_ylim(0, 15)

# Increase font size for x-axis tick labels
right_plot.tick_params(axis='x', labelsize=16)  # Increase from default to 14pt

# Add score annotations
for i, score in enumerate(scores):
    right_plot.text(i, score + 0.2, f'{score:.2f}', ha='center', fontsize=14, fontweight='bold')

# t-test for weighted scores
t_stat, p_value = stats.ttest_ind(
    baseline_results['weighted_scores'], 
    lancet_results['weighted_scores']
)
significance = ''
if p_value < 0.001:
    significance = '***'
elif p_value < 0.01:
    significance = '**'
elif p_value < 0.05:
    significance = '*'
elif p_value < 0.1:
    significance = '†'

# Add p-value for weighted scores
right_plot.set_title(f'Weighted Score ({significance})', fontsize=16)

# Right top plot - dimension weights comparison as stacked bars
weight_plot.clear()  # Clear existing weight plot

# Use custom colors for dimensions instead of tab10 colormap
dimension_colors = ['#b3e2cd', '#fdcdac', '#cbd5e8', '#f4cae4', '#e6f5c9', '#fff2ae']

# Create stacked horizontal bar chart for each system (Baseline and NeuroSync)
baseline_weights = baseline_results['normalized_weights']
lancet_weights = lancet_results['normalized_weights']

# Reduce bar height from 0.5 to 0.35 to make them narrower
bar_height = 0.35

# Plot baseline weights (top bar)
left = 0
for i, weight in enumerate(baseline_weights):
    weight_plot.barh(1, width=weight, left=left, height=bar_height, 
                    color=dimension_colors[i], edgecolor='black', linewidth=1)
    
    # Add percentage label if segment is wide enough (> 7%)
    if weight > 0.07:
        weight_plot.text(left + weight/2, 1, f"{int(weight*100)}%", 
                        ha='center', va='center', fontsize=12, fontweight='bold')
    left += weight

# Plot NeuroSync weights (bottom bar)
left = 0
for i, weight in enumerate(lancet_weights):
    weight_plot.barh(0, width=weight, left=left, height=bar_height, 
                    color=dimension_colors[i], edgecolor='black', linewidth=1)
    
    # Add percentage label if segment is wide enough (> 7%)
    if weight > 0.07:
        weight_plot.text(left + weight/2, 0, f"{int(weight*100)}%", 
                        ha='center', va='center', fontsize=12, fontweight='bold')
    left += weight

# Set y-axis labels with NeuroSync split into two lines
weight_plot.set_yticks([0, 1])
weight_plot.set_yticklabels(['Ours', 'Base\nline'], fontsize=16)

# Create a custom legend for dimension numbers - more compact
legend_elements = []
for i, dim in enumerate(dimensions):
    legend_elements.append(Patch(facecolor=dimension_colors[i], edgecolor='black', 
                                label=f"{i+1}."))

# Arrange legend in multiple columns for better space usage
weight_plot.legend(handles=legend_elements, loc='upper center', 
                 bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=12)

weight_plot.set_title('Dimension Weights Distribution', fontsize=16)
weight_plot.set_xlim(0, 1.0)
weight_plot.set_xlabel('Weight Proportion', fontsize=12)
weight_plot.grid(axis='x', linestyle='--', alpha=0.7)

plt.savefig('nasa_tlx_comparison.png', dpi=300, bbox_inches='tight')