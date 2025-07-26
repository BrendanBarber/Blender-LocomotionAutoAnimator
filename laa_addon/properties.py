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
    
    start_pose: StringProperty(
        name="Start Pose",
        description="Initial animation state",
        default="idle",
        update=property_update_callback
    )
    
    end_pose: StringProperty(
        name="End Pose",
        description="Final animation state",
        default="idle",
        update=property_update_callback
    )
    
    anim: StringProperty(
        name="Main Animation",
        description="Main animation loop during the path",
        default="walk",
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
    
    object_offset: FloatVectorProperty(
        name="Object Offset",
        description="XYZ offset of the object from the path",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION',
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