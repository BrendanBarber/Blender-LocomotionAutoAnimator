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

try:
    from . import properties
    from . import animation_library
    animation_library_available = True
except ImportError:
    try:
        import properties
        import animation_library
        animation_library_available = True
    except ImportError:
        import properties
        animation_library_available = False
        print("Animation library not available")

class ANIMPATH_PT_main_panel(Panel):
    """Main Animation Path panel in 3D Viewport sidebar"""
    bl_label = "Animation Paths"
    bl_idname = "ANIMPATH_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Animation"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.animation_path_props
        
        # Show auto-sync status
        obj = context.active_object
        if obj and obj.get("is_animation_path"):
            box = layout.box()
            box.label(text=f"🔄 Auto-syncing: {obj.name}", icon='LINKED')
            box.label(text="Properties automatically update path", icon='INFO')
            box.label(text="Curve shape preserved on edits", icon='CHECKMARK')
        
        # Main creation box
        box = layout.box()
        box.label(text="Animation Path Creator", icon='CURVE_PATH')
        
        # Position setting section
        col = box.column(align=True)
        col.label(text="Set Positions:", icon='CURSOR')
        
        # Quick set buttons
        row = col.row(align=True)
        row.operator("animpath.set_start_position", text="Set Start", icon='PLUS')
        row.operator("animpath.set_end_position", text="Set End", icon='PLUS')
        
        col.separator()
        
        # Numerical input fields for positions
        col.label(text="Start Position:")
        col.prop(props, "start_pos", text="")
        
        col.separator()
        
        col.label(text="End Position:")
        col.prop(props, "end_pos", text="")
        
        col.separator()
        
        # Target object section
        col.label(text="Target Object:", icon='OBJECT_DATA')
        
        row = col.row(align=True)
        row.prop(props, "target_object", text="")
        row.operator("animpath.set_target_object", text="", icon='EYEDROPPER')
        
        if props.target_object:
            col.label(text=f"Target: {props.target_object.name}", icon='CHECKMARK')
        
        col.separator()
        
        # Create path button
        col.operator("animpath.create_path", text="Create Animation Path", icon='PLUS')

class ANIMPATH_PT_animation_settings(Panel):
    """Animation settings sub-panel"""
    bl_label = "Animation Settings"
    bl_idname = "ANIMPATH_PT_animation_settings"
    bl_parent_id = "ANIMPATH_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.animation_path_props
        
        col = layout.column(align=True)
        col.label(text="Timeline:")
        row = col.row(align=True)
        row.prop(props, "start_frame")
        row.prop(props, "end_frame")
        
        if props.start_frame >= props.end_frame:
            col.label(text="⚠ Start frame must be < End frame", icon='ERROR')
        
        col.separator()
        
        col = layout.column(align=True)
        col.label(text="Animation States:")
        col.prop(props, "start_pose")
        col.prop(props, "anim")
        col.prop(props, "end_pose")
        
        # Animation library info and refresh
        box = layout.box()
        box.label(text="Animation Library:", icon='BOOKMARKS')
        
        if animation_library_available:
            try:
                pose_count = len([item for item in animation_library.get_available_poses(None, context) 
                                if not item[0].endswith('_MISSING') and item[0] != 'NONE'])
                anim_count = len([item for item in animation_library.get_available_animations(None, context) 
                                if not item[0].endswith('_MISSING') and item[0] != 'NONE'])
                
                row = box.row(align=True)
                row.label(text=f"Poses: {pose_count}")
                row.label(text=f"Animations: {anim_count}")
                
                box.operator("animpath.refresh_animation_library", text="Refresh Library", icon='FILE_REFRESH')
                
            except Exception as e:
                box.label(text=f"Library error: {str(e)}", icon='ERROR')
        else:
            box.label(text="Animation library not available", icon='ERROR')
        
        col.separator()
        col.label(text="Blend Settings:")
        col.prop(props, "start_blend_frames")
        col.prop(props, "end_blend_frames")
        
        total_frames = props.end_frame - props.start_frame
        total_blend = props.start_blend_frames + props.end_blend_frames
        if total_blend > total_frames:
            col.label(text="⚠ Blend frames exceed path duration", icon='ERROR')

class ANIMPATH_PT_object_animation(Panel):
    """Object animation panel"""
    bl_label = "Object Animation"
    bl_idname = "ANIMPATH_PT_object_animation"
    bl_parent_id = "ANIMPATH_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.animation_path_props
        
        obj = context.active_object
        if obj and obj.get("is_animation_path"):
            box = layout.box()
            box.label(text=f"Path: {obj.name}", icon='CURVE_PATH')
            
            target_obj_name = obj.get("target_object")
            if target_obj_name:
                target_obj = bpy.data.objects.get(target_obj_name)
                if target_obj:
                    col = box.column(align=True)
                    col.label(text=f"Target: {target_obj.name}", icon='OBJECT_DATA')
                    
                    # Check if target has an armature (for rig detection)
                    has_armature = self._check_for_armature(target_obj)
                    if has_armature:
                        armature_name = self._get_armature_name(target_obj)
                        col.label(text=f"Rig: {armature_name}", icon='ARMATURE_DATA')
                    
                    col.separator()
                    
                    # Object offset controls
                    col.label(text="Object Z Offset from Path:", icon='TRANSFORM_ORIGINS')
                    col.prop(props, "object_z_offset", text="")
                    
                    col.separator()

                    # Updated rotation checkbox with better description
                    col.prop(props, "use_rotation", text="Follow Curve Rotation")

                    col.separator()
                    
                    # Main animation button
                    col.operator("animpath.animate_object_along_path", 
                               text="Animate Object + Rig", icon='PLAY')
                    
                    start_frame = obj.get("start_frame", 1)
                    end_frame = obj.get("end_frame", 100)
                    col.label(text=f"Frames: {start_frame} - {end_frame}")
                    
                    # Show pose/animation info
                    start_pose = obj.get("start_pose", "NONE")
                    main_anim = obj.get("anim", "NONE")
                    end_pose = obj.get("end_pose", "NONE")
                    
                    if start_pose != "NONE" or main_anim != "NONE" or end_pose != "NONE":
                        col.separator()
                        info_box = col.box()
                        info_box.label(text="Rig Animation Preview:", icon='INFO')
                        
                        if start_pose != "NONE":
                            info_box.label(text=f"Start: {start_pose}", icon='POSE_HLT')
                        if main_anim != "NONE":
                            info_box.label(text=f"Main: {main_anim}", icon='ANIM')
                        if end_pose != "NONE":
                            info_box.label(text=f"End: {end_pose}", icon='POSE_HLT')
                    
                else:
                    box.label(text=f"⚠ Target object '{target_obj_name}' not found", icon='ERROR')
            else:
                box.label(text="No target object assigned", icon='INFO')
                box.label(text="Set target in properties above")
        
        else:
            layout.label(text="Select an Animation Path", icon='INFO')
            layout.label(text="to animate an object along it")
    
    def _check_for_armature(self, target_obj):
        """Check if target object has an associated armature"""
        # Check if target is an armature
        if target_obj.type == 'ARMATURE':
            return True
        
        # Check direct children for armature
        for child in target_obj.children:
            if child.type == 'ARMATURE':
                return True
        
        # Check if target has an armature modifier pointing to an armature
        if hasattr(target_obj, 'modifiers'):
            for modifier in target_obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object:
                    return True
        
        # Recursively check children's children (one level deep)
        for child in target_obj.children:
            for grandchild in child.children:
                if grandchild.type == 'ARMATURE':
                    return True
        
        return False
    
    def _get_armature_name(self, target_obj):
        """Get the name of the associated armature"""
        # Check if target is an armature
        if target_obj.type == 'ARMATURE':
            return target_obj.name
        
        # Check direct children for armature
        for child in target_obj.children:
            if child.type == 'ARMATURE':
                return child.name
        
        # Check if target has an armature modifier pointing to an armature
        if hasattr(target_obj, 'modifiers'):
            for modifier in target_obj.modifiers:
                if modifier.type == 'ARMATURE' and modifier.object:
                    return modifier.object.name
        
        # Recursively check children's children (one level deep)
        for child in target_obj.children:
            for grandchild in child.children:
                if grandchild.type == 'ARMATURE':
                    return grandchild.name
        
        return "Unknown"

class ANIMPATH_PT_edit_panel(Panel):
    """Edit existing paths panel"""
    bl_label = "Manual Controls"
    bl_idname = "ANIMPATH_PT_edit_panel"
    bl_parent_id = "ANIMPATH_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        obj = context.active_object
        if obj and obj.get("is_animation_path"):
            box = layout.box()
            box.label(text="Manual Override Controls", icon='TOOL_SETTINGS')
            box.label(text="(Auto-sync preserves curve shape)", icon='INFO')
            
            col = box.column(align=True)
            col.operator("animpath.load_path_to_properties", text="Reload from Path", icon='IMPORT')
            col.operator("animpath.update_path", text="Force Update Path", icon='FILE_REFRESH')
            
            col.separator()
            col.label(text="Curve Editing:")
            col.operator("animpath.reset_curve_to_control_points", text="Reset Curve to Straight", icon='CURVE_BEZCURVE')
            
            col.separator()
            col.operator("animpath.delete_path", text="Delete Path", icon='TRASH')
            
        else:
            layout.label(text="Select an Animation Path", icon='INFO')
            layout.label(text="Properties will auto-sync when selected")

classes = [
    ANIMPATH_PT_main_panel,
    ANIMPATH_PT_animation_settings,
    ANIMPATH_PT_object_animation,
    ANIMPATH_PT_edit_panel,
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