"""
Keyframe reduction algorithm for converting dense animation data to minimal Bezier keyframes.
Takes dense per-frame data and reduces it to the minimum number of keyframes needed
to approximate the same curve within a given error tolerance.
"""

import math
from typing import List, Tuple, Dict, Any

class KeyframeData:
    """Represents a keyframe with position, time, and Bezier handles"""
    def __init__(self, frame: float, value: float):
        self.frame = frame
        self.value = value
        self.handle_left = None
        self.handle_right = None
        self.interpolation = 'BEZIER'
    
    def __repr__(self):
        return f"KeyframeData(frame={self.frame}, value={self.value:.4f})"

def reduce_keyframes_to_bezier(dense_points: List[Tuple[float, float]], 
                              error_tolerance: float = 0.01,
                              max_iterations: int = 10) -> List[KeyframeData]:
    """
    Main function to reduce dense keyframe data to minimal Bezier keyframes.
    
    Args:
        dense_points: List of (frame, value) tuples representing the dense animation data
        error_tolerance: Maximum allowed error between original and approximated curves
        max_iterations: Maximum refinement iterations to prevent infinite loops
    
    Returns:
        List of KeyframeData objects with calculated Bezier handles
    """
    if len(dense_points) < 2:
        return [KeyframeData(frame, value) for frame, value in dense_points]
    
    print(f"Starting keyframe reduction: {len(dense_points)} points -> minimal keyframes")
    print(f"Error tolerance: {error_tolerance}")
    
    # Step 1: Find critical points (peaks, valleys, inflection points)
    critical_indices = find_critical_points(dense_points)
    print(f"Found {len(critical_indices)} critical points: {critical_indices}")
    
    # Step 2: Apply Douglas-Peucker algorithm for initial reduction
    reduced_indices = douglas_peucker_reduce(dense_points, error_tolerance)
    print(f"Douglas-Peucker reduced to {len(reduced_indices)} points: {reduced_indices}")
    
    # Step 3: Combine critical points with reduced points
    combined_indices = sorted(set(critical_indices + reduced_indices))
    print(f"Combined keyframe indices: {combined_indices}")
    
    # Step 4: Create initial keyframes
    initial_keyframes = [KeyframeData(dense_points[i][0], dense_points[i][1]) 
                        for i in combined_indices]
    
    # Step 5: Calculate Bezier handles for the keyframes
    keyframes_with_handles = calculate_bezier_handles(initial_keyframes, dense_points)
    
    # Step 6: Iterative refinement to improve accuracy
    final_keyframes = iterative_refinement(keyframes_with_handles, dense_points, 
                                         error_tolerance, max_iterations)
    
    print(f"Final result: {len(final_keyframes)} keyframes")
    for i, kf in enumerate(final_keyframes):
        print(f"  {i}: frame {kf.frame}, value {kf.value:.4f}")
    
    return final_keyframes

def find_critical_points(points: List[Tuple[float, float]]) -> List[int]:
    """
    Find critical points in the data: peaks, valleys, and inflection points.
    These points are essential for maintaining the shape of the curve.
    """
    if len(points) < 3:
        return [0, len(points) - 1] if len(points) > 1 else [0]
    
    critical_indices = [0]  # Always include start point
    
    # Calculate first and second derivatives (approximate)
    first_derivatives = []
    second_derivatives = []
    
    # First derivative (slope between adjacent points)
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        slope = dy / dx if dx != 0 else 0
        first_derivatives.append(slope)
    
    # Second derivative (change in slope)
    for i in range(len(first_derivatives) - 1):
        d_slope = first_derivatives[i + 1] - first_derivatives[i]
        second_derivatives.append(d_slope)
    
    # Find peaks and valleys (where first derivative changes sign)
    for i in range(1, len(first_derivatives)):
        prev_slope = first_derivatives[i - 1]
        curr_slope = first_derivatives[i]
        
        # Sign change indicates peak or valley
        if (prev_slope > 0 and curr_slope < 0) or (prev_slope < 0 and curr_slope > 0):
            critical_indices.append(i)
            print(f"Found peak/valley at point {i} (frame {points[i][0]})")
    
    # Find inflection points (where second derivative changes sign significantly)
    inflection_threshold = 0.001  # Minimum change to consider significant
    for i in range(1, len(second_derivatives)):
        prev_accel = second_derivatives[i - 1]
        curr_accel = second_derivatives[i]
        
        # Significant change in acceleration direction
        if abs(prev_accel - curr_accel) > inflection_threshold:
            if (prev_accel > 0 and curr_accel < 0) or (prev_accel < 0 and curr_accel > 0):
                critical_indices.append(i + 1)  # +1 because second derivative is offset
                print(f"Found inflection point at point {i + 1} (frame {points[i + 1][0]})")
    
    critical_indices.append(len(points) - 1)  # Always include end point
    
    # Remove duplicates and sort
    critical_indices = sorted(set(critical_indices))
    
    # Ensure we don't have indices out of bounds
    critical_indices = [i for i in critical_indices if 0 <= i < len(points)]
    
    return critical_indices

def douglas_peucker_reduce(points: List[Tuple[float, float]], tolerance: float) -> List[int]:
    """
    Apply Douglas-Peucker algorithm to reduce the number of points while maintaining shape.
    Returns indices of points to keep.
    """
    def perpendicular_distance(point, line_start, line_end):
        """Calculate perpendicular distance from point to line segment"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # If line segment has zero length, return distance to start point
        if x1 == x2 and y1 == y2:
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # Calculate perpendicular distance using cross product formula
        numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denominator = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
        
        return numerator / denominator if denominator > 0 else 0
    
    def douglas_peucker_recursive(start_idx: int, end_idx: int) -> List[int]:
        """Recursive implementation of Douglas-Peucker"""
        if end_idx <= start_idx + 1:
            return [start_idx, end_idx]
        
        # Find the point with maximum distance from line segment
        max_distance = 0
        max_index = start_idx
        
        line_start = points[start_idx]
        line_end = points[end_idx]
        
        for i in range(start_idx + 1, end_idx):
            distance = perpendicular_distance(points[i], line_start, line_end)
            if distance > max_distance:
                max_distance = distance
                max_index = i
        
        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            # Recursively simplify before and after the max point
            left_points = douglas_peucker_recursive(start_idx, max_index)
            right_points = douglas_peucker_recursive(max_index, end_idx)
            
            # Combine results (remove duplicate max_index)
            return left_points[:-1] + right_points
        else:
            # Max distance is within tolerance, keep only endpoints
            return [start_idx, end_idx]
    
    if len(points) < 2:
        return list(range(len(points)))
    
    result_indices = douglas_peucker_recursive(0, len(points) - 1)
    return sorted(set(result_indices))

def calculate_bezier_handles(keyframes: List[KeyframeData], 
                           original_points: List[Tuple[float, float]]) -> List[KeyframeData]:
    """
    Calculate appropriate Bezier handles for each keyframe to create smooth curves.
    """
    if len(keyframes) < 2:
        return keyframes
    
    print(f"Calculating Bezier handles for {len(keyframes)} keyframes")
    
    # Create a mapping from frame to original point for quick lookup
    frame_to_point = {frame: (frame, value) for frame, value in original_points}
    
    for i, keyframe in enumerate(keyframes):
        # Calculate tangent direction and handle lengths
        prev_kf = keyframes[i - 1] if i > 0 else None
        next_kf = keyframes[i + 1] if i < len(keyframes) - 1 else None
        
        # Calculate tangent based on neighboring keyframes
        if prev_kf and next_kf:
            # Interior keyframe - use slope between neighbors
            dx = next_kf.frame - prev_kf.frame
            dy = next_kf.value - prev_kf.value
            tangent_slope = dy / dx if dx != 0 else 0
        elif next_kf:
            # First keyframe - use slope to next
            dx = next_kf.frame - keyframe.frame
            dy = next_kf.value - keyframe.value
            tangent_slope = dy / dx if dx != 0 else 0
        elif prev_kf:
            # Last keyframe - use slope from previous
            dx = keyframe.frame - prev_kf.frame
            dy = keyframe.value - prev_kf.value
            tangent_slope = dy / dx if dx != 0 else 0
        else:
            # Single keyframe
            tangent_slope = 0
        
        # Calculate handle lengths (typically 1/3 of the distance to neighbors)
        if prev_kf:
            left_length = (keyframe.frame - prev_kf.frame) / 3.0
            keyframe.handle_left = (-left_length, -left_length * tangent_slope)
        
        if next_kf:
            right_length = (next_kf.frame - keyframe.frame) / 3.0
            keyframe.handle_right = (right_length, right_length * tangent_slope)
        
        print(f"Keyframe {i} (frame {keyframe.frame}): "
              f"left_handle={keyframe.handle_left}, right_handle={keyframe.handle_right}")
    
    return keyframes

def evaluate_bezier_curve(keyframes: List[KeyframeData], 
                         start_frame: float, end_frame: float, 
                         num_samples: int = 100) -> List[Tuple[float, float]]:
    """
    Evaluate the Bezier curve defined by keyframes at regular intervals.
    Returns sampled points for comparison with original data.
    """
    if len(keyframes) < 2:
        return [(kf.frame, kf.value) for kf in keyframes]
    
    sampled_points = []
    frame_step = (end_frame - start_frame) / (num_samples - 1) if num_samples > 1 else 0
    
    for i in range(num_samples):
        sample_frame = start_frame + i * frame_step
        
        # Find the segment containing this frame
        segment_start = None
        segment_end = None
        
        for j in range(len(keyframes) - 1):
            if keyframes[j].frame <= sample_frame <= keyframes[j + 1].frame:
                segment_start = keyframes[j]
                segment_end = keyframes[j + 1]
                break
        
        if segment_start and segment_end:
            # Interpolate using Bezier curve
            t = ((sample_frame - segment_start.frame) / 
                 (segment_end.frame - segment_start.frame) if 
                 segment_end.frame != segment_start.frame else 0)
            
            # Cubic Bezier interpolation
            value = evaluate_cubic_bezier(
                segment_start, segment_end, t
            )
            sampled_points.append((sample_frame, value))
        elif sample_frame <= keyframes[0].frame:
            sampled_points.append((sample_frame, keyframes[0].value))
        elif sample_frame >= keyframes[-1].frame:
            sampled_points.append((sample_frame, keyframes[-1].value))
    
    return sampled_points

def evaluate_cubic_bezier(start_kf: KeyframeData, end_kf: KeyframeData, t: float) -> float:
    """
    Evaluate a cubic Bezier curve between two keyframes at parameter t (0-1).
    """
    # Control points for the Bezier curve
    p0_frame, p0_value = start_kf.frame, start_kf.value
    p3_frame, p3_value = end_kf.frame, end_kf.value
    
    # Handle positions (absolute coordinates)
    if start_kf.handle_right:
        p1_frame = p0_frame + start_kf.handle_right[0]
        p1_value = p0_value + start_kf.handle_right[1]
    else:
        p1_frame, p1_value = p0_frame, p0_value
    
    if end_kf.handle_left:
        p2_frame = p3_frame + end_kf.handle_left[0]
        p2_value = p3_value + end_kf.handle_left[1]
    else:
        p2_frame, p2_value = p3_frame, p3_value
    
    # Cubic Bezier formula: B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
    one_minus_t = 1 - t
    
    # We only need to interpolate the value (y-coordinate)
    # The frame (x-coordinate) is determined by linear interpolation
    bezier_value = (
        one_minus_t**3 * p0_value +
        3 * one_minus_t**2 * t * p1_value +
        3 * one_minus_t * t**2 * p2_value +
        t**3 * p3_value
    )
    
    return bezier_value

def calculate_curve_error(original_points: List[Tuple[float, float]], 
                         approximated_points: List[Tuple[float, float]]) -> float:
    """
    Calculate the maximum error between original and approximated curves.
    Uses interpolation to compare at the same frame positions.
    """
    if not original_points or not approximated_points:
        return float('inf')
    
    max_error = 0.0
    
    # Create interpolation function for approximated curve
    approx_frames = [p[0] for p in approximated_points]
    approx_values = [p[1] for p in approximated_points]
    
    for orig_frame, orig_value in original_points:
        # Find approximated value at this frame using linear interpolation
        approx_value = interpolate_value(orig_frame, approx_frames, approx_values)
        
        error = abs(orig_value - approx_value)
        max_error = max(max_error, error)
    
    return max_error

def interpolate_value(target_frame: float, frames: List[float], values: List[float]) -> float:
    """
    Interpolate a value at target_frame using linear interpolation between known points.
    """
    if target_frame <= frames[0]:
        return values[0]
    if target_frame >= frames[-1]:
        return values[-1]
    
    # Find the segment containing target_frame
    for i in range(len(frames) - 1):
        if frames[i] <= target_frame <= frames[i + 1]:
            # Linear interpolation
            t = ((target_frame - frames[i]) / 
                 (frames[i + 1] - frames[i]) if frames[i + 1] != frames[i] else 0)
            return values[i] + t * (values[i + 1] - values[i])
    
    return values[0]  # Fallback

def iterative_refinement(keyframes: List[KeyframeData], 
                        original_points: List[Tuple[float, float]],
                        error_tolerance: float,
                        max_iterations: int = 10) -> List[KeyframeData]:
    """
    Iteratively refine the keyframes by adding points where error is highest.
    """
    current_keyframes = keyframes[:]
    
    for iteration in range(max_iterations):
        print(f"Refinement iteration {iteration + 1}")
        
        # Evaluate current curve
        start_frame = original_points[0][0]
        end_frame = original_points[-1][0]
        approximated = evaluate_bezier_curve(current_keyframes, start_frame, end_frame, 
                                           len(original_points))
        
        # Calculate error
        max_error = calculate_curve_error(original_points, approximated)
        print(f"  Current max error: {max_error:.6f} (tolerance: {error_tolerance})")
        
        if max_error <= error_tolerance:
            print(f"  Converged! Error within tolerance.")
            break
        
        # Find point with maximum error
        max_error_frame = None
        max_error_value = 0
        
        # Create interpolation for current approximation
        approx_frames = [p[0] for p in approximated]
        approx_values = [p[1] for p in approximated]
        
        for orig_frame, orig_value in original_points:
            approx_value = interpolate_value(orig_frame, approx_frames, approx_values)
            error = abs(orig_value - approx_value)
            
            if error > max_error_value:
                max_error_value = error
                max_error_frame = orig_frame
        
        if max_error_frame is None:
            break
        
        # Add a new keyframe at the point of maximum error
        # Find the original point data
        new_keyframe = None
        for frame, value in original_points:
            if frame == max_error_frame:
                new_keyframe = KeyframeData(frame, value)
                break
        
        if new_keyframe:
            # Insert in the correct position
            inserted = False
            for i in range(len(current_keyframes)):
                if current_keyframes[i].frame > new_keyframe.frame:
                    current_keyframes.insert(i, new_keyframe)
                    inserted = True
                    break
            
            if not inserted:
                current_keyframes.append(new_keyframe)
            
            # Recalculate handles for all keyframes
            current_keyframes = calculate_bezier_handles(current_keyframes, original_points)
            
            print(f"  Added keyframe at frame {max_error_frame} (error was {max_error_value:.6f})")
        else:
            break
    
    print(f"Refinement completed after {min(iteration + 1, max_iterations)} iterations")
    return current_keyframes


def convert_to_blender_keyframes(keyframe_data: List[KeyframeData], 
                                constraint, data_path: str = "offset_factor") -> None:
    """
    Apply the reduced keyframes to a Blender constraint or object property.
    """
    try:
        import bpy
        
        print(f"Applying {len(keyframe_data)} keyframes to {data_path}")
        
        for kf_data in keyframe_data:
            # Set the value and create keyframe
            setattr(constraint, data_path.split('.')[-1], kf_data.value)
            constraint.keyframe_insert(data_path=data_path, frame=kf_data.frame)
        
        # Set interpolation mode and handles
        if hasattr(constraint, 'id_data') and constraint.id_data.animation_data:
            action = constraint.id_data.animation_data.action
            constraint_path = f'constraints["{constraint.name}"].{data_path}'
            
            for fcurve in action.fcurves:
                if fcurve.data_path == constraint_path:
                    # Set all keyframes to Bezier
                    for i, keypoint in enumerate(fcurve.keyframe_points):
                        keypoint.interpolation = 'BEZIER'
                        
                        # Set handle types
                        keypoint.handle_left_type = 'FREE'
                        keypoint.handle_right_type = 'FREE'
                        
                        # Apply calculated handles if available
                        if i < len(keyframe_data):
                            kf_data = keyframe_data[i]
                            
                            if kf_data.handle_left:
                                left_frame = kf_data.frame + kf_data.handle_left[0]
                                left_value = kf_data.value + kf_data.handle_left[1]
                                keypoint.handle_left = (left_frame, left_value)
                            
                            if kf_data.handle_right:
                                right_frame = kf_data.frame + kf_data.handle_right[0]
                                right_value = kf_data.value + kf_data.handle_right[1]
                                keypoint.handle_right = (right_frame, right_value)
                    
                    print(f"Applied Bezier handles to {len(fcurve.keyframe_points)} keyframes")
                    break
        
    except Exception as e:
        print(f"Error applying keyframes to Blender: {e}")
        import traceback
        traceback.print_exc()