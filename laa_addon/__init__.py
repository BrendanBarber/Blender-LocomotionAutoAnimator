bl_info = {
    "name": "Locomotion Auto Animator",
    "author": "Gilan (Brendan)",
    "version": (1, 0, 0),
    "blender": (4, 4, 0),
    "location": "Sidebar > Locomotion Auto Animator",
    "description": "Automatically create movement cycles along a path for the SQM Minecraft Rig",
    "warning": "",
    "doc_url": "",
    "category": "Animation",
}

import bpy
import sys
import importlib

try:
    from . import animation_path
    from . import operators
    from . import panels
    from . import properties
    from . import animation_library
except ImportError as e:
    print(f"Import error in Locomotion Auto Animator: {e}")
    import animation_path
    import operators
    import panels
    import properties
    import animation_library

def reload_modules():
    modules = [animation_path, operators, panels, properties, animation_library]
    for module in modules:
        if module in sys.modules:
            importlib.reload(module)

def register():
    try:
        reload_modules()
        properties.register()
        panels.register()
        operators.register()
        print("Locomotion Auto Animator addon registered successfully")
    except Exception as e:
        print(f"Error registering Locomotion Auto Animator addon: {e}")
        import traceback
        traceback.print_exc()

def unregister():
    try:
        operators.unregister()
        panels.unregister()
        properties.unregister()
        print("Locomotion Auto Animator addon unregistered successfully")
    except Exception as e:
        print(f"Error unregistering Locomotion Auto Animator addon: {e}")

if __name__ == "__main__":
    register()