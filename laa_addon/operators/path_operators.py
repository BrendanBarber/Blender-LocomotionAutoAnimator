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
            try:
                from ..animation_path import create_animation_path_from_properties
            except ImportError:
                from animation_path import create_animation_path_from_properties
            
            path = create_animation_path_from_properties(context)
            curve_obj = path.create_blender_curve("AnimationPath")
            control_points = path.create_control_points(curve_obj)
            
            props = context.scene.animation_path_props
            if props.target_object:
                curve_obj["target_object"] = props.target_object.name
                curve_obj["use_rotation"] = props.use_rotation
                curve_obj["object_offset"] = tuple(props.object_offset)
            
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
            try:
                from ..animation_path import AnimationPath
            except ImportError:
                from animation_path import AnimationPath
            
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
                end_blend_frames=props.end_blend_frames
            )
            
            obj["start_frame"] = path.start_frame
            obj["end_frame"] = path.end_frame
            obj["start_pose"] = path.start_pose
            obj["end_pose"] = path.end_pose
            obj["anim"] = path.anim
            obj["start_blend_frames"] = path.start_blend_frames
            obj["end_blend_frames"] = path.end_blend_frames
            obj["object_offset"] = tuple(props.object_offset)
            
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
    """Delete selected Animation Path and its control points"""
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
        
        self.report({'INFO'}, f"Deleted Animation Path '{path_name}': {deleted_count} objects")
        return {'FINISHED'}

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
        props.use_rotation = obj.get("use_rotation", True)
        props.object_offset = Vector(obj.get("object_offset", (0.0, 0.0, 0.0)))
        
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