import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

try:
    from . import path_operators
    from . import animation_operators  
    from . import utility_operators
except ImportError:
    import path_operators
    import animation_operators
    import utility_operators

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
        from mathutils import Vector
        props = context.scene.animation_path_props
        
        # Import AnimationPath here to avoid circular imports
        try:
            from ..animation_path import AnimationPath
        except ImportError:
            from animation_path import AnimationPath
        
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
        
        # Update curve data's path_duration
        if path_obj.data and hasattr(path_obj.data, 'path_duration'):
            path_obj.data.path_duration = path.duration
            print(f"Updated path_duration to {path.duration} frames")
        
        if props.target_object:
            path_obj["target_object"] = props.target_object.name
        
        # Update control point positions if they exist
        for point_type in ["start", "end"]:
            point_name = path_obj.get(f"{point_type}_control_point")
            if point_name:
                point_obj = bpy.data.objects.get(point_name)
                if point_obj:
                    new_pos = getattr(props, f"{point_type}_pos")
                    point_obj.location = new_pos
        
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

def register():
    """Register all operator modules"""
    try:
        unregister()
    except:
        pass
    
    # Register all operator modules
    path_operators.register()
    animation_operators.register()
    utility_operators.register()
    
    # Register the selection change handler
    if selection_changed_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(selection_changed_handler)

def unregister():
    """Unregister all operator modules"""
    # Unregister the selection change handler
    if selection_changed_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(selection_changed_handler)
    
    # Unregister all operator modules
    utility_operators.unregister()
    animation_operators.unregister()
    path_operators.unregister()