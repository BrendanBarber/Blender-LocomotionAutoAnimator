#!/usr/bin/env python3
"""
Standalone curvature visualization script.
Run this outside of Blender with: python visualize_curvature.py path/to/debug_file.json

Requirements: pip install matplotlib numpy
"""

import json
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D


def load_debug_data(filepath):
    """Load the exported debug data from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading debug data: {e}")
        return None


def visualize_curvature_data(data):
    """Create comprehensive visualization of the curvature data."""
    
    positions = np.array(data['positions'])
    raw_curvatures = np.array(data['curvatures']['raw'])
    smoothed_curvatures = np.array(data['curvatures']['smoothed']) if data['curvatures']['smoothed'] else None
    thresholded_curvatures = np.array(data['curvatures']['thresholded']) if data['curvatures']['thresholded'] else None
    speeds = np.array(data['speeds']) if data['speeds'] else None
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(f'Curvature Analysis: {data["curve_name"]}', fontsize=16)
    
    # Extract coordinates
    x_coords = positions[:, 0]
    y_coords = positions[:, 1]
    z_coords = positions[:, 2]
    
    # Create color map based on curvature
    curvatures_for_color = smoothed_curvatures if smoothed_curvatures is not None else raw_curvatures
    if len(curvatures_for_color) > 0 and max(curvatures_for_color) > 0:
        norm_curvatures = curvatures_for_color / max(curvatures_for_color)
        colors = plt.cm.RdYlGn_r(norm_curvatures)
    else:
        colors = ['blue'] * len(curvatures_for_color)
    
    # Ensure colors array matches the number of segments (positions - 1)
    # If we have N positions, we have N-1 segments
    num_segments = len(positions) - 1
    if len(colors) != num_segments:
        # If curvatures is shorter than segments, extend it
        if len(colors) < num_segments:
            # Repeat the last color for missing segments
            last_color = colors[-1] if len(colors) > 0 else [0, 0, 1, 1]  # Default blue
            colors = list(colors) + [last_color] * (num_segments - len(colors))
        else:
            # If curvatures is longer, trim it
            colors = colors[:num_segments]
    
    # 1. Animation timeline: Position (0-1) over frames
    ax1 = fig.add_subplot(231)
    
    if data.get('animation_data') and data['animation_data'].get('keyframes'):
        # Extract frame and position data
        keyframes = data['animation_data']['keyframes']
        frames = [kf[0] for kf in keyframes]
        positions_01 = [kf[1] for kf in keyframes]
        
        # Plot the animation curve
        ax1.plot(frames, positions_01, 'b-', linewidth=2, label='Position on Path')
        ax1.scatter(frames[::max(1, len(frames)//20)], 
                   positions_01[::max(1, len(frames)//20)], 
                   c='red', s=20, alpha=0.7, label='Sample Points')
        
        # Color the line based on speed (derivative of position)
        if len(positions_01) > 1:
            speeds_from_pos = []
            for i in range(1, len(positions_01)):
                frame_diff = frames[i] - frames[i-1]
                pos_diff = positions_01[i] - positions_01[i-1]
                speed = pos_diff / frame_diff if frame_diff > 0 else 0
                speeds_from_pos.append(abs(speed))
            
            # Plot speed as background color
            if speeds_from_pos:
                norm_speeds = np.array(speeds_from_pos) / max(speeds_from_pos) if max(speeds_from_pos) > 0 else np.zeros_like(speeds_from_pos)
                for i in range(len(speeds_from_pos)):
                    color_intensity = norm_speeds[i]
                    ax1.axvspan(frames[i], frames[i+1], alpha=0.2, 
                               color=plt.cm.RdYlGn_r(color_intensity))
        
        ax1.set_title('Animation: Position on Path (0-1) vs Frame\n(Background: Red=Fast, Green=Slow)')
        ax1.set_xlabel('Frame')
        ax1.set_ylabel('Path Position (0-1)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_ylim(-0.05, 1.05)
        
        # Add frame range info
        start_frame = data['animation_data'].get('start_frame', frames[0])
        end_frame = data['animation_data'].get('end_frame', frames[-1])
        ax1.axvline(x=start_frame, color='green', linestyle=':', alpha=0.7, label='Start')
        ax1.axvline(x=end_frame, color='red', linestyle=':', alpha=0.7, label='End')
        
    else:
        # Fallback: show a linear animation for reference
        ax1.text(0.5, 0.5, 'No Animation Data Available\n\nLinear motion would look like:', 
                transform=ax1.transAxes, ha='center', va='center', fontsize=12)
        
        # Show what linear motion would look like
        dummy_frames = np.linspace(0, 100, 101)
        dummy_positions = np.linspace(0, 1, 101)
        ax1.plot(dummy_frames, dummy_positions, 'gray', linestyle='--', alpha=0.5, label='Linear Reference')
        ax1.set_title('Animation Timeline (No Data - Showing Linear Reference)')
        ax1.set_xlabel('Frame')
        ax1.set_ylabel('Path Position (0-1)')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
    
    # 2. Top-down view (X-Y plane)
    ax2 = fig.add_subplot(232)
    
    # Plot curve with curvature coloring
    for i in range(len(positions) - 1):
        ax2.plot([x_coords[i], x_coords[i+1]], 
                [y_coords[i], y_coords[i+1]], 
                color=colors[i], linewidth=3)
    
    # Add direction arrows
    arrow_step = max(1, len(positions) // 15)
    for i in range(0, len(positions) - 1, arrow_step):
        if i + 1 < len(positions):
            dx = x_coords[i+1] - x_coords[i]
            dy = y_coords[i+1] - y_coords[i]
            if abs(dx) > 1e-6 or abs(dy) > 1e-6:  # Avoid zero-length arrows
                ax2.arrow(x_coords[i], y_coords[i], dx*0.8, dy*0.8, 
                         head_width=0.05, head_length=0.05, fc='black', ec='black', alpha=0.7)
    
    ax2.set_title('Top View (X-Y)\nwith Direction Arrows')
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_aspect('equal')
    ax2.grid(True, alpha=0.3)
    
    # 3. Side view (X-Z plane)
    ax3 = fig.add_subplot(233)
    
    for i in range(len(positions) - 1):
        ax3.plot([x_coords[i], x_coords[i+1]], 
                [z_coords[i], z_coords[i+1]], 
                color=colors[i], linewidth=3)
    
    ax3.set_title('Side View (X-Z)')
    ax3.set_xlabel('X')
    ax3.set_ylabel('Z')
    ax3.grid(True, alpha=0.3)
    
    # 4. Curvature comparison plot
    ax4 = fig.add_subplot(234)
    
    t_values = np.linspace(0, 1, len(raw_curvatures))
    
    # Plot different curvature versions
    ax4.plot(t_values, raw_curvatures, 'b-', linewidth=1, label='Raw Curvature', alpha=0.7)
    
    if thresholded_curvatures is not None:
        ax4.plot(t_values, thresholded_curvatures, 'orange', linewidth=2, 
                label='Thresholded', alpha=0.8)
    
    if smoothed_curvatures is not None:
        ax4.plot(t_values, smoothed_curvatures, 'r-', linewidth=2, label='Smoothed')
    
    # Add threshold line if we can infer it
    threshold = 0.001  # Default, could be extracted from data
    ax4.axhline(y=threshold, color='gray', linestyle='--', alpha=0.7,
               label=f'Threshold ({threshold})')
    
    ax4.set_title('Curvature Comparison')
    ax4.set_xlabel('Curve Parameter (0-1)')
    ax4.set_ylabel('Curvature')
    ax4.grid(True, alpha=0.3)
    ax4.legend()
    
    # 5. Speed plot or statistics
    ax5 = fig.add_subplot(235)
    
    if speeds is not None:
        speed_t_values = np.linspace(0, 1, len(speeds))
        ax5.plot(speed_t_values, speeds, 'g-', linewidth=3, label='Speed Factor')
        ax5.fill_between(speed_t_values, speeds, alpha=0.3, color='green')
        ax5.set_title('Speed Factor Along Curve')
        ax5.set_xlabel('Curve Parameter (0-1)')
        ax5.set_ylabel('Speed Factor')
        ax5.grid(True, alpha=0.3)
        ax5.legend()
    else:
        ax5.axis('off')
        stats = data['statistics']
        stats_text = f"""
Curve Statistics:

Total Points: {stats['total_points']}
Curvature Range: {stats['curvature_range'][0]:.6f} to {stats['curvature_range'][1]:.6f}
Mean Curvature: {stats['mean_curvature']:.6f}
Points Above Threshold: {stats['points_above_threshold']}

Max Curvature: {max(raw_curvatures):.6f}
Min Curvature: {min(raw_curvatures):.6f}
Std Dev: {np.std(raw_curvatures):.6f}
"""
        ax5.text(0.05, 0.95, stats_text, transform=ax5.transAxes, 
                fontsize=10, ha='left', va='top', family='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
        ax5.set_title('Statistics')
    
    # 6. Curvature distribution histogram
    ax6 = fig.add_subplot(236)
    
    # Create histogram of curvature values
    ax6.hist(raw_curvatures, bins=30, alpha=0.7, color='skyblue', edgecolor='black', label='Raw')
    if smoothed_curvatures is not None:
        ax6.hist(smoothed_curvatures, bins=30, alpha=0.7, color='red', edgecolor='black', label='Smoothed')
    
    ax6.axvline(x=threshold, color='orange', linestyle='--', linewidth=2, label=f'Threshold ({threshold})')
    ax6.set_title('Curvature Distribution')
    ax6.set_xlabel('Curvature Value')
    ax6.set_ylabel('Frequency')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Print detailed analysis
    print("\n" + "="*60)
    print("DETAILED CURVATURE ANALYSIS")
    print("="*60)
    print(f"Curve: {data['curve_name']}")
    print(f"Total points: {len(positions)}")
    print(f"Total segments: {len(positions) - 1}")
    print(f"Curvature values: {len(raw_curvatures)}")
    print(f"Color array size: {len(colors)}")
    print(f"Curvature range: {min(raw_curvatures):.6f} to {max(raw_curvatures):.6f}")
    
    # Animation analysis
    if data.get('animation_data') and data['animation_data'].get('keyframes'):
        keyframes = data['animation_data']['keyframes']
        frames = [kf[0] for kf in keyframes]
        positions_01 = [kf[1] for kf in keyframes]
        
        print(f"\nAnimation Analysis:")
        print(f"Frame range: {frames[0]} to {frames[-1]} ({len(frames)} keyframes)")
        print(f"Position range: {min(positions_01):.6f} to {max(positions_01):.6f}")
        
        # Calculate actual speeds from keyframes
        if len(positions_01) > 1:
            frame_speeds = []
            for i in range(1, len(positions_01)):
                frame_diff = frames[i] - frames[i-1]
                pos_diff = positions_01[i] - positions_01[i-1]
                speed = pos_diff / frame_diff if frame_diff > 0 else 0
                frame_speeds.append(speed)
            
            if frame_speeds:
                print(f"Speed range: {min(frame_speeds):.6f} to {max(frame_speeds):.6f} (pos/frame)")
                print(f"Average speed: {np.mean(frame_speeds):.6f} pos/frame")
    else:
        print(f"\nNo animation keyframe data available")
    
    # Find peaks in curvature
    high_curvature_threshold = np.percentile(raw_curvatures, 90)  # Top 10%
    high_curv_indices = [i for i, c in enumerate(raw_curvatures) if c > high_curvature_threshold]
    
    if high_curv_indices:
        print(f"\nTop 10 highest curvature points (>{high_curvature_threshold:.6f}):")
        sorted_indices = sorted(high_curv_indices, key=lambda i: raw_curvatures[i], reverse=True)[:10]
        for i, idx in enumerate(sorted_indices):
            pos = positions[idx]
            print(f"  {i+1:2d}. Point {idx:3d}: curvature = {raw_curvatures[idx]:.6f} at ({pos[0]:7.3f}, {pos[1]:7.3f}, {pos[2]:7.3f})")
    
    print("="*60)
    
    return fig


def main():
    if len(sys.argv) != 2:
        print("Usage: python visualize_curvature.py <debug_data.json>")
        print("Example: python visualize_curvature.py curvature_debug_Curve.json")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    print(f"Loading debug data from: {filepath}")
    data = load_debug_data(filepath)
    
    if data is None:
        print("Failed to load debug data")
        sys.exit(1)
    
    print(f"Visualizing curvature data for: {data['curve_name']}")
    fig = visualize_curvature_data(data)
    
    # Save plot if desired
    output_path = filepath.replace('.json', '_visualization.png')
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Visualization saved to: {output_path}")
    
    plt.show()


if __name__ == "__main__":
    main()