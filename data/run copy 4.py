import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
from nasatlx import baseline_data, lancet_data
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

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
fig = plt.figure(figsize=(14, 8))

# Create custom subplot layout
left_plot = plt.subplot2grid((1, 4), (0, 0), colspan=3)
right_plot = fig.add_axes([0.75, 0.11, 0.2, 0.3])  # [left, bottom, width, height]

# Left plot - dimension ratings with weight-encoded bar width
x = np.arange(len(dimensions))

# Define colors clearly
baseline_color = '#6BAED6'  # Distinct blue
lancet_color = '#FB8072'    # Distinct salmon/red
quartile_color = '#888888'  # Gray color for quartile lines
outlier_color = '#FF5733'   # Orange-red for outliers

# Calculate bar widths based on weights
max_width = 0.35
width_multiplier = 6.0
baseline_widths = baseline_results['normalized_weights'] * max_width * width_multiplier
lancet_widths = lancet_results['normalized_weights'] * max_width * width_multiplier

# Draw bars with varying widths and add quartile lines
for i, (b_rating, l_rating, b_width, l_width) in enumerate(zip(
    baseline_results['avg_ratings'], 
    lancet_results['avg_ratings'],
    baseline_widths,
    lancet_widths
)):
    # Position bars with appropriate offsets to center them
    b_offset = -b_width/2
    l_offset = l_width/2
    
    # Draw bars
    left_plot.bar(x[i] + b_offset, b_rating, width=b_width, 
           color=baseline_color, edgecolor='black', linewidth=1)
    left_plot.bar(x[i] + l_offset, l_rating, width=l_width, 
           color=lancet_color, edgecolor='black', linewidth=1)
    
    # Add quartile lines for baseline - with shorter width and connected by vertical line
    b_lower, b_upper = baseline_quartiles[i]
    width_factor = 0.6  # Shorter horizontal lines (60% of bar width)
    
    # Central position for the quartile lines
    b_center = x[i] + b_offset
    
    # Draw horizontal quartile lines (shorter)
    left_plot.plot(
        [b_center - b_width*width_factor/2, b_center + b_width*width_factor/2], 
        [b_lower, b_lower], 
        color=quartile_color, linewidth=0.8
    )
    left_plot.plot(
        [b_center - b_width*width_factor/2, b_center + b_width*width_factor/2], 
        [b_upper, b_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Connect quartiles with vertical line
    left_plot.plot(
        [b_center, b_center], 
        [b_lower, b_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Add quartile lines for lancet - with shorter width and connected by vertical line
    l_lower, l_upper = lancet_quartiles[i]
    
    # Central position for the quartile lines
    l_center = x[i] + l_offset
    
    # Draw horizontal quartile lines (shorter)
    left_plot.plot(
        [l_center - l_width*width_factor/2, l_center + l_width*width_factor/2], 
        [l_lower, l_lower], 
        color=quartile_color, linewidth=0.8
    )
    left_plot.plot(
        [l_center - l_width*width_factor/2, l_center + l_width*width_factor/2], 
        [l_upper, l_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Connect quartiles with vertical line
    left_plot.plot(
        [l_center, l_center], 
        [l_lower, l_upper], 
        color=quartile_color, linewidth=0.8
    )
    
    # Plot outliers with star markers
    if baseline_outliers[i]:
        for outlier in baseline_outliers[i]:
            left_plot.plot(x[i] + b_offset, outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)
    
    if lancet_outliers[i]:
        for outlier in lancet_outliers[i]:
            left_plot.plot(x[i] + l_offset, outlier, 'r*', ms=10, markeredgecolor='black', zorder=5)

# Create two separate legend elements
# 1. System legend (right side)
system_legend_elements = [
    Patch(facecolor=baseline_color, edgecolor='black', label='Baseline'),
    Patch(facecolor=lancet_color, edgecolor='black', label='Lancet'),
    Line2D([0], [0], marker='*', color='none', markerfacecolor='r', 
           markeredgecolor='black', markersize=10, label='Outlier')
]

# 2. Significance legend (left side) - organized in two rows
significance_legend_elements = [
    Line2D([0], [0], marker='', color='none', label='† p<0.1        * p<0.05'),
    Line2D([0], [0], marker='', color='none', label='** p<0.01      *** p<0.001')
]

# Add both legends separately
# Need to add the legends again because adding a new legend removes the previous one
first_legend = left_plot.legend(handles=significance_legend_elements, loc='upper left', framealpha=0.9, title='Significance')
left_plot.add_artist(first_legend)  # Add the first legend back
left_plot.legend(handles=system_legend_elements, loc='upper right', framealpha=0.9, title='System')

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

# Add difference annotations with significance markers only (no p-values)
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
            ha='center', color=color, fontweight='bold')

# Right plot - weighted total scores
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

# Also perform t-test for weighted scores
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
right_plot.set_title(f'Weighted Score (p={p_value:.3f}{significance})', fontsize=16)

plt.savefig('nasa_tlx_comparison.png', dpi=300, bbox_inches='tight')