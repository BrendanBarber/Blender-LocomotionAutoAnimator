import bpy
from bpy.types import Panel, PropertyGroup
from bpy.props import (
    StringProperty, 
    IntProperty, 
    FloatVectorProperty, 
    FloatProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty
)
from mathutils import Vector

def property_update_callback(self, context):
    """Callback function for when properties are updated"""
    # Import here to avoid circular imports
    try:
        from . import operators
        operators.update_path_from_properties(context)
    except ImportError:
        try:
            import operators
            operators.update_path_from_properties(context)
        except:
            pass

# Import animation library functions with safe fallbacks
def get_available_poses(self, context):
    """Get available poses for enum property with safe fallback"""
    try:
        from . import animation_library
        return animation_library.get_available_poses(self, context)
    except ImportError:
        try:
            import animation_library
            return animation_library.get_available_poses(self, context)
        except ImportError:
            return [("NONE", "None", "No pose available", 'X', 0)]
    except Exception as e:
        print(f"Error getting poses: {e}")
        return [("NONE", "None", "Error loading poses", 'ERROR', 0)]

def get_available_animations(self, context):
    """Get available animations for enum property with safe fallback"""
    try:
        from . import animation_library
        return animation_library.get_available_animations(self, context)
    except ImportError:
        try:
            import animation_library
            return animation_library.get_available_animations(self, context)
        except ImportError:
            return [("NONE", "None", "No animation available", 'X', 0)]
    except Exception as e:
        print(f"Error getting animations: {e}")
        return [("NONE", "None", "Error loading animations", 'ERROR', 0)]

class AnimationPathProperties(PropertyGroup):
    """Properties for Animation Path creation and editing"""
    
    start_pos: FloatVectorProperty(
        name="Start Position",
        description="Starting position of the animation path",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION',
        update=property_update_callback
    )
    
    end_pos: FloatVectorProperty(
        name="End Position", 
        description="Ending position of the animation path",
        default=(5.0, 0.0, 0.0),
        subtype='TRANSLATION',
        update=property_update_callback
    )
    
    start_frame: IntProperty(
        name="Start Frame",
        description="Frame when the path begins",
        default=1,
        min=1,
        update=property_update_callback
    )
    
    end_frame: IntProperty(
        name="End Frame",
        description="Frame when the path ends",
        default=100,
        min=2,
        update=property_update_callback
    )
    
    start_pose: EnumProperty(
        name="Start Pose",
        description="Initial animation state",
        items=get_available_poses,
        update=property_update_callback
    )
    
    end_pose: EnumProperty(
        name="End Pose",
        description="Final animation state",
        items=get_available_poses,
        update=property_update_callback
    )
    
    anim: EnumProperty(
        name="Main Animation",
        description="Main animation loop during the path",
        items=get_available_animations,
        update=property_update_callback
    )
    
    start_blend_frames: IntProperty(
        name="Start Blend Frames",
        description="Frames to blend from start pose into main animation",
        default=5,
        min=0,
        update=property_update_callback
    )
    
    end_blend_frames: IntProperty(
        name="End Blend Frames",
        description="Frames to blend from main animation to end pose",
        default=5,
        min=0,
        update=property_update_callback
    )

    blend_speed: BoolProperty(
        name="Blend Speed",
        description="Use the blend frames to determine speed, this will result in speeding up and slowing down at start and end",
        default=False,
        update=property_update_callback
    )

    anim_speed_mult: FloatProperty(
        name="Animation Speed Multiplier",
        description="Change the base speed of the main animation, 1x is normal speed.",
        default=1.0,
        min=0.1,
        max=10.0,
        update=property_update_callback
    )
    
    target_object: PointerProperty(
        name="Target Object",
        description="Object to animate along the path",
        type=bpy.types.Object,
        update=property_update_callback
    )
    
    use_rotation: BoolProperty(
        name="Follow Curve Rotation",
        description="The object will rotate along the curve facing the correct direction",
        default=True,
        update=property_update_callback
    )
    
    object_z_offset: FloatProperty(
        name="Object Z Offset",
        description="Z offset of the object from the path",
        default=0.0,
        update=property_update_callback
    )
    
    clear_existing_animation: BoolProperty(
        name="Clear Existing Animation",
        description="Clear existing location keyframes before applying path animation",
        default=True
    )
    
    keyframe_density: IntProperty(
        name="Keyframe Density",
        description="Interval between keyframes (1 = every frame, 5 = every 5 frames)",
        default=1,
        min=1,
        max=10
    )

    use_curvature_control: BoolProperty(
        name="Curvature Speed Control",
        description="Automatically adjust speed based on curve tightness",
        default=False,
        update=property_update_callback
    )
    
    min_speed_factor: FloatProperty(
        name="Min Speed (Curves)",
        description="Minimum speed multiplier on tight curves (0.4 = 40% speed)",
        default=0.75,
        min=0.1,
        max=1.0,
        update=property_update_callback
    )
    
    max_speed_factor: FloatProperty(
        name="Max Speed (Straights)",
        description="Maximum speed multiplier on straight sections (1.5 = 150% speed)",
        default=1.0,
        min=1.0,
        max=5.0,
        update=property_update_callback
    )
    
    curvature_sensitivity: FloatProperty(
        name="Curvature Sensitivity",
        description="How dramatically speed changes with curvature (higher = more dramatic)",
        default=1.0,
        min=0.1,
        max=3.0,
        update=property_update_callback
    )
    
    curvature_samples: IntProperty(
        name="Curve Samples",
        description="Number of points to sample for curvature analysis (more = smoother but slower)",
        default=50,
        min=20,
        max=200,
        update=property_update_callback
    )

    use_keyframe_reduction: BoolProperty(
        name="Use Keyframe Reduction",
        description="Reduce the number of keyframes using Bezier approximation for smoother curves",
        default=True
    )
    
    keyframe_error_tolerance: FloatProperty(
        name="Keyframe Error Tolerance",
        description="Maximum allowed error when reducing keyframes (lower = more keyframes)",
        default=0.01,
        min=0.001,
        max=0.1,
        step=0.001,
        precision=3
    )

    use_speed_matched_animation: bpy.props.BoolProperty(
        name="Speed-Matched Animation",
        description="Use multiple NLA strips with different playback speeds instead of single strip",
        default=True
    )

classes = [
    AnimationPathProperties,
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
    
    try:
        bpy.types.Scene.animation_path_props = PointerProperty(type=AnimationPathProperties)
    except:
        pass

def unregister():
    try:
        del bpy.types.Scene.animation_path_props
    except:
        pass
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass