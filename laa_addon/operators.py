import bpy
import math
from mathutils import Vector
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty
from bpy.app.handlers import persistent

try:
    from .animation_path import AnimationPath, create_animation_path_from_properties
except ImportError:
    from animation_path import AnimationPath, create_animation_path_from_properties

# Global variable to prevent infinite recursion during property updates
_updating_properties = False

def load_path_properties_from_object(context, path_obj):
    """Load properties from a path object into the properties panel"""
    global _updating_properties
    if _updating_properties or not path_obj or not path_obj.get("is_animation_path"):
        return
    
    _updating_properties = True
    try:
        props = context.scene.animation_path_props
        
        props.start_frame = path_obj.get("start_frame", 1)
        props.end_frame = path_obj.get("end_frame", 100)
        props.start_pose = path_obj.get("start_pose", "idle")
        props.end_pose = path_obj.get("end_pose", "idle")
        props.anim = path_obj.get("anim", "walk")
        props.start_blend_frames = path_obj.get("start_blend_frames", 0)
        props.end_blend_frames = path_obj.get("end_blend_frames", 0)
        props.use_rotation = path_obj.get("use_rotation", True)
        
        # Load object offset
        object_offset = path_obj.get("object_offset", (0.0, 0.0, 0.0))
        props.object_offset = Vector(object_offset)
        
        target_obj_name = path_obj.get("target_object")
        if target_obj_name:
            target_obj = bpy.data.objects.get(target_obj_name)
            if target_obj:
                props.target_object = target_obj
        else:
            props.target_object = None
        
        # Load positions from control points (DON'T update curve geometry)
        for point_type in ["start", "end"]:
            point_name = path_obj.get(f"{point_type}_control_point")
            if point_name:
                point_obj = bpy.data.objects.get(point_name)
                if point_obj:
                    setattr(props, f"{point_type}_pos", point_obj.location)
        
        # Store reference to currently selected path
        context.scene["_selected_animation_path"] = path_obj.name
        
    finally:
        _updating_properties = False

def update_path_from_properties(context):
    """Update the selected path object from current properties"""
    global _updating_properties
    if _updating_properties:
        return
    
    selected_path_name = context.scene.get("_selected_animation_path")
    if not selected_path_name:
        return
    
    path_obj = bpy.data.objects.get(selected_path_name)
    if not path_obj or not path_obj.get("is_animation_path"):
        return
    
    _updating_properties = True
    try:
        props = context.scene.animation_path_props
        
        # Create AnimationPath to validate properties
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
        
        # Update path object properties
        path_obj["start_frame"] = path.start_frame
        path_obj["end_frame"] = path.end_frame
        path_obj["start_pose"] = path.start_pose
        path_obj["end_pose"] = path.end_pose
        path_obj["anim"] = path.anim
        path_obj["start_blend_frames"] = path.start_blend_frames
        path_obj["end_blend_frames"] = path.end_blend_frames
        path_obj["use_rotation"] = props.use_rotation
        path_obj["object_offset"] = tuple(props.object_offset)
        
        # **FIX: Update curve data's path_duration**
        if path_obj.data and hasattr(path_obj.data, 'path_duration'):
            path_obj.data.path_duration = path.duration
            print(f"Updated path_duration to {path.duration} frames")
        
        if props.target_object:
            path_obj["target_object"] = props.target_object.name
        
        # Update control point positions if they exist (DON'T reset curve geometry)
        for point_type in ["start", "end"]:
            point_name = path_obj.get(f"{point_type}_control_point")
            if point_name:
                point_obj = bpy.data.objects.get(point_name)
                if point_obj:
                    new_pos = getattr(props, f"{point_type}_pos")
                    point_obj.location = new_pos
        
        # **REMOVED: Don't automatically update curve geometry from control points**
        # This was causing the curve to reset to straight line
        # path.update_curve_from_control_points(path_obj)
        
    except ValueError as e:
        # If validation fails, revert to previous values
        load_path_properties_from_object(context, path_obj)
    finally:
        _updating_properties = False

@persistent
def selection_changed_handler(scene, depsgraph):
    """Handler called when selection changes"""
    if not hasattr(bpy.context, 'active_object'):
        return
    
    active_obj = bpy.context.active_object
    if active_obj and active_obj.get("is_animation_path"):
        load_path_properties_from_object(bpy.context, active_obj)

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

class ANIMPATH_OT_animate_object_along_path(Operator):
    """Animate the assigned object along the selected path using Follow Path constraint"""
    bl_idname = "animpath.animate_object_along_path"
    bl_label = "Animate Object Along Path"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        path_obj = context.active_object
        
        if not path_obj or not path_obj.get("is_animation_path"):
            self.report({'ERROR'}, "No Animation Path selected")
            return {'CANCELLED'}
        
        target_obj_name = path_obj.get("target_object")
        if not target_obj_name:
            self.report({'ERROR'}, "No target object assigned to this path")
            return {'CANCELLED'}
        
        target_obj = bpy.data.objects.get(target_obj_name)
        if not target_obj:
            self.report({'ERROR'}, f"Target object '{target_obj_name}' not found")
            return {'CANCELLED'}
        
        # Ensure target object is in current view layer
        if target_obj.name not in context.view_layer.objects:
            self.report({'ERROR'}, f"Target object '{target_obj_name}' is not in the current view layer")
            return {'CANCELLED'}
        
        try:
            start_frame = path_obj.get("start_frame", 1)
            end_frame = path_obj.get("end_frame", 100)
            use_rotation = path_obj.get("use_rotation", True)
            object_offset = Vector(path_obj.get("object_offset", (0.0, 0.0, 0.0)))
            
            # **FIX: Ensure curve data path_duration matches the frame range**
            if path_obj.data and hasattr(path_obj.data, 'path_duration'):
                new_duration = end_frame - start_frame
                if path_obj.data.path_duration != new_duration:
                    path_obj.data.path_duration = new_duration
                    print(f"Updated curve path_duration to {new_duration} frames")
            
            props = context.scene.animation_path_props
            if props.clear_existing_animation:
                target_obj.animation_data_clear()
                for constraint in target_obj.constraints:
                    if constraint.type == 'FOLLOW_PATH':
                        target_obj.constraints.remove(constraint)
            
            # Create Follow Path constraint
            follow_path = target_obj.constraints.new(type='FOLLOW_PATH')
            follow_path.target = path_obj
            follow_path.name = f"FollowPath_{path_obj.name}"
            
            # **FIX: Enable curve following for rotation**
            follow_path.use_curve_follow = True  # This makes rotation follow the curve
            follow_path.use_fixed_location = False
            follow_path.forward_axis = 'FORWARD_Y'
            follow_path.up_axis = 'UP_Z'
            
            # Set Animation target to be the target object
            animation_target = target_obj
            
            # **UPDATED: Handle rotation based on use_rotation setting**
            if use_rotation:
                # When use_rotation is True, set initial rotation and let curve following handle the rest
                context.scene.frame_set(start_frame)
                
                # Get initial direction from curve and set rotation
                initial_rotation = (0, 0, math.radians(180))
                animation_target.rotation_euler = initial_rotation
                animation_target.keyframe_insert(data_path="rotation_euler", frame=start_frame)
                animation_target.keyframe_insert(data_path="rotation_euler", frame=end_frame)
            else:
                # When use_rotation is False, disable curve following
                follow_path.use_curve_follow = False
                
                # Keyframe current rotation to prevent unwanted rotation
                current_rotation = animation_target.rotation_euler.copy()
                animation_target.rotation_euler = current_rotation
                animation_target.keyframe_insert(data_path="rotation_euler", frame=start_frame - 1)
                animation_target.keyframe_insert(data_path="rotation_euler", frame=start_frame)
                animation_target.keyframe_insert(data_path="rotation_euler", frame=end_frame)
                animation_target.keyframe_insert(data_path="rotation_euler", frame=end_frame + 1)
            
            # Position keyframes with offset
            context.scene.frame_set(start_frame)
            start_pos = self._get_control_point_position(path_obj, "start")
            
            animation_target.location = object_offset
            animation_target.keyframe_insert(data_path="location", frame=start_frame)

            # Position at end
            context.scene.frame_set(end_frame)
            animation_target.location = object_offset
            animation_target.keyframe_insert(data_path="location", frame=end_frame)

            # Final position after path ends
            end_pos = self._get_control_point_position(path_obj, "end")
            if end_pos:
                animation_target.location = end_pos + object_offset
                animation_target.keyframe_insert(data_path="location", frame=end_frame + 1)

            # Final rotation after path ends
            if use_rotation:
                context.scene.frame_set(end_frame)
                world_matrix = animation_target.matrix_world.copy()
                final_rotation = world_matrix.to_euler()

                context.scene.frame_set(end_frame + 1)
                animation_target.rotation_euler = final_rotation
                animation_target.keyframe_insert(data_path="rotation_euler", frame=end_frame + 1)

            # Animate constraint offset
            follow_path.offset_factor = 0.0
            follow_path.keyframe_insert(data_path="offset_factor", frame=start_frame)
            follow_path.offset_factor = 1.0
            follow_path.keyframe_insert(data_path="offset_factor", frame=end_frame)
            
            # Control constraint influence
            follow_path.influence = 1.0
            follow_path.keyframe_insert(data_path="influence", frame=start_frame)
            follow_path.keyframe_insert(data_path="influence", frame=end_frame)
            follow_path.influence = 0.0
            follow_path.keyframe_insert(data_path="influence", frame=end_frame + 1)
            follow_path.keyframe_insert(data_path="influence", frame=start_frame - 1)
            
            # Set interpolation
            if animation_target.animation_data and animation_target.animation_data.action:
                for fcurve in animation_target.animation_data.action.fcurves:
                    if fcurve.data_path.endswith("offset_factor"):
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'LINEAR'
                    elif fcurve.data_path.endswith("influence"):
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'CONSTANT'
            
            context.view_layer.update()

            # Only select if object is in current view layer
            if animation_target.name in context.view_layer.objects:
                bpy.ops.object.select_all(action='DESELECT')
                animation_target.select_set(True)
                context.view_layer.objects.active = animation_target

                bpy.ops.constraint.followpath_path_animate(
                    constraint=follow_path.name,
                    owner='OBJECT'
                )
            
            context.scene.frame_set(start_frame)
            
            rotation_info = "with curve rotation" if (use_rotation and follow_path.use_curve_follow) else "without rotation"
            self.report({'INFO'}, f"Added Follow Path animation to {target_obj.name} from frame {start_frame} to {end_frame} {rotation_info}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error setting up path animation: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

    def _calculate_initial_rotation(self, path_obj):
        """Calculate the initial rotation to align with path direction at start"""
        try:
            curve_data = path_obj.data
            if not curve_data.splines:
                return (0, 0, 0)
            
            spline = curve_data.splines[0]
            
            # Get start and a point slightly ahead to determine direction
            start_pos = self._get_curve_position_at_start(spline)
            direction_pos = self._get_curve_position_near_start(spline)
            
            if start_pos and direction_pos:
                # Calculate direction vector
                direction = direction_pos - start_pos
                if direction.length > 0.001:  # Avoid zero-length vectors
                    direction.normalize()
                    
                    # Calculate Z rotation (yaw) - rotation around Z-axis for flat paths
                    # atan2(x, y) gives angle from Y-axis
                    angle_z = math.atan2(direction.x, direction.y)
                    
                    # Apply the correction: negate and add pi (for flat paths only)
                    angle_z = (-angle_z) + math.pi
                    
                    # For flat paths, no X or Y rotation needed
                    return (0, 0, angle_z)
                
            # Fallback rotation for flat paths
            return (0, 0, math.pi)
            
        except Exception as e:
            print(f"Error calculating initial rotation: {e}")
            return (0, 0, math.pi)

    def _get_curve_position_at_start(self, spline):
        """Get the position at the very start of the curve"""
        if spline.type == 'NURBS' and spline.points:
            return Vector(spline.points[0].co[:3])
        elif spline.type == 'BEZIER' and spline.bezier_points:
            return spline.bezier_points[0].co
        return None

    def _get_curve_position_near_start(self, spline):
        """Get a position slightly ahead of the start to determine direction"""
        if spline.type == 'NURBS' and len(spline.points) > 1:
            # Use the second control point or interpolate slightly ahead
            if len(spline.points) >= 2:
                p0 = Vector(spline.points[0].co[:3])
                p1 = Vector(spline.points[1].co[:3])
                # Return a point 10% of the way to the second control point
                return p0.lerp(p1, 0.1)
        elif spline.type == 'BEZIER' and spline.bezier_points:
            # Use the first control point's right handle or the second point
            if len(spline.bezier_points) >= 2:
                p0 = spline.bezier_points[0].co
                handle_right = spline.bezier_points[0].handle_right
                
                # If the handle is in the same position as the point, use next point
                if (handle_right - p0).length < 0.001:
                    return spline.bezier_points[1].co
                else:
                    # Use the handle direction
                    return p0.lerp(handle_right, 0.5)
            elif len(spline.bezier_points) == 1:
                # Single point, use the right handle
                p0 = spline.bezier_points[0].co
                handle_right = spline.bezier_points[0].handle_right
                return handle_right
        
        return None
    
    def _get_control_point_position(self, path_obj, point_type):
        """Helper to get control point position"""
        point_name = path_obj.get(f"{point_type}_control_point")
        if point_name:
            point_obj = bpy.data.objects.get(point_name)
            if point_obj:
                return point_obj.location.copy()
        
        # Fallback to stored data
        fallback_pos = path_obj.get(f"{point_type}_pos")
        if fallback_pos:
            return Vector(fallback_pos)
        
        # Last resort: curve geometry
        if point_type == "start":
            return self._get_curve_start_position(path_obj)
        elif point_type == "end":
            return self._get_curve_end_position(path_obj)
        
        return None
    
    def _get_curve_start_position(self, curve_obj):
        """Get start position from curve"""
        curve_data = curve_obj.data
        if curve_data.splines:
            spline = curve_data.splines[0]
            if spline.type == 'NURBS' and spline.points:
                return Vector(spline.points[0].co[:3])
            elif spline.type == 'BEZIER' and spline.bezier_points:
                return spline.bezier_points[0].co
        return None
    
    def _get_curve_end_position(self, curve_obj):
        """Get end position from curve"""
        curve_data = curve_obj.data
        if curve_data.splines:
            spline = curve_data.splines[0]
            if spline.type == 'NURBS' and spline.points:
                return Vector(spline.points[-1].co[:3])
            elif spline.type == 'BEZIER' and spline.bezier_points:
                return spline.bezier_points[-1].co
        return None

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
            
            # **REMOVED: Don't update curve geometry automatically**
            # path.update_curve_from_control_points(obj)
            
            obj["start_frame"] = path.start_frame
            obj["end_frame"] = path.end_frame
            obj["start_pose"] = path.start_pose
            obj["end_pose"] = path.end_pose
            obj["anim"] = path.anim
            obj["start_blend_frames"] = path.start_blend_frames
            obj["end_blend_frames"] = path.end_blend_frames
            obj["object_offset"] = tuple(props.object_offset)
            
            # **FIX: Update curve data's path_duration**
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

classes = [
    ANIMPATH_OT_set_start_position,
    ANIMPATH_OT_set_end_position,
    ANIMPATH_OT_set_target_object,
    ANIMPATH_OT_create_path,
    ANIMPATH_OT_animate_object_along_path,
    ANIMPATH_OT_update_path,
    ANIMPATH_OT_delete_path,
    ANIMPATH_OT_load_path_to_properties,
    ANIMPATH_OT_reset_curve_to_control_points,
]

def register():
    try:
        unregister()
    except:
        pass
    
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
    
    # Register the selection change handler
    if selection_changed_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(selection_changed_handler)

def unregister():
    # Unregister the selection change handler
    if selection_changed_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(selection_changed_handler)
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass