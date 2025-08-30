"""
Utility operators for animation library management and other general functions
"""

import bpy
from bpy.types import Operator

class ANIMPATH_OT_refresh_animation_library(Operator):
    """Refresh the animation library cache"""
    bl_idname = "animpath.refresh_animation_library"
    bl_label = "Refresh Animation Library"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            from .. import animation_library
            
            animation_library.refresh_animation_library()
            
            # Count available items
            poses = animation_library.get_available_poses(None, context)
            animations = animation_library.get_available_animations(None, context)
            
            pose_count = len([item for item in poses if not item[0].endswith('_MISSING') and item[0] != 'NONE'])
            anim_count = len([item for item in animations if not item[0].endswith('_MISSING') and item[0] != 'NONE'])
            
            self.report({'INFO'}, f"Animation library refreshed: {pose_count} poses, {anim_count} animations")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error refreshing animation library: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class ANIMPATH_OT_clear_animation_cache(Operator):
    """Clear the animation library cache"""
    bl_idname = "animpath.clear_animation_cache"
    bl_label = "Clear Animation Cache"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            from .. import animation_library
            
            animation_library.clear_action_cache()
            self.report({'INFO'}, "Animation cache cleared")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error clearing animation cache: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class ANIMPATH_OT_select_all_paths(Operator):
    """Select all Animation Paths in the scene"""
    bl_idname = "animpath.select_all_paths"
    bl_label = "Select All Animation Paths"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Clear current selection
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select all animation path objects
        selected_count = 0
        for obj in bpy.data.objects:
            if obj.get("is_animation_path"):
                if obj.name in context.view_layer.objects:
                    obj.select_set(True)
                    selected_count += 1
        
        if selected_count > 0:
            self.report({'INFO'}, f"Selected {selected_count} Animation Paths")
        else:
            self.report({'INFO'}, "No Animation Paths found in scene")
        
        return {'FINISHED'}

class ANIMPATH_OT_show_path_info(Operator):
    """Show information about the selected Animation Path"""
    bl_idname = "animpath.show_path_info"
    bl_label = "Show Path Info"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.get("is_animation_path"):
            self.report({'ERROR'}, "No Animation Path selected")
            return {'CANCELLED'}
        
        # Collect path information
        info_lines = []
        info_lines.append(f"Path Name: {obj.name}")
        info_lines.append(f"Start Frame: {obj.get('start_frame', 'Unknown')}")
        info_lines.append(f"End Frame: {obj.get('end_frame', 'Unknown')}")
        info_lines.append(f"Duration: {obj.get('end_frame', 100) - obj.get('start_frame', 1)} frames")
        info_lines.append(f"Start Pose: {obj.get('start_pose', 'Unknown')}")
        info_lines.append(f"Main Animation: {obj.get('anim', 'Unknown')}")
        info_lines.append(f"End Pose: {obj.get('end_pose', 'Unknown')}")
        info_lines.append(f"Start Blend Frames: {obj.get('start_blend_frames', 0)}")
        info_lines.append(f"End Blend Frames: {obj.get('end_blend_frames', 0)}")
        
        target_obj_name = obj.get("target_object")
        if target_obj_name:
            target_obj = bpy.data.objects.get(target_obj_name)
            if target_obj:
                info_lines.append(f"Target Object: {target_obj.name} (Found)")
            else:
                info_lines.append(f"Target Object: {target_obj_name} (Missing)")
        else:
            info_lines.append("Target Object: None")
        
        info_lines.append(f"Use Rotation: {obj.get('use_rotation', True)}")
        
        object_z_offset = obj.get("object_z_offset", 0.0)
        info_lines.append(f"Object Z Offset: {object_z_offset:.3f}")
        
        # Check for control points
        start_point_name = obj.get("start_control_point")
        end_point_name = obj.get("end_control_point")
        
        start_exists = start_point_name and bpy.data.objects.get(start_point_name)
        end_exists = end_point_name and bpy.data.objects.get(end_point_name)
        
        info_lines.append(f"Start Control Point: {'Found' if start_exists else 'Missing'}")
        info_lines.append(f"End Control Point: {'Found' if end_exists else 'Missing'}")
        
        # Print to console and show in operator report
        print("\n=== Animation Path Info ===")
        for line in info_lines:
            print(line)
        print("===========================\n")
        
        self.report({'INFO'}, f"Path info printed to console: {len(info_lines)} properties")
        
        return {'FINISHED'}

class ANIMPATH_OT_validate_animation_library(Operator):
    """Validate animation library files and report any issues"""
    bl_idname = "animpath.validate_animation_library"
    bl_label = "Validate Animation Library"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        try:
            from .. import animation_library
            
            # Get available poses and animations
            poses = animation_library.get_available_poses(None, context)
            animations = animation_library.get_available_animations(None, context)
            
            # Count valid and missing items
            valid_poses = [item for item in poses if not item[0].endswith('_MISSING') and item[0] != 'NONE']
            missing_poses = [item for item in poses if item[0].endswith('_MISSING')]
            
            valid_animations = [item for item in animations if not item[0].endswith('_MISSING') and item[0] != 'NONE']
            missing_animations = [item for item in animations if item[0].endswith('_MISSING')]
            
            # Report results
            info_lines = []
            info_lines.append(f"Valid Poses: {len(valid_poses)}")
            info_lines.append(f"Missing Poses: {len(missing_poses)}")
            info_lines.append(f"Valid Animations: {len(valid_animations)}")
            info_lines.append(f"Missing Animations: {len(missing_animations)}")
            
            if missing_poses:
                info_lines.append("\nMissing Pose Files:")
                for item in missing_poses:
                    info_lines.append(f"  - {item[0].replace('_MISSING', '')}")
            
            if missing_animations:
                info_lines.append("\nMissing Animation Files:")
                for item in missing_animations:
                    info_lines.append(f"  - {item[0].replace('_MISSING', '')}")
            
            # Print to console
            print("\n=== Animation Library Validation ===")
            for line in info_lines:
                print(line)
            print("====================================\n")
            
            if missing_poses or missing_animations:
                self.report({'WARNING'}, f"Validation complete: {len(missing_poses + missing_animations)} missing files (see console)")
            else:
                self.report({'INFO'}, "Animation library validation passed: all files found")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error validating animation library: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

# List of classes to register
classes = [
    ANIMPATH_OT_refresh_animation_library,
    ANIMPATH_OT_clear_animation_cache,
    ANIMPATH_OT_select_all_paths,
    ANIMPATH_OT_show_path_info,
    ANIMPATH_OT_validate_animation_library,
]

def register():
    """Register utility operators"""
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError as e:
            if "already registered" in str(e):
                try:
                    bpy.utils.unregister_class(cls)
                    bpy.utils.register_class(cls)
                except:
                    print(f"Warning: Could not register class {cls.__name__}: {e}")
            else:
                print(f"Error registering class {cls.__name__}: {e}")

def unregister():
    """Unregister utility operators"""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass