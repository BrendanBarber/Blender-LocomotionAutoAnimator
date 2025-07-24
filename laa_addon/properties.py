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

class AnimationPathProperties(PropertyGroup):
    """Properties for Animation Path creation and editing"""
    
    start_pos: FloatVectorProperty(
        name="Start Position",
        description="Starting position of the animation path",
        default=(0.0, 0.0, 0.0),
        subtype='TRANSLATION'
    )
    
    end_pos: FloatVectorProperty(
        name="End Position", 
        description="Ending position of the animation path",
        default=(5.0, 0.0, 0.0),
        subtype='TRANSLATION'
    )
    
    start_frame: IntProperty(
        name="Start Frame",
        description="Frame when the path begins",
        default=1,
        min=1
    )
    
    end_frame: IntProperty(
        name="End Frame",
        description="Frame when the path ends",
        default=100,
        min=2
    )
    
    start_pose: StringProperty(
        name="Start Pose",
        description="Initial animation state",
        default="idle"
    )
    
    end_pose: StringProperty(
        name="End Pose",
        description="Final animation state",
        default="idle"
    )
    
    anim: StringProperty(
        name="Main Animation",
        description="Main animation loop during the path",
        default="walk"
    )
    
    start_blend_frames: IntProperty(
        name="Start Blend Frames",
        description="Frames to blend from start pose into main animation",
        default=5,
        min=0
    )
    
    end_blend_frames: IntProperty(
        name="End Blend Frames",
        description="Frames to blend from main animation to end pose",
        default=5,
        min=0
    )
    
    target_object: PointerProperty(
        name="Target Object",
        description="Object to animate along the path",
        type=bpy.types.Object
    )
    
    use_rotation: BoolProperty(
        name="Align to Path",
        description="Rotate object to face the direction of movement",
        default=True
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