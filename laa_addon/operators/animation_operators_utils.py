"""
Utility functions for animation operators
"""

import bpy
import bmesh
import math
from mathutils import Vector

def clear_selective_animation(target_obj, start_frame, end_frame, path_obj=None):
    """
    Clear animation data for path animations using a hybrid approach:
    - Clear ALL location/rotation keyframes in the frame range (range-based)
    - Use precise tracking for constraint cleanup (if path_obj provided)
    """
    try:
        cleanup_performed = False
        
        if path_obj:
            # Use hybrid approach: range-based for transforms, precise for constraints
            cleanup_performed |= _cleanup_hybrid_animation_data(target_obj, path_obj, start_frame, end_frame)
            
            # Also clean up any armature animation data
            armature_obj = _find_armature(target_obj)
            if armature_obj and armature_obj != target_obj:
                cleanup_performed |= _cleanup_armature_path_animation(armature_obj, path_obj.name)
            elif armature_obj == target_obj:
                # If target is the armature, clean up NLA strips but preserve any follow path keyframes
                cleanup_performed |= _cleanup_armature_path_animation(armature_obj, path_obj.name)
                
            if cleanup_performed:
                print(f"Cleared animation data for path: {path_obj.name} (range-based transforms + precise constraints)")
            else:
                print(f"No animation data found for path: {path_obj.name}")
                
        else:
            # Fallback to original frame-range based clearing
            cleanup_performed = _clear_animation_by_frame_range(target_obj, start_frame, end_frame)
            
        return cleanup_performed
        
    except Exception as e:
        print(f"Error in selective animation clearing: {e}")
        import traceback
        traceback.print_exc()
        return False

def _cleanup_hybrid_animation_data(target_obj, path_obj, start_frame, end_frame):
    """
    Hybrid cleanup: 
    1. Use tracking data to clear ALL previously created keyframes (including those outside current range)
    2. Then clear any remaining keyframes in the current range (safety net)
    3. Handle constraints with precise tracking
    """
    cleanup_performed = False
    
    try:
        if not target_obj.animation_data or not target_obj.animation_data.action:
            print("No animation data on target object")
            return cleanup_performed
            
        action = target_obj.animation_data.action
        
        # Get stored tracking data
        tracking_key = f"keyframe_tracking_{target_obj.name}"
        keyframe_data = path_obj.get(tracking_key)
        
        if keyframe_data:
            print(f"Using tracking data to clear previously created keyframes")
            
            # 1. PRECISE CLEARING: Clear tracked location/rotation keyframes (including outside current range)
            for data_path in ["location", "rotation_euler", "rotation_quaternion"]:
                frames_to_clear = keyframe_data.get(data_path, [])
                if frames_to_clear:
                    cleanup_performed |= _clear_keyframes_at_frames(action, data_path, frames_to_clear)
                    print(f"Cleared {len(frames_to_clear)} tracked {data_path} keyframes: {frames_to_clear}")
            
            # 2. PRECISE CONSTRAINT CLEARING: Use stored tracking data for constraints
            constraint_data = keyframe_data.get("constraints", {})
            for constraint_name, constraint_props in constraint_data.items():
                for prop_name, frames_to_clear in constraint_props.items():
                    constraint_data_path = f'constraints["{constraint_name}"].{prop_name}'
                    cleanup_performed |= _clear_keyframes_at_frames(action, constraint_data_path, frames_to_clear)
            
            # Remove the constraint itself
            if constraint_data:
                constraint_name = list(constraint_data.keys())[0]
                constraint_to_remove = None
                for constraint in target_obj.constraints:
                    if constraint.name == constraint_name:
                        constraint_to_remove = constraint
                        break
                
                if constraint_to_remove:
                    target_obj.constraints.remove(constraint_to_remove)
                    cleanup_performed = True
                    print(f"Removed constraint: {constraint_name}")
            
            # Clear the tracking data since we've cleaned up
            if tracking_key in path_obj:
                del path_obj[tracking_key]
                print("Cleared tracking data")
        
        else:
            print(f"No tracking data found, using fallback cleanup methods")
        
        # 3. RANGE-BASED SAFETY NET: Clear any remaining location/rotation keyframes in current range
        # This catches any keyframes that weren't tracked or were created manually
        print(f"Safety net: clearing any remaining location/rotation keyframes in range {start_frame}-{end_frame}")
        transform_paths = ['location', 'rotation_euler', 'rotation_quaternion']
        
        for data_path in transform_paths:
            fcurves_to_process = []
            for fcurve in action.fcurves:
                if fcurve.data_path == data_path:
                    fcurves_to_process.append(fcurve)
            
            for fcurve in fcurves_to_process:
                keyframes_to_remove = []
                
                # Find ANY remaining keyframes within the new frame range
                for i, keyframe in enumerate(fcurve.keyframe_points):
                    if start_frame <= keyframe.co[0] <= end_frame:
                        keyframes_to_remove.append(i)
                
                # Remove keyframes in reverse order to maintain indices
                if keyframes_to_remove:
                    print(f"Safety net: removing {len(keyframes_to_remove)} additional {data_path} keyframes in range")
                    for i in reversed(keyframes_to_remove):
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[i])
                        cleanup_performed = True
                
                # If fcurve has no keyframes left, remove it entirely
                if len(fcurve.keyframe_points) == 0:
                    action.fcurves.remove(fcurve)
                    print(f"Removed empty fcurve: {data_path}")
        
        # 4. CONSTRAINT FALLBACK: Remove constraints by name pattern if no tracking data handled them
        if not keyframe_data:
            print(f"Fallback: constraint cleanup by name pattern")
            constraint_name = f"FollowPath_{path_obj.name}"
            constraints_to_remove = []
            
            for constraint in target_obj.constraints:
                if constraint.type == 'FOLLOW_PATH' and constraint.name == constraint_name:
                    constraints_to_remove.append(constraint)
            
            for constraint in constraints_to_remove:
                target_obj.constraints.remove(constraint)
                cleanup_performed = True
                print(f"Removed constraint by name: {constraint.name}")
                
            # Also clear any constraint keyframes by name pattern
            fcurves_to_remove = []
            for fcurve in action.fcurves:
                if (fcurve.data_path.startswith('constraints[') and 
                    f'"{constraint_name}"' in fcurve.data_path):
                    fcurves_to_remove.append(fcurve)
            
            for fcurve in fcurves_to_remove:
                action.fcurves.remove(fcurve)
                cleanup_performed = True
                print(f"Removed constraint fcurve: {fcurve.data_path}")
        
        if cleanup_performed:
            print(f"Hybrid cleanup completed: precise tracking + safety net for range {start_frame}-{end_frame}")
            
    except Exception as e:
        print(f"Error during hybrid animation cleanup: {e}")
        import traceback
        traceback.print_exc()
    
    return cleanup_performed

def store_keyframe_tracking_data(path_obj, target_obj, constraint_name, keyframe_data):
    """
    Store tracking data for keyframes created by this path animation.
    
    keyframe_data should be a dict like:
    {
        "location": [start_frame, end_frame, end_frame + 1],
        "rotation_euler": [start_frame, end_frame, end_frame + 1],
        "constraints": {
            "FollowPath_PathName": {
                "offset_factor": [start_frame, start_frame+1, ..., end_frame],
                "influence": [start_frame-1, start_frame, end_frame, end_frame+1]
            }
        }
    }
    """
    try:
        # Store the tracking data on the path object
        tracking_key = f"keyframe_tracking_{target_obj.name}"
        path_obj[tracking_key] = keyframe_data
        
        print(f"Stored keyframe tracking data for {target_obj.name}:")
        for data_path, frames in keyframe_data.items():
            if data_path == "constraints":
                for constraint_name, constraint_data in frames.items():
                    for prop, prop_frames in constraint_data.items():
                        print(f"  {constraint_name}.{prop}: {len(prop_frames)} keyframes")
            else:
                print(f"  {data_path}: {len(frames)} keyframes at frames {frames}")
                
    except Exception as e:
        print(f"Error storing keyframe tracking data: {e}")

def _cleanup_tracked_animation_data(target_obj, path_obj):
    """Clean up animation data using stored tracking information"""
    cleanup_performed = False
    
    try:
        # Get the stored tracking data
        tracking_key = f"keyframe_tracking_{target_obj.name}"
        keyframe_data = path_obj.get(tracking_key)
        
        if not keyframe_data:
            print(f"No tracking data found for {target_obj.name}, falling back to constraint-based cleanup")
            return _cleanup_path_animation_data(target_obj, path_obj.name)
        
        print(f"Using tracked keyframe data to clean up {target_obj.name}")
        
        if not target_obj.animation_data or not target_obj.animation_data.action:
            print("No animation data on target object")
            return cleanup_performed
            
        action = target_obj.animation_data.action
        
        # Clean up transform keyframes (location, rotation)
        for data_path in ["location", "rotation_euler", "rotation_quaternion"]:
            frames_to_clear = keyframe_data.get(data_path, [])
            if frames_to_clear:
                cleanup_performed |= _clear_keyframes_at_frames(action, data_path, frames_to_clear)
        
        # Clean up constraint keyframes
        constraint_data = keyframe_data.get("constraints", {})
        for constraint_name, constraint_props in constraint_data.items():
            for prop_name, frames_to_clear in constraint_props.items():
                constraint_data_path = f'constraints["{constraint_name}"].{prop_name}'
                cleanup_performed |= _clear_keyframes_at_frames(action, constraint_data_path, frames_to_clear)
        
        # Remove the constraint itself
        constraint_name = list(constraint_data.keys())[0] if constraint_data else f"FollowPath_{path_obj.name}"
        constraint_to_remove = None
        for constraint in target_obj.constraints:
            if constraint.name == constraint_name:
                constraint_to_remove = constraint
                break
        
        if constraint_to_remove:
            target_obj.constraints.remove(constraint_to_remove)
            cleanup_performed = True
            print(f"Removed constraint: {constraint_name}")
        
        # Clear the tracking data since we've cleaned up
        if tracking_key in path_obj:
            del path_obj[tracking_key]
            print("Cleared tracking data")
            
    except Exception as e:
        print(f"Error during tracked animation cleanup: {e}")
        import traceback
        traceback.print_exc()
    
    return cleanup_performed

def _clear_keyframes_at_frames(action, data_path, frames_to_clear):
    """Remove keyframes at specific frames for a given data path"""
    cleanup_performed = False
    
    try:
        # Find all fcurves for this data path
        fcurves_to_process = []
        for fcurve in action.fcurves:
            if fcurve.data_path == data_path:
                fcurves_to_process.append(fcurve)
        
        for fcurve in fcurves_to_process:
            keyframes_to_remove = []
            
            # Find keyframes at the specified frames
            for i, keyframe in enumerate(fcurve.keyframe_points):
                if keyframe.co[0] in frames_to_clear:
                    keyframes_to_remove.append(i)
            
            # Remove keyframes in reverse order to maintain indices
            for i in reversed(keyframes_to_remove):
                fcurve.keyframe_points.remove(fcurve.keyframe_points[i])
                cleanup_performed = True
            
            # If fcurve has no keyframes left, remove it entirely
            if len(fcurve.keyframe_points) == 0:
                action.fcurves.remove(fcurve)
                print(f"Removed empty fcurve: {data_path}")
        
        if cleanup_performed:
            print(f"Cleared {len(frames_to_clear)} keyframes from {data_path}")
            
    except Exception as e:
        print(f"Error clearing keyframes for {data_path}: {e}")
    
    return cleanup_performed

def _cleanup_path_animation_data(target_obj, path_name):
    """Clean up animation data created by a specific path"""
    cleanup_performed = False
    
    try:
        # Clean up Follow Path constraints and related keyframes
        if target_obj.animation_data and target_obj.animation_data.action:
            action = target_obj.animation_data.action
            fcurves_to_remove = []
            
            # Find fcurves related to the specific Follow Path constraint
            constraint_name = f"FollowPath_{path_name}"
            
            for fcurve in action.fcurves:
                try:
                    should_remove = False
                    
                    # Remove constraint-related keyframes for this specific path
                    if (fcurve.data_path.startswith('constraints[') and 
                        (f'"{constraint_name}"' in fcurve.data_path)):
                        should_remove = True
                        print(f"Marking constraint fcurve for removal: {fcurve.data_path}")
                    
                    # For location/rotation keyframes, check if they were likely created by path animation
                    elif fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:
                        # Check if this fcurve looks like path animation
                        if _is_likely_path_animation_fcurve(fcurve, target_obj, path_name):
                            should_remove = True
                            print(f"Marking location/rotation fcurve for removal: {fcurve.data_path}[{fcurve.array_index}]")
                    
                    if should_remove:
                        fcurves_to_remove.append(fcurve)
                
                except (AttributeError, ReferenceError):
                    # FCurve or its data may have been invalidated
                    continue
            
            # Remove the identified fcurves
            for fcurve in fcurves_to_remove:
                try:
                    action.fcurves.remove(fcurve)
                    cleanup_performed = True
                except (AttributeError, ReferenceError):
                    # FCurve may have been invalidated
                    continue
        
        # Remove Follow Path constraints created by this path
        constraints_to_remove = []
        if hasattr(target_obj, 'constraints'):
            constraint_name = f"FollowPath_{path_name}"
            for constraint in target_obj.constraints:
                try:
                    if (constraint.type == 'FOLLOW_PATH' and 
                        constraint.name == constraint_name):
                        constraints_to_remove.append(constraint)
                except (AttributeError, ReferenceError):
                    # Constraint may have been invalidated
                    continue
        
        for constraint in constraints_to_remove:
            try:
                constraint_name = constraint.name  # Store name before removal
                target_obj.constraints.remove(constraint)
                cleanup_performed = True
                print(f"Removed Follow Path constraint: {constraint_name}")
            except (AttributeError, ReferenceError):
                # Constraint may have been invalidated
                continue
    
    except Exception as e:
        print(f"Error during path animation cleanup: {e}")
    
    return cleanup_performed

def _cleanup_armature_path_animation(armature_obj, path_name):
    """Clean up NLA strips and tracks created by a specific path"""
    cleanup_performed = False
    
    try:
        if not armature_obj.animation_data:
            return False
        
        # Remove NLA tracks created by this path
        tracks_to_remove = []
        for track in armature_obj.animation_data.nla_tracks:
            try:
                if track.name.startswith(f"LAA_{path_name}"):
                    tracks_to_remove.append(track)
            except (AttributeError, ReferenceError):
                # Track may have been invalidated
                continue
        
        for track in tracks_to_remove:
            try:
                track_name = track.name  # Store name before removal
                armature_obj.animation_data.nla_tracks.remove(track)
                cleanup_performed = True
                print(f"Removed NLA track: {track_name}")
            except (AttributeError, ReferenceError):
                # Track may have been invalidated
                continue
    
    except Exception as e:
        print(f"Error during armature animation cleanup: {e}")
    
    return cleanup_performed

def _is_likely_path_animation_fcurve(fcurve, target_obj, path_name):
    """
    Determine if an fcurve was likely created by path animation.
    This is a heuristic approach since we can't always know for certain.
    """
    try:
        # If there are very few keyframes, it might be path animation
        # (path animations typically have start/end keyframes)
        keyframe_count = len(fcurve.keyframe_points)
        
        if keyframe_count <= 4:  # Typical for path animations (start, end, maybe +1 frame)
            # Check if keyframes align with typical path animation patterns
            frames = [kf.co[0] for kf in fcurve.keyframe_points]
            
            # Look for patterns like consecutive frames at the end (typical of path animations)
            consecutive_end_frames = 0
            if len(frames) >= 2:
                frames.sort()
                for i in range(len(frames) - 1):
                    if frames[i + 1] - frames[i] == 1:  # Consecutive frames
                        consecutive_end_frames += 1
            
            # If we see consecutive frames (common in path animations), it's likely path-related
            if consecutive_end_frames > 0:
                return True
            
            # For location fcurves specifically, if there are exactly 2-3 keyframes, 
            # it's often from path animation
            if fcurve.data_path == 'location' and 2 <= keyframe_count <= 3:
                return True
        
        # Additional check: if all keyframes have the same value (common for offset animations)
        if keyframe_count >= 2:
            values = [kf.co[1] for kf in fcurve.keyframe_points]
            if len(set(values)) == 1:  # All values are the same
                return True
        
        return False
        
    except Exception as e:
        print(f"Error checking if fcurve is path animation: {e}")
        return False

def _find_armature(target_obj):
    """Find an armature object - either the target itself or its child"""
    # Check if target is an armature
    if target_obj.type == 'ARMATURE':
        return target_obj
    
    # Check direct children for armature
    for child in target_obj.children:
        if child.type == 'ARMATURE':
            return child
    
    # Check if target has an armature modifier pointing to an armature
    if hasattr(target_obj, 'modifiers'):
        for modifier in target_obj.modifiers:
            if modifier.type == 'ARMATURE' and modifier.object:
                return modifier.object
    
    # Recursively check children's children (one level deep)
    for child in target_obj.children:
        for grandchild in child.children:
            if grandchild.type == 'ARMATURE':
                return grandchild
    
    return None

def _clear_animation_by_frame_range(target_obj, start_frame, end_frame):
    """
    Original frame-range based clearing (fallback method)
    """
    cleanup_performed = False
    
    # Clear position and rotation keyframes in frame range
    if target_obj.animation_data and target_obj.animation_data.action:
        action = target_obj.animation_data.action
        
        # Data paths we want to clear
        data_paths_to_clear = ['location', 'rotation_euler']
        
        for data_path in data_paths_to_clear:
            # Find all fcurves for this data path (x, y, z components)
            fcurves_to_process = []
            for fcurve in action.fcurves:
                if fcurve.data_path == data_path:
                    fcurves_to_process.append(fcurve)
            
            # Remove keyframes in the specified range for each fcurve
            for fcurve in fcurves_to_process:
                keyframes_to_remove = []
                
                # Find keyframes within the frame range
                for i, keyframe in enumerate(fcurve.keyframe_points):
                    if start_frame <= keyframe.co[0] <= end_frame:
                        keyframes_to_remove.append(i)
                
                # Remove keyframes in reverse order to maintain indices
                for i in reversed(keyframes_to_remove):
                    fcurve.keyframe_points.remove(fcurve.keyframe_points[i])
                    cleanup_performed = True
                
                # If fcurve has no keyframes left, remove it entirely
                if len(fcurve.keyframe_points) == 0:
                    action.fcurves.remove(fcurve)
        
        if cleanup_performed:
            print(f"Cleared location and rotation keyframes between frames {start_frame}-{end_frame}")
    
    # Remove follow path constraints that are active in the frame range
    constraints_to_remove = []
    
    for constraint in target_obj.constraints:
        if constraint.type == 'FOLLOW_PATH':
            should_remove = False
            
            # Check if constraint has influence > 0 in the frame range
            if hasattr(constraint, 'influence'):
                # Check if there are keyframes for influence
                if target_obj.animation_data and target_obj.animation_data.action:
                    action = target_obj.animation_data.action
                    influence_path = f'constraints["{constraint.name}"].influence'
                    
                    # Find the influence fcurve
                    influence_fcurve = None
                    for fcurve in action.fcurves:
                        if fcurve.data_path == influence_path:
                            influence_fcurve = fcurve
                            break
                    
                    if influence_fcurve:
                        # Check if any keyframe in range has influence > 0
                        for keyframe in influence_fcurve.keyframe_points:
                            frame = keyframe.co[0]
                            influence_value = keyframe.co[1]
                            
                            if start_frame <= frame <= end_frame and influence_value > 0:
                                should_remove = True
                                break
                    else:
                        # No keyframes for influence, check current value
                        if constraint.influence > 0:
                            should_remove = True
                else:
                    # No animation data, check current influence value
                    if constraint.influence > 0:
                        should_remove = True
            
            if should_remove:
                constraints_to_remove.append(constraint)
    
    # Remove the identified constraints
    for constraint in constraints_to_remove:
        print(f"Removing follow path constraint: {constraint.name}")
        target_obj.constraints.remove(constraint)
        cleanup_performed = True
    
    return cleanup_performed

def apply_speed_control(follow_path_constraint, curve_obj, start_frame, end_frame, 
                        min_speed_factor=0.5, 
                        max_speed_factor=1.0,
                        curvature_threshold=0.001):
    """
    Apply curvature-based speed control to a Follow Path constraint.
    Slows down on sharp curves, speeds up on straight sections.
    
    curvature_threshold: Minimum curvature value to consider. Lower values are treated as 0.0 (straight).
    """
    try:
        import bmesh
        import mathutils
        import math
        
        total_frames = end_frame - start_frame
        if total_frames <= 0:
            return False
            
        # Get curve mesh representation for sampling
        context = bpy.context
        depsgraph = context.evaluated_depsgraph_get()
        curve_eval = curve_obj.evaluated_get(depsgraph)
        
        # Convert curve to mesh to sample the actual geometry
        mesh = curve_eval.to_mesh()
        if not mesh.vertices or len(mesh.vertices) < 3:
            curve_eval.to_mesh_clear()
            return False

        # Increase resolution for sampling.
        original_resolution = curve_obj.data.resolution_u
        original_render_resolution = curve_obj.data.render_resolution_u

        curve_obj.data.resolution_u = 64
        curve_obj.data.render_resolution_u = 64

        positions = []
        mesh = curve_eval.to_mesh()
        for v in mesh.vertices:
            positions.append(curve_obj.matrix_world @ v.co)

        curve_eval.to_mesh_clear()

        # Calculate curvature at each point along the curve mesh
        curvatures = []
        
        step = 3
        for i in range(step, len(positions) - step):
            p1 = positions[i - step]
            p2 = positions[i]
            p3 = positions[i + step]
            
            # Calculate vectors from current point to neighbors
            v1 = (p1 - p2).normalized()  # Vector pointing backward
            v2 = (p3 - p2).normalized()  # Vector pointing forward
            
            # Calculate the angle between the vectors
            # The dot product gives us cos(angle)
            dot_product = v1.dot(v2)
            # Clamp to avoid numerical errors with acos
            dot_product = max(-1.0, min(1.0, dot_product))
            
            # The angle between the vectors (in radians)
            angle = math.acos(dot_product)
            
            # FIXED: Use deviation from 90° as curvature measure
            # Based on your data, 90° turn angle = straight sections
            # Points farther from 90° = more curved sections
            turn_angle = math.pi - angle
            turn_angle_degrees = math.degrees(turn_angle)
            
            # Calculate how far this point deviates from 90° (straight)
            deviation_from_90 = abs(turn_angle_degrees - 90.0)
            
            # Apply threshold - treat small deviations as straight
            min_deviation = 2.0  # 2 degrees minimum deviation to be considered curved
            if deviation_from_90 < min_deviation:
                curvature = 0.0
                print(f"Point {i}: STRAIGHT (deviation too small) - turn angle = {turn_angle_degrees:.2f}°, deviation = {deviation_from_90:.2f}°")
            else:
                # Higher deviation from 90° = higher curvature
                # Normalize by max possible deviation (90°)
                curvature = deviation_from_90 / 90.0
                
                print(f"Point {i}: curvature = {curvature:.4f}, turn angle = {turn_angle_degrees:.2f}°, deviation from 90° = {deviation_from_90:.2f}°")
            
            curvatures.append(curvature)
        
        # Handle edge cases (first and last points)
        if curvatures:
            curvatures.insert(0, curvatures[0])
            curvatures.append(curvatures[-1])
            print(f"Added edge curvatures: first = {curvatures[0]:.4f}, last = {curvatures[-1]:.4f}")
        else:
            curvatures = [0.0] * len(positions)
            print("No curvatures calculated, using zeros")
        
        print(f"Final curvatures summary:")
        print(f"  Zero curvatures (straight): {curvatures.count(0.0)}")
        print(f"  Non-zero curvatures (curved): {len([c for c in curvatures if c > 0])}")
        print(f"  Max curvature: {max(curvatures):.4f}")
        print(f"  First 10 curvatures: {[f'{c:.4f}' for c in curvatures[:10]]}")
        
        # Apply threshold to filter out very small curvatures
        thresholded_curvatures = []
        for curvature in curvatures:
            if curvature < curvature_threshold:
                thresholded_curvatures.append(0.0)
            else:
                thresholded_curvatures.append(curvature)
        
        changes_after_threshold = sum(1 for i in range(len(curvatures)) if curvatures[i] != thresholded_curvatures[i])
        print(f"Threshold ({curvature_threshold}) changed {changes_after_threshold} values")
        
        # Smooth curvatures to avoid jitter
        smoothed_curvatures = []
        window_size = 10
        for i in range(len(thresholded_curvatures)):
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(thresholded_curvatures), i + window_size // 2 + 1)
            avg_curvature = sum(thresholded_curvatures[start_idx:end_idx]) / (end_idx - start_idx)
            smoothed_curvatures.append(avg_curvature)
        
        print(f"Smoothed curvatures: {[f'{c:.4f}' for c in smoothed_curvatures[:10]]}")
        
        # Convert curvatures to speeds (this part was already correct)
        if smoothed_curvatures:
            min_curvature = min(smoothed_curvatures)
            max_curvature = max(smoothed_curvatures)
            
            print(f"Curvature range: {min_curvature:.4f} to {max_curvature:.4f}")
            
            speeds = []
            if max_curvature > min_curvature and max_curvature > 0:
                for curvature in smoothed_curvatures:
                    if curvature == 0.0:
                        speed = 1.0  # Maximum speed for straight sections
                    else:
                        normalized = (curvature - min_curvature) / (max_curvature - min_curvature)
                        speed = 1.0 - normalized  # High curvature = low speed
                    speeds.append(speed)
            else:
                # All curvatures are below threshold or identical - use constant speed
                speeds = [1.0] * len(smoothed_curvatures)
                print("Using constant speed (no significant curvature variation)")
        else:
            speeds = [1.0]
        
        print(f"Speed factors: {[f'{s:.4f}' for s in speeds[:10]]}")
        
        # Calculate cumulative distances based on speeds
        segment_distances = []
        for i in range(len(speeds) - 1):
            avg_speed = (speeds[i] + speeds[i + 1]) / 2.0
            adjusted_speed = min_speed_factor + avg_speed * (max_speed_factor - min_speed_factor)
            segment_distance = adjusted_speed  # Inverse of speed
            segment_distances.append(segment_distance)
        
        print(f"Segment distances: {[f'{d:.4f}' for d in segment_distances[:10]]}")
        
        # Calculate cumulative distances
        cumulative_distances = [0.0]
        for dist in segment_distances:
            cumulative_distances.append(cumulative_distances[-1] + dist)
        
        print(f"Cumulative distances: {[f'{d:.4f}' for d in cumulative_distances[:10]]}")
        
        # Normalize cumulative distances to 0-1 range
        total_distance = cumulative_distances[-1]
        if total_distance > 0:
            normalized_positions = [d / total_distance for d in cumulative_distances]
        else:
            normalized_positions = [i / (len(cumulative_distances) - 1) for i in range(len(cumulative_distances))]
        
        print(f"Normalized positions: {[f'{p:.4f}' for p in normalized_positions[:10]]}")

        # Reset resolution
        curve_obj.data.resolution_u = original_resolution
        curve_obj.data.render_resolution_u = original_render_resolution
        
        # Set keyframes for each frame
        print(f"Setting keyframes from frame {start_frame} to {end_frame}")
        for frame_offset in range(total_frames + 1):
            current_frame = start_frame + frame_offset
            frame_progress = frame_offset / total_frames
            
            # Find the corresponding position along the path
            position = frame_progress  # Default linear
            
            # Interpolate between normalized positions
            for i in range(len(normalized_positions) - 1):
                t1 = i / (len(normalized_positions) - 1)
                t2 = (i + 1) / (len(normalized_positions) - 1)
                
                if t1 <= frame_progress <= t2:
                    # Linear interpolation between positions
                    local_t = (frame_progress - t1) / (t2 - t1) if t2 > t1 else 0
                    position = normalized_positions[i] + local_t * (normalized_positions[i + 1] - normalized_positions[i])
                    break
            
            # Ensure position stays within bounds
            position = max(0.0, min(1.0, position))
            
            # Set keyframe
            follow_path_constraint.offset_factor = position
            follow_path_constraint.keyframe_insert(data_path="offset_factor", frame=current_frame)
            
            if frame_offset % 10 == 0:  # Print every 10th frame to avoid spam
                print(f"Frame {current_frame}: progress = {frame_progress:.3f}, position = {position:.3f}")
        
        print("Speed control applied successfully!")
        return True
        
    except Exception as e:
        print(f"Error in apply_speed_control: {e}")
        import traceback
        traceback.print_exc()
        return False