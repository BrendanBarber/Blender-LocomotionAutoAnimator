"""
Path-related operators for Animation Path creation, editing, and management
"""

import bpy
from mathutils import Vector
from bpy.types import Operator

class ANIMPATH_OT_set_start_position(Operator):
    """Set start position from 3D cursor"""
    bl_idname = "animpath.set_start_position"
    bl_label = "Set Start Position"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.animation_path_props
        props.start_pos = context.scene.cursor.location.copy()
        self.report({'INFO'}, f"Start position set to {props.start_pos}")
        return {'FINISHED'}

class ANIMPATH_OT_set_end_position(Operator):
    """Set end position from 3D cursor"""
    bl_idname = "animpath.set_end_position"
    bl_label = "Set End Position"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.animation_path_props
        props.end_pos = context.scene.cursor.location.copy()
        self.report({'INFO'}, f"End position set to {props.end_pos}")
        return {'FINISHED'}

class ANIMPATH_OT_set_target_object(Operator):
    """Set target object from active selection"""
    bl_idname = "animpath.set_target_object"
    bl_label = "Set Target Object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if context.active_object:
            props = context.scene.animation_path_props
            props.target_object = context.active_object
            self.report({'INFO'}, f"Target object set to: {context.active_object.name}")
        else:
            self.report({'WARNING'}, "No active object selected")
        return {'FINISHED'}

class ANIMPATH_OT_create_path(Operator):
    """Create a new Animation Path"""
    bl_idname = "animpath.create_path"
    bl_label = "Create Animation Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            # Import here to avoid circular imports
            from ..animation_path import create_animation_path_from_properties
            
            path = create_animation_path_from_properties(context)
            curve_obj = path.create_blender_curve("AnimationPath")
            control_points = path.create_control_points(curve_obj)
            
            props = context.scene.animation_path_props
            if props.target_object:
                curve_obj["target_object"] = props.target_object.name
                curve_obj["use_rotation"] = props.use_rotation
                curve_obj["object_z_offset"] = props.object_z_offset
            
            bpy.ops.object.select_all(action='DESELECT')
            curve_obj.select_set(True)
            context.view_layer.objects.active = curve_obj
            
            self.report({'INFO'}, f"Created Animation Path: {curve_obj.name} (Frames: {path.start_frame}-{path.end_frame})")
            
        except ValueError as e:
            self.report({'ERROR'}, f"Error creating path: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class ANIMPATH_OT_update_path(Operator):
    """Update selected Animation Path"""
    bl_idname = "animpath.update_path"
    bl_label = "Update Animation Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.get("is_animation_path"):
            self.report({'ERROR'}, "No Animation Path selected")
            return {'CANCELLED'}
        
        try:
            # Import here to avoid circular imports
            from ..animation_path import AnimationPath
            
            props = context.scene.animation_path_props
            path = AnimationPath(
                start_pos=props.start_pos,
                start_frame=props.start_frame,
                end_pos=props.end_pos,
                end_frame=props.end_frame,
                start_pose=props.start_pose,
                end_pose=props.end_pose,
                anim=props.anim,
                start_blend_frames=props.start_blend_frames,
                end_blend_frames=props.end_blend_frames,
                anim_speed_mult=props.anim_speed_mult
            )
            
            obj["start_frame"] = path.start_frame
            obj["end_frame"] = path.end_frame
            obj["start_pose"] = path.start_pose
            obj["end_pose"] = path.end_pose
            obj["anim"] = path.anim
            obj["start_blend_frames"] = path.start_blend_frames
            obj["end_blend_frames"] = path.end_blend_frames
            obj["anim_speed_mult"] = path.anim_speed_mult
            obj["object_z_offset"] = props.object_z_offset
            
            # Update curve data's path_duration
            if obj.data and hasattr(obj.data, 'path_duration'):
                obj.data.path_duration = path.duration
                print(f"Updated path_duration to {path.duration} frames")
            
            if props.target_object:
                obj["target_object"] = props.target_object.name
            obj["use_rotation"] = props.use_rotation
            
            # Update control point positions only
            for point_type in ["start", "end"]:
                point_name = obj.get(f"{point_type}_control_point")
                if point_name:
                    point_obj = bpy.data.objects.get(point_name)
                    if point_obj:
                        new_pos = getattr(props, f"{point_type}_pos")
                        point_obj.location = new_pos
            
            self.report({'INFO'}, f"Updated Animation Path: {obj.name} (Frames: {path.start_frame}-{path.end_frame})")
            
        except ValueError as e:
            self.report({'ERROR'}, f"Error updating path: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

class ANIMPATH_OT_delete_path(Operator):
    """Delete selected Animation Path and its control points, keyframes, and NLA strips"""
    bl_idname = "animpath.delete_path"
    bl_label = "Delete Animation Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.get("is_animation_path"):
            self.report({'ERROR'}, "No Animation Path selected")
            return {'CANCELLED'}
        
        path_name = obj.name
        objects_to_delete = []
        curve_data_to_delete = []
        
        # Clean up animation data before deleting path objects
        cleanup_success = self._cleanup_animation_data(obj, context)
        if cleanup_success:
            self.report({'INFO'}, f"Cleaned up animation data for path: {path_name}")
        
        # Store the curve data for deletion
        if obj.data and obj.data.users == 1:  # Only delete if no other objects use this data
            curve_data_to_delete.append(obj.data)
        
        # Find parent empty and all related objects
        parent_empty_name = obj.get("laa_path_parent")
        parent_empty = bpy.data.objects.get(parent_empty_name) if parent_empty_name else None
        
        if parent_empty:
            # Collect all children of the parent empty (includes path and control points)
            for child in parent_empty.children:
                objects_to_delete.append(child)
                # Store curve data for deletion if it's a curve object
                if child.data and hasattr(child.data, 'splines') and child.data.users == 1:
                    curve_data_to_delete.append(child.data)
            
            # Add the parent empty itself
            objects_to_delete.append(parent_empty)
        else:
            # Fallback: manually find and collect control points
            start_point_name = obj.get("start_control_point")
            end_point_name = obj.get("end_control_point")
            
            for point_name in [start_point_name, end_point_name]:
                if point_name:
                    point_obj = bpy.data.objects.get(point_name)
                    if point_obj:
                        objects_to_delete.append(point_obj)
            
            # Add the path object itself
            objects_to_delete.append(obj)
        
        # Also look for and delete any offset empties created for this path
        for scene_obj in bpy.data.objects:
            if scene_obj.get("is_laa_offset_empty") and scene_obj.get("animation_path_parent") == path_name:
                objects_to_delete.append(scene_obj)
        
        # Clear selection to avoid issues
        bpy.ops.object.select_all(action='DESELECT')
        
        # Delete all objects
        deleted_count = 0
        for delete_obj in objects_to_delete:
            if delete_obj and delete_obj.name in bpy.data.objects:
                try:
                    bpy.data.objects.remove(delete_obj, do_unlink=True)
                    deleted_count += 1
                except Exception as e:
                    print(f"Warning: Could not delete object {delete_obj.name}: {e}")
        
        # Clear the selected path reference if it was this path
        selected_path_name = context.scene.get("_selected_animation_path")
        if selected_path_name == path_name:
            if "_selected_animation_path" in context.scene:
                del context.scene["_selected_animation_path"]
        
        # Update the viewport
        context.view_layer.update()
        
        self.report({'INFO'}, f"Deleted Animation Path '{path_name}': {deleted_count} objects and associated animation data")
        return {'FINISHED'}
    
    def _cleanup_animation_data(self, path_obj, context):
        """Clean up animation data (keyframes and NLA strips) created by this path"""
        try:
            path_name = path_obj.name
            target_obj_name = path_obj.get("target_object")
            
            if not target_obj_name:
                print(f"No target object found for path {path_name}")
                return False
            
            target_obj = bpy.data.objects.get(target_obj_name)
            if not target_obj:
                print(f"Target object '{target_obj_name}' not found")
                return False
            
            cleanup_performed = False
            
            # Clean up target object animation data
            cleanup_performed |= self._cleanup_object_animation(target_obj, path_name, path_obj)
            
            # Find and clean up armature animation data
            armature_obj = self._find_armature(target_obj)
            if armature_obj and armature_obj != target_obj:
                cleanup_performed |= self._cleanup_armature_animation(armature_obj, path_name)
            elif armature_obj == target_obj:
                # If target is the armature, clean up NLA strips but preserve any follow path keyframes
                cleanup_performed |= self._cleanup_armature_animation(armature_obj, path_name)
            
            return cleanup_performed
            
        except Exception as e:
            print(f"Error cleaning up animation data: {e}")
            return False
    
    def _cleanup_object_animation(self, target_obj, path_name, path_obj):
        """Clean up Follow Path constraints and related keyframes"""
        cleanup_performed = False

        try:
            # Get frame range from path object
            start_frame = path_obj.get("start_frame", 1)
            end_frame = path_obj.get("end_frame", 100)
            
            # First, clean up keyframes before removing constraints
            if target_obj.animation_data and target_obj.animation_data.action:
                action = target_obj.animation_data.action
                fcurves_to_remove = []
                
                # Find fcurves related to Follow Path constraint
                for fcurve in action.fcurves:
                    try:
                        # Remove constraint-related keyframes
                        if (fcurve.data_path.startswith('constraints[') and 
                            ('offset_factor' in fcurve.data_path or 'influence' in fcurve.data_path)):
                            # Check if this fcurve belongs to our constraint
                            if f'FollowPath_{path_name}' in fcurve.data_path:
                                fcurves_to_remove.append(fcurve)
                        
                        # Remove location/rotation keyframes within the path's frame range
                        elif fcurve.data_path in ['location', 'rotation_euler', 'rotation_quaternion']:
                            # Check if keyframes exist in the path's frame range
                            keyframes_in_range = [kf for kf in fcurve.keyframe_points 
                                                if start_frame <= kf.co[0] <= end_frame + 1]
                            
                            if keyframes_in_range and len(keyframes_in_range) == len(fcurve.keyframe_points):
                                # If ALL keyframes are in the path range, it's likely a path animation
                                fcurves_to_remove.append(fcurve)
                            elif keyframes_in_range:
                                # Remove only keyframes in the path range
                                for kf in reversed(keyframes_in_range):
                                    fcurve.keyframe_points.remove(kf, fast=True)
                                cleanup_performed = True
                    
                    except (AttributeError, ReferenceError):
                        # FCurve or its data may have been invalidated
                        continue
                
                # Remove the identified fcurves
                for fcurve in fcurves_to_remove:
                    try:
                        action.fcurves.remove(fcurve)
                        cleanup_performed = True
                        print(f"Removed fcurve: {fcurve.data_path}")
                    except (AttributeError, ReferenceError):
                        # FCurve may have been invalidated
                        continue
            
            # Now remove Follow Path constraints created by this path
            constraints_to_remove = []
            if hasattr(target_obj, 'constraints'):
                for constraint in target_obj.constraints:
                    try:
                        if (constraint.type == 'FOLLOW_PATH' and 
                            constraint.name == f"FollowPath_{path_name}"):
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
            print(f"Error during object animation cleanup: {e}")
        
        return cleanup_performed
    
    def _cleanup_armature_animation(self, armature_obj, path_name):
        """Clean up NLA strips and tracks created by this path"""
        cleanup_performed = False
        
        try:
            if not armature_obj.animation_data:
                return False
            
            # Remove NLA tracks created by this path
            tracks_to_remove = []
            for track in armature_obj.animation_data.nla_tracks:
                try:
                    if track.name.startswith(f"LAA_{path_name}_"):
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
    
    def _find_armature(self, target_obj):
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

class ANIMPATH_OT_load_path_to_properties(Operator):
    """Load selected Animation Path data to properties panel"""
    bl_idname = "animpath.load_path_to_properties"
    bl_label = "Load Path to Properties"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.get("is_animation_path"):
            self.report({'ERROR'}, "No Animation Path selected")
            return {'CANCELLED'}
        
        props = context.scene.animation_path_props
        
        props.start_frame = obj.get("start_frame", 1)
        props.end_frame = obj.get("end_frame", 100)
        props.start_pose = obj.get("start_pose", "idle")
        props.end_pose = obj.get("end_pose", "idle")
        props.anim = obj.get("anim", "walk")
        props.start_blend_frames = obj.get("start_blend_frames", 0)
        props.end_blend_frames = obj.get("end_blend_frames", 0)
        props.anim_speed_mult = obj.get("anim_speed_mult", 1.0)
        props.use_rotation = obj.get("use_rotation", True)
        props.object_z_offset = obj.get("object_z_offset", 0.0)
        
        target_obj_name = obj.get("target_object")
        if target_obj_name:
            target_obj = bpy.data.objects.get(target_obj_name)
            if target_obj:
                props.target_object = target_obj
        
        # Load positions from control points
        for point_type in ["start", "end"]:
            point_name = obj.get(f"{point_type}_control_point")
            if point_name:
                point_obj = bpy.data.objects.get(point_name)
                if point_obj:
                    setattr(props, f"{point_type}_pos", point_obj.location)
        
        # Set scene frame range to match loaded animation path
        context.scene.frame_start = props.start_frame
        context.scene.frame_end = props.end_frame
        
        self.report({'INFO'}, f"Loaded path data to properties: {obj.name} (Frames: {props.start_frame}-{props.end_frame})")
        return {'FINISHED'}

class ANIMPATH_OT_reset_curve_to_control_points(Operator):
    """Reset curve shape to match control point positions"""
    bl_idname = "animpath.reset_curve_to_control_points"
    bl_label = "Reset Curve to Control Points"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        obj = context.active_object
        
        if not obj or not obj.get("is_animation_path"):
            self.report({'ERROR'}, "No Animation Path selected")
            return {'CANCELLED'}
        
        control_points = {}
        
        for point_type in ["start", "end"]:
            point_name = obj.get(f"{point_type}_control_point")
            if point_name:
                point_obj = bpy.data.objects.get(point_name)
                if point_obj:
                    control_points[point_type] = point_obj.location.copy()
        
        if len(control_points) < 2:
            self.report({'ERROR'}, "Need start and end control points to reset curve")
            return {'CANCELLED'}
        
        curve_data = obj.data
        spline = curve_data.splines[0]
        
        start_pos = control_points.get("start")
        end_pos = control_points.get("end")
        direction = end_pos - start_pos
        
        for i in range(5):
            t = i / 4.0
            if i == 0:
                pos = start_pos
            elif i == 4:
                pos = end_pos
            else:
                pos = start_pos + direction * t
            spline.points[i].co = (pos.x, pos.y, pos.z, 1.0)
        
        self.report({'INFO'}, "Reset curve to control points")
        return {'FINISHED'}

# List of classes to register
classes = [
    ANIMPATH_OT_set_start_position,
    ANIMPATH_OT_set_end_position,
    ANIMPATH_OT_set_target_object,
    ANIMPATH_OT_create_path,
    ANIMPATH_OT_update_path,
    ANIMPATH_OT_delete_path,
    ANIMPATH_OT_load_path_to_properties,
    ANIMPATH_OT_reset_curve_to_control_points,
]

def register():
    """Register path operators"""
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
    """Unregister path operators"""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass