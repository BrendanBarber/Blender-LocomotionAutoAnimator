import bpy
import os
from pathlib import Path

# Global cache for loaded actions
_action_cache = {}
_poses_cache = []
_animations_cache = []
_cache_initialized = False

def get_animations_folder():
    """Get the path to the animations folder"""
    addon_dir = Path(__file__).parent
    return addon_dir / "animations"

def get_poses_folder():
    """Get the path to the poses folder"""
    return get_animations_folder() / "poses"

def get_animations_subfolder():
    """Get the path to the animations subfolder"""
    return get_animations_folder() / "animations"

def scan_animation_library():
    """Scan the animation library and populate caches"""
    global _poses_cache, _animations_cache, _cache_initialized
    
    _poses_cache = []
    _animations_cache = []
    
    # Start with index 0 for "None" option
    pose_index = 0
    anim_index = 0
    
    # Add "None" options first
    _poses_cache.append(("NONE", "None", "No pose", 'X', pose_index))
    pose_index += 1
    
    _animations_cache.append(("NONE", "None", "No animation", 'X', anim_index))
    anim_index += 1
    
    # Scan poses
    poses_folder = get_poses_folder()
    if poses_folder.exists():
        for blend_file in poses_folder.glob("*.blend"):
            pose_name = blend_file.stem
            _poses_cache.append((pose_name, pose_name, f"Pose: {pose_name}", 'ARMATURE_DATA', pose_index))
            pose_index += 1
    
    # Scan animations
    animations_folder = get_animations_subfolder()
    if animations_folder.exists():
        for blend_file in animations_folder.glob("*.blend"):
            anim_name = blend_file.stem
            _animations_cache.append((anim_name, anim_name, f"Animation: {anim_name}", 'ANIM', anim_index))
            anim_index += 1
    
    _cache_initialized = True
    print(f"Animation library scanned: {len(_poses_cache)-1} poses, {len(_animations_cache)-1} animations")

def get_available_poses(self, context):
    """Get available poses for enum property"""
    global _cache_initialized
    if not _cache_initialized:
        scan_animation_library()
    
    # Check for missing poses and add warnings
    result = []
    index_counter = 0
    
    for item in _poses_cache:
        pose_name = item[0]
        if pose_name != "NONE":
            pose_file = get_poses_folder() / f"{pose_name}.blend"
            if not pose_file.exists():
                # Add MISSING entry with unique index
                missing_item = (f"{pose_name}_MISSING", f"{pose_name} (MISSING)", f"Missing pose file: {pose_name}.blend", 'ERROR', index_counter)
                result.append(missing_item)
                print(f"Warning: Missing pose file: {pose_file}")
            else:
                # Add existing pose with corrected index
                corrected_item = (item[0], item[1], item[2], item[3], index_counter)
                result.append(corrected_item)
        else:
            # Add NONE option with corrected index
            corrected_item = (item[0], item[1], item[2], item[3], index_counter)
            result.append(corrected_item)
        
        index_counter += 1
    
    return result

def get_available_animations(self, context):
    """Get available animations for enum property"""
    global _cache_initialized
    if not _cache_initialized:
        scan_animation_library()
    
    # Check for missing animations and add warnings
    result = []
    index_counter = 0
    
    for item in _animations_cache:
        anim_name = item[0]
        if anim_name != "NONE":
            anim_file = get_animations_subfolder() / f"{anim_name}.blend"
            if not anim_file.exists():
                # Add MISSING entry with unique index
                missing_item = (f"{anim_name}_MISSING", f"{anim_name} (MISSING)", f"Missing animation file: {anim_name}.blend", 'ERROR', index_counter)
                result.append(missing_item)
                print(f"Warning: Missing animation file: {anim_file}")
            else:
                # Add existing animation with corrected index
                corrected_item = (item[0], item[1], item[2], item[3], index_counter)
                result.append(corrected_item)
        else:
            # Add NONE option with corrected index
            corrected_item = (item[0], item[1], item[2], item[3], index_counter)
            result.append(corrected_item)
        
        index_counter += 1
    
    return result

def load_action_from_file(filename, is_pose=True):
    """Load an action from a blend file and cache it"""
    global _action_cache
    
    # Check cache first
    cache_key = f"{'pose' if is_pose else 'anim'}_{filename}"
    if cache_key in _action_cache:
        return _action_cache[cache_key]
    
    # Determine file path
    if is_pose:
        file_path = get_poses_folder() / f"{filename}.blend"
    else:
        file_path = get_animations_subfolder() / f"{filename}.blend"
    
    if not file_path.exists():
        print(f"Error: Animation file not found: {file_path}")
        return None
    
    # Load the action from the blend file
    try:
        # Store current actions to detect new ones
        existing_actions = set(bpy.data.actions.keys())
        
        # Append from the blend file
        with bpy.data.libraries.load(str(file_path)) as (data_from, data_to):
            # Look for action with same name as file
            if filename in data_from.actions:
                data_to.actions = [filename]
            elif len(data_from.actions) == 1:
                # If only one action, use it regardless of name
                data_to.actions = data_from.actions
            else:
                print(f"Warning: Could not find action '{filename}' in {file_path}")
                return None
        
        # Find the newly loaded action
        new_actions = set(bpy.data.actions.keys()) - existing_actions
        if new_actions:
            action_name = list(new_actions)[0]
            loaded_action = bpy.data.actions[action_name]
            
            # Cache the action
            _action_cache[cache_key] = loaded_action
            print(f"Loaded and cached action: {filename} -> {action_name}")
            return loaded_action
        else:
            print(f"Error: No new action found after loading {file_path}")
            return None
            
    except Exception as e:
        print(f"Error loading action from {file_path}: {e}")
        return None

def get_pose_action(pose_name):
    """Get a pose action by name"""
    if pose_name == "NONE" or pose_name.endswith("_MISSING"):
        return None
    return load_action_from_file(pose_name, is_pose=True)

def get_animation_action(anim_name):
    """Get an animation action by name"""
    if anim_name == "NONE" or anim_name.endswith("_MISSING"):
        return None
    return load_action_from_file(anim_name, is_pose=False)

def clear_action_cache():
    """Clear the action cache"""
    global _action_cache, _cache_initialized
    _action_cache.clear()
    _cache_initialized = False
    print("Animation library cache cleared")

def refresh_animation_library():
    """Refresh the animation library (rescan and clear cache)"""
    clear_action_cache()
    scan_animation_library()

def create_discrete_speed_nla_strips(target_obj, path_obj, speed_data):
    """
    Create NLA strips with discrete speed changes that occur only at animation loop boundaries.
    Uses speed segments as guides for where changes should roughly occur.
    """
    if not target_obj or not path_obj:
        print("Error: Missing target object or path object")
        return False
    
    # Get path properties
    start_pose_name = path_obj.get("start_pose", "NONE")
    end_pose_name = path_obj.get("end_pose", "NONE") 
    anim_name = path_obj.get("anim", "NONE")
    path_name = path_obj.name
    
    # Ensure target has animation data
    if not target_obj.animation_data:
        target_obj.animation_data_create()
    
    # Create or find main NLA track
    track_name = f"LAA_{path_name}_DiscreteSpeed"
    nla_track = None
    
    for track in target_obj.animation_data.nla_tracks:
        if track.name == track_name:
            nla_track = track
            break
    
    if not nla_track:
        nla_track = target_obj.animation_data.nla_tracks.new()
        nla_track.name = track_name
        print(f"Created discrete speed NLA track: {track_name}")
    
    # Clear existing strips
    for strip in list(nla_track.strips):
        nla_track.strips.remove(strip)
    
    try:
        # Create base pose layer if needed
        if start_pose_name != "NONE":
            base_track = _create_base_pose_track(target_obj, path_obj, start_pose_name)
        
        # Get the main animation action
        if anim_name == "NONE":
            print("No animation specified - skipping discrete speed strips")
            return False
            
        main_action = get_animation_action(anim_name)
        if not main_action:
            print(f"Could not load animation: {anim_name}")
            return False
        
        # Get action properties
        action_start = main_action.frame_range[0]
        action_end = main_action.frame_range[1]
        action_length = action_end - action_start
        
        print(f"Animation '{anim_name}': {action_start}-{action_end} ({action_length} frames)")
        
        # Get blend frame settings from path object
        start_blend_frames = path_obj.get("start_blend_frames", 5)
        end_blend_frames = path_obj.get("end_blend_frames", 5)
        
        # Convert speed segments into discrete speed changes
        speed_changes = _calculate_discrete_speed_changes(speed_data, action_length)
        
        if not speed_changes:
            print("No valid speed changes calculated")
            return False
        
        # Create strips for each speed section
        strips_created = 0
        
        # Get blend frame settings from the first segment or use defaults
        start_blend_frames = speed_data[0].get('start_blend_frames', 5) if speed_data else 5
        end_blend_frames = speed_data[0].get('end_blend_frames', 5) if speed_data else 5
        
        for i, change in enumerate(speed_changes):
            timeline_start = change['timeline_start']
            timeline_end = change['timeline_end'] 
            speed = change['speed']
            loop_cycles = change['loop_cycles']
            
            # Create strip name
            strip_name = f"{path_name}_Speed{speed:.2f}_{i+1}"
            
            # Create the NLA strip
            strip = nla_track.strips.new(strip_name, int(timeline_start), main_action)
            
            # Set playback scale (higher = slower, lower = faster)
            strip.scale = 1.0 / speed
            
            # Set action frame range - always use the full loop
            strip.action_frame_start = action_start
            strip.action_frame_end = action_end
            
            # Set strip timeline range
            strip.frame_start = int(timeline_start)
            strip.frame_end = int(timeline_end)
            
            # Set blend properties
            strip.blend_type = 'REPLACE'
            strip.extrapolation = 'HOLD_FORWARD'
            
            # Apply blend frames only to first and last strips
            if i == 0:
                # First strip gets start blend
                strip.blend_in = start_blend_frames
            elif i == len(speed_changes) - 1:
                # Last strip gets end blend
                strip.blend_out = end_blend_frames
            
            print(f"Created strip: {strip_name}")
            print(f"  Timeline: {strip.frame_start}-{strip.frame_end} ({strip.frame_end - strip.frame_start + 1} frames)")
            print(f"  Speed: {speed:.2f}x (1 complete loop)")
            print(f"  Scale: {strip.scale:.3f}")
            if i == 0 and start_blend_frames > 0:
                print(f"  Start blend: {start_blend_frames} frames")
            if i == len(speed_changes) - 1 and end_blend_frames > 0:
                print(f"  End blend: {end_blend_frames} frames")
            
            strips_created += 1
        
        # Handle end pose if different from start
        if (end_pose_name != "NONE" and end_pose_name != start_pose_name):
            final_frame = speed_changes[-1]['timeline_end']
            _create_end_pose_overlay(target_obj, path_obj, end_pose_name, final_frame)
        
        print(f"Successfully created {strips_created} discrete speed NLA strips")
        return True
        
    except Exception as e:
        print(f"Error creating discrete speed NLA strips: {e}")
        import traceback
        traceback.print_exc()
        return False

def _calculate_discrete_speed_changes(speed_data, action_length):
    """
    Convert speed segments into discrete speed changes where each strip plays exactly one complete loop.
    Strip duration = action_length / speed (never shorter than action_length).
    """
    if not speed_data:
        return []
    
    # Get total timeline range
    first_segment = speed_data[0]
    last_segment = speed_data[-1]
    timeline_start = first_segment['start_frame']
    timeline_end = last_segment['end_frame']
    
    print(f"Total timeline: {timeline_start}-{timeline_end}")
    print(f"Animation loop length: {action_length} frames")
    
    # Create one strip per significant speed change, each containing exactly one loop
    speed_changes = []
    current_timeline_pos = timeline_start
    last_speed = None
    
    # Process each segment to find speed changes
    for segment in speed_data:
        speed = segment['speed_multiplier']
        
        # Only create a new strip if speed has changed significantly
        if last_speed is None or abs(speed - last_speed) > 0.02:  # 2% threshold
            
            # Check if we have room for this strip
            remaining_timeline = timeline_end - current_timeline_pos + 1
            if remaining_timeline <= 0:
                break
            
            # Calculate strip duration for exactly one complete loop at this speed
            strip_duration = action_length / speed
            
            # If this strip would extend past timeline end, make it the final strip
            if current_timeline_pos + strip_duration > timeline_end + 1:
                strip_duration = timeline_end - current_timeline_pos + 1
                
            change = {
                'timeline_start': current_timeline_pos,
                'timeline_end': current_timeline_pos + strip_duration - 1,
                'speed': speed,
                'strip_duration': strip_duration,
                'loop_cycles': strip_duration / (action_length / speed)  # Should be 1.0 unless truncated
            }
            
            speed_changes.append(change)
            
            print(f"Strip {len(speed_changes)} at speed {speed:.2f}x:")
            print(f"  Timeline: {current_timeline_pos:.1f}-{change['timeline_end']:.1f} ({strip_duration:.1f} frames)")
            print(f"  One complete loop duration: {action_length / speed:.1f} frames")
            if strip_duration < action_length / speed:
                print(f"  (Truncated at timeline end)")
            
            current_timeline_pos += strip_duration
            last_speed = speed
    
    # If we haven't reached the timeline end, extend the last strip
    if speed_changes and speed_changes[-1]['timeline_end'] < timeline_end:
        adjustment = timeline_end - speed_changes[-1]['timeline_end']
        speed_changes[-1]['timeline_end'] = timeline_end
        speed_changes[-1]['strip_duration'] += adjustment
        speed_changes[-1]['loop_cycles'] = speed_changes[-1]['strip_duration'] / (action_length / speed_changes[-1]['speed'])
        print(f"Extended final strip by {adjustment:.1f} frames to reach timeline end")
    
    print(f"Created {len(speed_changes)} strips, each containing one complete loop")
    
    return speed_changes

def _create_base_pose_track(target_obj, path_obj, pose_name):
    """Create a base pose track for the start pose."""
    track_name = f"LAA_{path_obj.name}_BasePose"
    
    # Find or create base pose track
    base_track = None
    for track in target_obj.animation_data.nla_tracks:
        if track.name == track_name:
            base_track = track
            break
    
    if not base_track:
        base_track = target_obj.animation_data.nla_tracks.new()
        base_track.name = track_name
    
    # Clear existing strips
    for strip in list(base_track.strips):
        base_track.strips.remove(strip)
    
    # Create base pose strip
    pose_action = get_pose_action(pose_name)
    if pose_action:
        # Get total duration from path
        start_frame = path_obj.get("start_frame", 1)
        end_frame = path_obj.get("end_frame", 100)
        start_blend_frames = path_obj.get("start_blend_frames", 5)
        
        strip = base_track.strips.new(f"BasePose_{pose_name}", start_frame, pose_action)
        strip.frame_end = end_frame
        strip.blend_type = 'COMBINE'  # Base layer
        strip.influence = 1.0
        strip.extrapolation = 'HOLD'
        
        # Apply start blend to base pose
        if start_blend_frames > 0:
            strip.blend_in = start_blend_frames
        
        print(f"Created base pose strip: {pose_name}")
    
    return base_track

def _create_end_pose_overlay(target_obj, path_obj, pose_name, start_frame):
    """Create an end pose overlay track."""
    track_name = f"LAA_{path_obj.name}_EndPose"
    
    # Find or create end pose track
    end_track = None
    for track in target_obj.animation_data.nla_tracks:
        if track.name == track_name:
            end_track = track
            break
    
    if not end_track:
        end_track = target_obj.animation_data.nla_tracks.new()
        end_track.name = track_name
    
    # Clear existing strips
    for strip in list(end_track.strips):
        end_track.strips.remove(strip)
    
    # Create end pose strip
    pose_action = get_pose_action(pose_name)
    if pose_action:
        end_blend_frames = path_obj.get("end_blend_frames", 10)
        
        # Position end pose to start blending before the animation ends
        blend_start = int(start_frame) - end_blend_frames
        
        strip = end_track.strips.new(f"EndPose_{pose_name}", blend_start, pose_action)
        strip.frame_end = int(start_frame)
        strip.blend_type = 'ADD'  # Overlay
        strip.influence = 1.0
        strip.extrapolation = 'HOLD'
        
        # Apply end blend
        if end_blend_frames > 0:
            strip.blend_in = end_blend_frames
        
        print(f"Created end pose overlay: {pose_name} at frame {start_frame} with {end_blend_frames} frame blend")
    
    return end_track

# Legacy function kept for compatibility but now calls discrete version
def create_speed_matched_nla_strips(target_obj, path_obj, speed_data):
    """
    Legacy wrapper - now uses discrete speed system for better results.
    """
    print("Using discrete speed system for improved animation continuity...")
    return create_discrete_speed_nla_strips(target_obj, path_obj, speed_data)

def convert_speed_data_to_segments(speed_curve_data, start_frame, end_frame, min_segment_frames=10):
    """
    Convert your relative speed data into segments for NLA strips.
    
    speed_curve_data: dict with frame->speed mappings from your speed control system
    min_segment_frames: minimum frames per segment to avoid too many tiny strips
    """
    if not speed_curve_data:
        return []
    
    segments = []
    frames = sorted(speed_curve_data.keys())
    
    if not frames:
        return []
    
    current_segment_start = start_frame
    current_speed = speed_curve_data[frames[0]]
    speed_tolerance = 0.03  # How much speed can vary within a segment
    
    for i, frame in enumerate(frames):
        if i == 0:
            continue  # Skip first frame as we already set current_speed
            
        frame_speed = speed_curve_data[frame]
        speed_change = abs(frame_speed - current_speed)
        segment_length = frame - current_segment_start
        
        # Check if we should end the current segment
        should_end_segment = (
            (speed_change > speed_tolerance and segment_length >= min_segment_frames) or
            i == len(frames) - 1  # This is actually the last frame
        )
        
        if should_end_segment:
            # Determine segment end frame
            if i == len(frames) - 1:  # Last frame
                segment_end = end_frame
            else:
                # End the segment one frame BEFORE the next segment starts
                segment_end = frame - 1
            
            # Only create segment if it has valid duration
            if segment_end >= current_segment_start:
                segments.append({
                    'start_frame': current_segment_start,
                    'end_frame': segment_end,
                    'speed_multiplier': current_speed,
                    'blend_frames': 5  # Default blend frames for discrete system
                })
            
            # Start new segment (if not the last frame)
            if i < len(frames) - 1:
                current_segment_start = frame  # Next segment starts exactly at this frame
                current_speed = frame_speed
    
    # Handle rare case where no segments were created
    if not segments:
        segments.append({
            'start_frame': start_frame,
            'end_frame': end_frame,
            'speed_multiplier': current_speed,
            'blend_frames': 5
        })
    
    # Ensure no gaps or overlaps - make segments perfectly adjacent
    for i in range(len(segments) - 1):
        # Next segment should start exactly where current segment ends + 1
        segments[i+1]['start_frame'] = segments[i]['end_frame'] + 1
    
    # Ensure the last segment ends at the specified end_frame
    if segments:
        segments[-1]['end_frame'] = end_frame
    
    print(f"Created {len(segments)} speed segments from speed data")
    for i, seg in enumerate(segments):
        duration = seg['end_frame'] - seg['start_frame'] + 1
        print(f"  Segment {i+1}: frames {seg['start_frame']}-{seg['end_frame']} ({duration} frames), speed {seg['speed_multiplier']:.2f}")
    
    return segments

# Initialize the library on import
def initialize_library():
    """Initialize the animation library"""
    try:
        scan_animation_library()
    except Exception as e:
        print(f"Error initializing animation library: {e}")

# Auto-initialize when module is imported
initialize_library()