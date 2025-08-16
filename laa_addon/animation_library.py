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

def create_nla_strips_for_path(target_obj, path_obj):
    """Create NLA strips for animation path using proper NLA blending"""
    if not target_obj or not path_obj:
        print("Error: Missing target object or path object")
        return False
    
    print(f"Creating NLA strips for {target_obj.name} using path {path_obj.name}")
    
    # Get path properties
    start_frame = path_obj.get("start_frame", 1)
    end_frame = path_obj.get("end_frame", 100)
    start_pose_name = path_obj.get("start_pose", "NONE")
    end_pose_name = path_obj.get("end_pose", "NONE")
    anim_name = path_obj.get("anim", "NONE")
    start_blend_frames = path_obj.get("start_blend_frames", 0)
    end_blend_frames = path_obj.get("end_blend_frames", 0)
    
    path_name = path_obj.name
    total_duration = end_frame - start_frame
    
    print(f"Path settings: {start_frame}-{end_frame}, start_pose:{start_pose_name}, anim:{anim_name}, end_pose:{end_pose_name}")
    print(f"Blend frames: start={start_blend_frames}, end={end_blend_frames}")
    
    # Ensure target has animation data
    if not target_obj.animation_data:
        target_obj.animation_data_create()
        print(f"Created animation data for {target_obj.name}")
    
    # Store existing action to restore later (if it contains transform data)
    existing_action = None
    has_transform_keyframes = False
    if target_obj.animation_data.action:
        existing_action = target_obj.animation_data.action
        for fcurve in existing_action.fcurves:
            if fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:
                has_transform_keyframes = True
                break
    
    # Only clear action if it doesn't have transform keyframes
    if not has_transform_keyframes:
        target_obj.animation_data.action = None
    
    # Create or find NLA track
    track_name = f"LAA_{path_name}"
    nla_track = None
    
    # Find existing track
    for track in target_obj.animation_data.nla_tracks:
        if track.name == track_name:
            nla_track = track
            break
    
    # Create new track if not found
    if not nla_track:
        nla_track = target_obj.animation_data.nla_tracks.new()
        nla_track.name = track_name
        print(f"Created NLA track: {track_name}")
    
    # Clear existing strips in this track
    for strip in list(nla_track.strips):
        nla_track.strips.remove(strip)
        print(f"Removed existing strip")
    
    strips_created = 0
    
    try:
        # If there are start/end poses, create base pose layer first
        if start_pose_name != "NONE" or end_pose_name != "NONE":
            # Create a base track for poses
            base_track_name = f"LAA_{path_name}_Poses"
            base_track = None
            
            # Find or create base track
            for track in target_obj.animation_data.nla_tracks:
                if track.name == base_track_name:
                    base_track = track
                    break
            
            if not base_track:
                base_track = target_obj.animation_data.nla_tracks.new()
                base_track.name = base_track_name
                print(f"Created base pose track: {base_track_name}")
            
            # Clear existing strips in base track
            for strip in list(base_track.strips):
                base_track.strips.remove(strip)
            
            # Add start pose (full duration)
            if start_pose_name != "NONE":
                start_action = get_pose_action(start_pose_name)
                if start_action:
                    start_strip = base_track.strips.new(f"{path_name}_StartPose", start_frame, start_action)
                    start_strip.frame_end = end_frame
                    start_strip.blend_type = 'COMBINE'
                    start_strip.extrapolation = 'HOLD' 
                    strips_created += 1
                    print(f"Created start pose base strip from {start_frame} to {end_frame}")
        
        # Create main animation track with blending
        if anim_name != "NONE":
            main_action = get_animation_action(anim_name)
            if main_action:
                strip_name = f"{path_name}_MainAnim"
                main_strip = nla_track.strips.new(strip_name, start_frame, main_action)
                main_strip.frame_end = end_frame
                main_strip.blend_type = 'REPLACE'
                main_strip.extrapolation = 'HOLD'
                
                # Apply blend in/out only if corresponding poses are set
                if start_blend_frames > 0 and start_pose_name != "NONE":
                    main_strip.blend_in = start_blend_frames
                    print(f"Set blend_in: {start_blend_frames} frames")
                else:
                    if start_pose_name == "NONE":
                        print("Start pose is NONE - ignoring start blend")
                
                if end_blend_frames > 0 and end_pose_name != "NONE":
                    main_strip.blend_out = end_blend_frames
                    print(f"Set blend_out: {end_blend_frames} frames")
                else:
                    if end_pose_name == "NONE":
                        print("End pose is NONE - ignoring end blend")
                
                # Set up action repeating if needed
                action_length = main_action.frame_range[1] - main_action.frame_range[0]
                if action_length > 0:
                    animation_duration = end_frame - start_frame
                    if animation_duration > action_length:
                        main_strip.repeat = animation_duration / action_length
                        print(f"Set repeat factor: {main_strip.repeat}")
                
                print(f"Created main animation strip: {strip_name} from {start_frame} to {end_frame}")
                strips_created += 1
            else:
                print(f"Warning: Could not load main animation action: {anim_name}")
        
        # If different from start pose, add end pose as overlay
        if end_pose_name != "NONE" and end_pose_name != start_pose_name and end_blend_frames > 0:
            end_action = get_pose_action(end_pose_name)
            if end_action:
                # Create end pose track
                end_track_name = f"LAA_{path_name}_EndPose"
                end_track = target_obj.animation_data.nla_tracks.new()
                end_track.name = end_track_name
                
                # Position end pose to blend in during the last frames
                end_start = end_frame - end_blend_frames
                end_strip = end_track.strips.new(f"{path_name}_EndPose", end_start, end_action)
                end_strip.frame_end = end_frame
                end_strip.blend_type = 'ADD'  # or 'COMBINE' for additive blending
                end_strip.extrapolation = 'HOLD'
                end_strip.blend_in = end_blend_frames
                
                print(f"Created end pose strip from {end_start} to {end_frame}")
                strips_created += 1
            else:
                print(f"Warning: Could not load end pose action: {end_pose_name}")
        
        # Ensure all tracks are active
        for track in target_obj.animation_data.nla_tracks:
            if track.name.startswith(f"LAA_{path_name}"):
                track.mute = False
                track.is_solo = False
        
        # Update the scene
        bpy.context.view_layer.update()
        
        # Restore the original action if it had transform keyframes
        if has_transform_keyframes and existing_action:
            target_obj.animation_data.action = existing_action
            print("Restored original action with transform keyframes")
        
        if strips_created > 0:
            print(f"Successfully created {strips_created} NLA strips with blending for path {path_name}")
            return True
        else:
            print(f"No NLA strips were created for path {path_name}")
            return False
        
    except Exception as e:
        print(f"Error creating NLA strips: {e}")
        import traceback
        traceback.print_exc()
        return False

def apply_pose_to_armature(armature_obj, pose_name, frame=None):
    """Apply a specific pose to an armature at a given frame"""
    if not armature_obj or armature_obj.type != 'ARMATURE':
        print(f"Error: Object {armature_obj} is not an armature")
        return False
    
    pose_action = get_pose_action(pose_name)
    if not pose_action:
        print(f"Error: Could not load pose {pose_name}")
        return False
    
    # Ensure animation data exists
    if not armature_obj.animation_data:
        armature_obj.animation_data_create()
    
    # Temporarily set the action to apply the pose
    old_action = armature_obj.animation_data.action
    armature_obj.animation_data.action = pose_action
    
    # If frame is specified, set it and update
    if frame is not None:
        bpy.context.scene.frame_set(frame)
    
    # Update the scene to apply the pose
    bpy.context.view_layer.update()
    
    # Insert keyframes for all pose bones
    if frame is not None:
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.anim.keyframe_insert_menu(type='BUILTIN_KSI_LocRot')
        bpy.ops.object.mode_set(mode='OBJECT')
    
    # Restore the old action
    armature_obj.animation_data.action = old_action
    
    print(f"Applied pose {pose_name} to {armature_obj.name}")
    return True

def create_speed_matched_nla_strips(target_obj, path_obj, speed_data):
    """
    Create multiple NLA strips with different playback speeds based on speed data.
    
    speed_data should be a list of segments like:
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
        
        # Create strips for each speed segment
        for i, segment in enumerate(speed_data):
            start_frame = segment['start_frame']
            end_frame = segment['end_frame']
            speed_multiplier = segment['speed_multiplier']
            blend_frames = segment.get('blend_frames', 0)
            
            segment_duration = end_frame - start_frame
            
            # Create strip for this segment
            strip_name = f"{path_name}_Segment_{i+1}_Speed_{speed_multiplier:.2f}"
            strip = nla_track.strips.new(strip_name, start_frame, main_action)
            strip.frame_end = end_frame
            strip.scale = speed_multiplier  # This is the key - set playback speed!
            strip.blend_type = 'REPLACE'
            strip.extrapolation = 'HOLD'
            
            # Set up blending between segments
            if i > 0 and blend_frames > 0:
                strip.blend_in = blend_frames
            
            if i < len(speed_data) - 1 and blend_frames > 0:
                strip.blend_out = blend_frames
            
            # Adjust action repeating based on speed
            if action_length > 0:
                # How much of the action should play during this segment
                effective_duration = segment_duration * speed_multiplier
                strip.repeat = effective_duration / action_length
                
                # Offset the action start to maintain continuity
                if i > 0:
                    # Calculate where the previous segment ended in action time
                    prev_segment = speed_data[i-1]
                    prev_duration = (prev_segment['end_frame'] - prev_segment['start_frame']) * prev_segment['speed_multiplier']
                    action_offset = (prev_duration / action_length) % 1.0
                    strip.action_frame_start = main_action.frame_range[0] + (action_offset * action_length)
            
            print(f"Created speed strip: {strip_name} (frames {start_frame}-{end_frame}, speed {speed_multiplier:.2f}x)")
            strips_created += 1
        
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
    speed_tolerance = 0.1  # How much speed can vary within a segment
    
    for i, frame in enumerate(frames[1:], 1):
        frame_speed = speed_curve_data[frame]
        
        # Check if speed has changed significantly or we've reached minimum segment length
        speed_change = abs(frame_speed - current_speed)
        segment_length = frame - current_segment_start
        
        if (speed_change > speed_tolerance and segment_length >= min_segment_frames) or frame == frames[-1]:
            # End current segment
            segment_end = frame if frame != frames[-1] else end_frame
            
            segments.append({
                'start_frame': current_segment_start,
                'end_frame': segment_end,
                'speed_multiplier': current_speed,
                'blend_frames': 3  # Small blend between segments
            })
            
            # Start new segment
            current_segment_start = frame
            current_speed = frame_speed
    
    # Ensure we don't have overlapping segments
    for i in range(len(segments) - 1):
        if segments[i]['end_frame'] >= segments[i+1]['start_frame']:
            segments[i]['end_frame'] = segments[i+1]['start_frame']
    
    print(f"Created {len(segments)} speed segments from speed data")
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