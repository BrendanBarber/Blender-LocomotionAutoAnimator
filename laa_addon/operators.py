import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty, FloatVectorProperty, BoolProperty
from mathutils import Vector

try:
    from .animation_path import AnimationPath, create_animation_path_from_properties
except ImportError:
    from animation_path import AnimationPath, create_animation_path_from_properties

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
            
            # Set scene frame range to match animation path
            context.scene.frame_start = path.start_frame
            context.scene.frame_end = path.end_frame
            
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
            
            props = context.scene.animation_path_props
            if props.clear_existing_animation:
                target_obj.animation_data_clear()
                for constraint in target_obj.constraints:
                    if constraint.type == 'FOLLOW_PATH':
                        target_obj.constraints.remove(constraint)
            
            original_location = target_obj.location.copy()
            
            follow_path = target_obj.constraints.new(type='FOLLOW_PATH')
            follow_path.target = path_obj
            follow_path.name = f"FollowPath_{path_obj.name}"
            
            follow_path.use_curve_follow = use_rotation
            follow_path.use_fixed_location = False
            follow_path.forward_axis = 'FORWARD_Y'
            follow_path.up_axis = 'UP_Z'
            
            # Position at start
            context.scene.frame_set(start_frame)
            start_pos = self._get_control_point_position(path_obj, "start")
            if start_pos:
                target_obj.location = start_pos
                target_obj.keyframe_insert(data_path="location", frame=start_frame)
                if not use_rotation:
                    target_obj.keyframe_insert(data_path="rotation_euler", frame=start_frame)
            
            # Position at end
            context.scene.frame_set(end_frame)
            end_pos = self._get_control_point_position(path_obj, "end")
            if end_pos:
                target_obj.location = end_pos
                target_obj.keyframe_insert(data_path="location", frame=end_frame)
                if not use_rotation:
                    target_obj.keyframe_insert(data_path="rotation_euler", frame=end_frame)

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
            
            # Final position keyframes
            context.scene.frame_set(end_frame)
            target_obj.location = start_pos
            target_obj.keyframe_insert(data_path="location", frame=end_frame)
            target_obj.location = end_pos
            target_obj.keyframe_insert(data_path="location", frame=end_frame + 1)
            
            # Set interpolation
            if target_obj.animation_data and target_obj.animation_data.action:
                for fcurve in target_obj.animation_data.action.fcurves:
                    if fcurve.data_path.endswith("offset_factor"):
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'LINEAR'
                    elif fcurve.data_path.endswith("influence"):
                        for keyframe in fcurve.keyframe_points:
                            keyframe.interpolation = 'CONSTANT'
            
            context.view_layer.update()

            # Only select if object is in current view layer
            if target_obj.name in context.view_layer.objects:
                bpy.ops.object.select_all(action='DESELECT')
                target_obj.select_set(True)
                context.view_layer.objects.active = target_obj

                bpy.ops.constraint.followpath_path_animate(
                    constraint=follow_path.name,
                    owner='OBJECT'
                )
            
            context.scene.frame_set(start_frame)
            self.report({'INFO'}, f"Added Follow Path animation to {target_obj.name} from frame {start_frame} to {end_frame}")
            
        except Exception as e:
            self.report({'ERROR'}, f"Error setting up path animation: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}
    
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
            
            path.update_curve_from_control_points(obj)
            
            obj["start_frame"] = path.start_frame
            obj["end_frame"] = path.end_frame
            obj["start_pose"] = path.start_pose
            obj["end_pose"] = path.end_pose
            obj["anim"] = path.anim
            obj["start_blend_frames"] = path.start_blend_frames
            obj["end_blend_frames"] = path.end_blend_frames
            
            if props.target_object:
                obj["target_object"] = props.target_object.name
            obj["use_rotation"] = props.use_rotation
            
            # Set scene frame range to match updated animation path
            context.scene.frame_start = path.start_frame
            context.scene.frame_end = path.end_frame
            
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
        
        parent_empty_name = obj.get("laa_path_parent")
        parent_empty = bpy.data.objects.get(parent_empty_name) if parent_empty_name else None
        path_name = obj.name
        
        if parent_empty:
            bpy.data.objects.remove(parent_empty, do_unlink=True)
            self.report({'INFO'}, f"Deleted Animation Path hierarchy: {path_name}")
        else:
            # Fallback cleanup
            start_point_name = obj.get("start_control_point")
            end_point_name = obj.get("end_control_point")
            
            for point_name in [start_point_name, end_point_name]:
                if point_name:
                    point_obj = bpy.data.objects.get(point_name)
                    if point_obj:
                        bpy.data.objects.remove(point_obj, do_unlink=True)
            
            bpy.data.objects.remove(obj, do_unlink=True)
            self.report({'INFO'}, f"Deleted Animation Path: {path_name}")
        
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

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass