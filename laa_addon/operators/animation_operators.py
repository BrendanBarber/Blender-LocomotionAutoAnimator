"""
Animation-related operators for path following and object animation with pose/animation support
"""

import bpy
import math
from mathutils import Vector
from bpy.types import Operator

class ANIMPATH_OT_animate_object_along_path(Operator):
    """Animate the assigned object along the selected path using Follow Path constraint and apply poses/animations"""
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
            # Get animation properties
            start_frame = path_obj.get("start_frame", 1)
            end_frame = path_obj.get("end_frame", 100)
            use_rotation = path_obj.get("use_rotation", True)
            object_offset = Vector(path_obj.get("object_offset", (0.0, 0.0, 0.0)))
            
            # Get pose and animation settings
            start_pose = path_obj.get("start_pose", "NONE")
            end_pose = path_obj.get("end_pose", "NONE")
            main_anim = path_obj.get("anim", "NONE")
            start_blend_frames = path_obj.get("start_blend_frames", 5)
            end_blend_frames = path_obj.get("end_blend_frames", 5)
            
            # Ensure curve data path_duration matches the frame range
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
            
            # Create Follow Path constraint for object movement
            follow_path = target_obj.constraints.new(type='FOLLOW_PATH')
            follow_path.target = path_obj
            follow_path.name = f"FollowPath_{path_obj.name}"
            
            # Enable curve following for rotation
            follow_path.use_curve_follow = True
            follow_path.use_fixed_location = False
            follow_path.forward_axis = 'FORWARD_Y'
            follow_path.up_axis = 'UP_Z'
            
            # Set Animation target to be the target object
            animation_target = target_obj
            
            # Handle rotation based on use_rotation setting
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
            
            # Set interpolation for path animation
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
            
            # Apply poses and animations to rig (if target is an armature or has an armature child)
            self._apply_rig_animations(target_obj, path_obj, start_frame, end_frame,
                                     start_pose, end_pose, main_anim,
                                     start_blend_frames, end_blend_frames)
            
            context.scene.frame_set(start_frame)
            
            rotation_info = "with curve rotation" if (use_rotation and follow_path.use_curve_follow) else "without rotation"
            self.report({'INFO'}, f"Added Follow Path animation to {target_obj.name} from frame {start_frame} to {end_frame} {rotation_info}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error setting up path animation: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
    def _apply_rig_animations(self, target_obj, path_obj, start_frame, end_frame,
                             start_pose, end_pose, main_anim, start_blend_frames, end_blend_frames):
        """Apply poses and animations to the rig"""
        # Find the armature - either the target object itself or a child
        armature_obj = self._find_armature(target_obj)
        
        if not armature_obj:
            print(f"No armature found for {target_obj.name} - skipping pose/animation application")
            return
        
        # IMPORTANT: Only apply to armature if it's NOT the same as target_obj
        # or if target_obj already has path animation keyframes
        if armature_obj == target_obj:
            # Store existing animation data before applying rig animations
            existing_action = None
            if target_obj.animation_data and target_obj.animation_data.action:
                existing_action = target_obj.animation_data.action
                
            # Apply rig animations
            from .. import animation_library
            success = animation_library.create_nla_strips_for_path(armature_obj, path_obj)
            
            # Restore the original action to preserve path keyframes
            if existing_action and target_obj.animation_data:
                target_obj.animation_data.action = existing_action
                
        else:
            # Safe to apply to child armature
            from .. import animation_library
            success = animation_library.create_nla_strips_for_path(armature_obj, path_obj)
    
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


class ANIMPATH_OT_apply_rig_animations_only(Operator):
    """Apply only the poses and animations to the rig without path animation"""
    bl_idname = "animpath.apply_rig_animations_only"
    bl_label = "Apply Rig Animations Only"
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
        
        try:
            # Get animation properties
            start_frame = path_obj.get("start_frame", 1)
            end_frame = path_obj.get("end_frame", 100)
            start_pose = path_obj.get("start_pose", "NONE")
            end_pose = path_obj.get("end_pose", "NONE")
            main_anim = path_obj.get("anim", "NONE")
            start_blend_frames = path_obj.get("start_blend_frames", 5)
            end_blend_frames = path_obj.get("end_blend_frames", 5)
            
            # Find the armature - either the target object itself or a child
            armature_obj = self._find_armature(target_obj)
            
            if not armature_obj:
                self.report({'ERROR'}, f"No armature found for {target_obj.name}")
                return {'CANCELLED'}
            
            print(f"Applying animations to armature: {armature_obj.name}")
            
            # Import animation library functions
            try:
                from . import animation_library
            except ImportError:
                try:
                    import animation_library
                except ImportError:
                    self.report({'ERROR'}, "Animation library not available")
                    return {'CANCELLED'}
            
            # Create NLA strips for the armature
            success = animation_library.create_nla_strips_for_path(armature_obj, path_obj)
            
            if success:
                self.report({'INFO'}, f"Successfully applied poses/animations to {armature_obj.name}")
            else:
                self.report({'WARNING'}, f"Failed to apply poses/animations to {armature_obj.name}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error applying rig animations: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
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


# List of classes to register
classes = [
    ANIMPATH_OT_animate_object_along_path,
    ANIMPATH_OT_apply_rig_animations_only,
]

def register():
    """Register animation operators"""
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
    """Unregister animation operators"""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass