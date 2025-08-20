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

def create_speed_matched_nla_strips(target_obj, path_obj, speed_data):
    """
    Create multiple NLA strips with different playback speeds based on speed data.
    
    speed_data is as a list of segments:
    [
        {
            'start_frame': 10,
            'end_frame': 30, 
            'speed_multiplier': 0.5,  # Slow section
            'blend_frames': 5
        },
        {
            'start_frame': 30,
            'end_frame': 60,
            'speed_multiplier': 1.5,  # Fast section  
            'blend_frames': 5
        }
    ]
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
    track_name = f"LAA_{path_name}_SpeedMatched"
    nla_track = None
    
    for track in target_obj.animation_data.nla_tracks:
        if track.name == track_name:
            nla_track = track
            break
    
    if not nla_track:
        nla_track = target_obj.animation_data.nla_tracks.new()
        nla_track.name = track_name
        print(f"Created speed-matched NLA track: {track_name}")
    
    # Clear existing strips
    for strip in list(nla_track.strips):
        nla_track.strips.remove(strip)
    
    strips_created = 0

    try:
        # Create base pose layer if needed
        if start_pose_name != "NONE":
            base_track = _create_base_pose_track(target_obj, path_obj, start_pose_name)
        
        # Get the main animation action
        if anim_name == "NONE":
            print("No animation specified - skipping speed-matched strips")
            return False
            
        main_action = get_animation_action(anim_name)
        if not main_action:
            print(f"Could not load animation: {anim_name}")
            return False
        
        action_length = main_action.frame_range[1] - main_action.frame_range[0]
        print(f"Animation '{anim_name}' length: {action_length} frames")
        
        # Track what pose is actually being displayed for continuity
        last_displayed_action_frame = 0.0
        
        # Create strips for each speed segment
        for i, segment in enumerate(speed_data):
            start_frame = segment['start_frame']
            end_frame = segment['end_frame']
            speed_multiplier = segment['speed_multiplier']
            blend_frames = segment.get('blend_frames', 0)
            
            segment_duration = end_frame - start_frame
            
            if segment_duration <= 0:
                print(f"Warning: Segment {i+1} has invalid duration: {segment_duration}")
                continue
            
            # For the first segment, start from 0
            if i == 0:
                action_start_offset = 0.0
            else:
                # For subsequent segments, start where the previous segment's pose ended
                action_start_offset = last_displayed_action_frame % action_length
            
            # Clean up floating point precision issues
            if abs(action_start_offset) < 0.01:
                action_start_offset = 0.0
            elif abs(action_start_offset - action_length) < 0.01:
                action_start_offset = 0.0
            
            current_timeline_frame = start_frame
            remaining_timeline_frames = segment_duration
            strip_counter = 1
            segment_strips = []
            current_action_offset = action_start_offset
            
            while remaining_timeline_frames > 0:
                # Calculate how much animation we can fit in this strip
                available_animation_time = action_length - current_action_offset
                
                # Calculate how many timeline frames this animation time represents at this speed
                available_timeline_frames = int(round(available_animation_time * speed_multiplier))
                
                # Use the smaller of what's available vs what we need
                timeline_frames_for_this_strip = min(available_timeline_frames, int(remaining_timeline_frames))
                
                # Ensure we have at least 1 frame
                timeline_frames_for_this_strip = max(1, timeline_frames_for_this_strip)
                
                # If we only have a tiny sliver left, break
                if timeline_frames_for_this_strip < 1 or remaining_timeline_frames < 1:
                    break
                
                # Calculate the actual animation time this strip will cover
                animation_time_for_this_strip = timeline_frames_for_this_strip / speed_multiplier
                
                # Create the strip
                if strip_counter == 1:
                    strip_name = f"{path_name}_Seg{i+1}_Spd{speed_multiplier:.2f}"
                else:
                    strip_name = f"{path_name}_Seg{i+1}_{strip_counter}_Spd{speed_multiplier:.2f}"
                
                strip = nla_track.strips.new(strip_name, int(current_timeline_frame), main_action)
                strip.scale = 1.0 / speed_multiplier
                
                # Set action frame range
                strip.action_frame_start = main_action.frame_range[0] + current_action_offset
                strip.action_frame_end = main_action.frame_range[0] + current_action_offset + animation_time_for_this_strip
                
                # Ensure action_frame_end doesn't exceed animation bounds
                if strip.action_frame_end > main_action.frame_range[1]:
                    strip.action_frame_end = main_action.frame_range[1]
                    # Recalculate actual animation time used
                    animation_time_for_this_strip = strip.action_frame_end - strip.action_frame_start
                
                # Set timeline position
                strip.frame_start = int(current_timeline_frame)
                strip.frame_end = int(current_timeline_frame) + timeline_frames_for_this_strip
                
                # Set blend type and extrapolation
                strip.blend_type = 'REPLACE'
                strip.extrapolation = 'HOLD_FORWARD'
                
                # Set up blending
                if i > 0 and strip_counter == 1 and blend_frames > 0:
                    strip.blend_in = blend_frames
                
                if i < len(speed_data) - 1 and remaining_timeline_frames == timeline_frames_for_this_strip and blend_frames > 0:
                    strip.blend_out = blend_frames
                
                segment_strips.append(strip)
                
                print(f"Created strip: {strip_name}")
                print(f"  Timeline: {strip.frame_start:.1f}-{strip.frame_end:.1f} ({timeline_frames_for_this_strip} frames)")
                print(f"  Action: {strip.action_frame_start:.1f}-{strip.action_frame_end:.1f}")
                print(f"  Speed: {speed_multiplier:.2f}x, Scale: {strip.scale:.3f}")
                
                strips_created += 1
                
                # Update for next strip
                current_timeline_frame += timeline_frames_for_this_strip
                remaining_timeline_frames -= timeline_frames_for_this_strip
                
                # Calculate where we actually end up in the animation for the next strip
                if strip.action_frame_end >= main_action.frame_range[1]:
                    # We completed a cycle, start fresh
                    current_action_offset = 0.0
                else:
                    # Continue from where this strip ended
                    current_action_offset = strip.action_frame_end - main_action.frame_range[0]
                    
                strip_counter += 1
            
            # Calculate what pose is actually displayed at the end of this segment
            # This accounts for the scale effect
            if segment_strips:
                last_strip = segment_strips[-1]
                # At the boundary frame, what pose is actually being displayed?
                boundary_timeline_frame = end_frame
                
                # Calculate the displayed action frame at the boundary
                # Formula: displayed_frame = action_start + (timeline_frame - strip_start) / scale
                timeline_offset_in_strip = boundary_timeline_frame - last_strip.frame_start
                displayed_action_offset = timeline_offset_in_strip / last_strip.scale
                last_displayed_action_frame = last_strip.action_frame_start + displayed_action_offset
        
        # Handle end pose if different from start
        if (end_pose_name != "NONE" and end_pose_name != start_pose_name):
            _create_end_pose_overlay(target_obj, path_obj, end_pose_name, speed_data[-1]['end_frame'])
        
        print(f"Successfully created {strips_created} speed-matched NLA strips")
        return True
        
    except Exception as e:
        print(f"Error creating speed-matched NLA strips: {e}")
        import traceback
        traceback.print_exc()
        return False

def _create_base_pose_track(target_obj, path_obj, start_pose_name):
    """Create base pose track for the full duration"""
    path_name = path_obj.name
    base_track_name = f"LAA_{path_name}_BasePose"
    
    # Find or create base track
    base_track = None
    for track in target_obj.animation_data.nla_tracks:
        if track.name == base_track_name:
            base_track = track
            break
    
    if not base_track:
        base_track = target_obj.animation_data.nla_tracks.new()
        base_track.name = base_track_name
    
    # Clear existing strips
    for strip in list(base_track.strips):
        base_track.strips.remove(strip)
    
    # Add start pose
    start_action = get_pose_action(start_pose_name)
    if start_action:
        # Get total duration from path
        start_frame = path_obj.get("start_frame", 1)
        end_frame = path_obj.get("end_frame", 100)
        
        start_strip = base_track.strips.new(f"{path_name}_BasePose", start_frame, start_action)
        start_strip.frame_end = end_frame
        start_strip.blend_type = 'COMBINE'
        start_strip.extrapolation = 'HOLD'
        print(f"Created base pose track: {base_track_name}")
    
    return base_track


def _create_end_pose_overlay(target_obj, path_obj, end_pose_name, final_frame):
    """Create end pose overlay for blending"""
    path_name = path_obj.name
    end_blend_frames = path_obj.get("end_blend_frames", 5)
    
    if end_blend_frames <= 0:
        return
    
    end_action = get_pose_action(end_pose_name)
    if not end_action:
        return
    
    # Create end pose track
    end_track_name = f"LAA_{path_name}_EndPose"
    end_track = target_obj.animation_data.nla_tracks.new()
    end_track.name = end_track_name
    
    # Position end pose to blend in during final frames
    end_start = final_frame - end_blend_frames
    end_strip = end_track.strips.new(f"{path_name}_EndPose", end_start, end_action)
    end_strip.frame_end = final_frame
    end_strip.blend_type = 'ADD'
    end_strip.extrapolation = 'HOLD'
    end_strip.blend_in = end_blend_frames
    
    print(f"Created end pose overlay from frame {end_start} to {final_frame}")


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
    speed_tolerance = 0.01  # How much speed can vary within a segment
    
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
                segment_end = frame
            
            # Create the segment
            segments.append({
                'start_frame': current_segment_start,
                'end_frame': segment_end,
                'speed_multiplier': current_speed,
                'blend_frames': 0
            })
            
            # Start new segment (if not the last frame)
            if i < len(frames) - 1:
                current_segment_start = frame
                current_speed = frame_speed
    
    # Handle rare case where no segments were created
    if not segments:
        segments.append({
            'start_frame': start_frame,
            'end_frame': end_frame,
            'speed_multiplier': current_speed,
            'blend_frames': 0
        })
    
    # Clean up overlapping segments
    for i in range(len(segments) - 1):
        if segments[i]['end_frame'] > segments[i+1]['start_frame']:
            segments[i]['end_frame'] = segments[i+1]['start_frame']
    
    print(f"Created {len(segments)} speed segments from speed data")
    for i, seg in enumerate(segments):
        print(f"  Segment {i+1}: frames {seg['start_frame']}-{seg['end_frame']}, speed {seg['speed_multiplier']:.2f}")
    
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