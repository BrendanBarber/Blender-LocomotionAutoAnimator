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
except ImportError:
    import properties

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
        
        box = layout.box()
        box.label(text="Animation Path Creator", icon='CURVE_PATH')
        
        col = box.column(align=True)
        col.label(text="Set Positions:", icon='CURSOR')
        
        row = col.row(align=True)
        row.operator("animpath.set_start_position", text="Set Start", icon='PLUS')
        row.operator("animpath.set_end_position", text="Set End", icon='PLUS')
        
        if any(props.start_pos) or any(props.end_pos):
            col.separator()
            col.label(text="Current Positions:")
            col.label(text=f"Start: {props.start_pos[0]:.2f}, {props.start_pos[1]:.2f}, {props.start_pos[2]:.2f}")
            col.label(text=f"End: {props.end_pos[0]:.2f}, {props.end_pos[1]:.2f}, {props.end_pos[2]:.2f}")
        
        col.separator()
        col.label(text="Target Object:", icon='OBJECT_DATA')
        
        row = col.row(align=True)
        row.prop(props, "target_object", text="")
        row.operator("animpath.set_target_object", text="", icon='EYEDROPPER')
        
        if props.target_object:
            col.label(text=f"Target: {props.target_object.name}", icon='CHECKMARK')
        
        col.separator()
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
                    
                    use_rotation = obj.get("use_rotation", True)
                    col.label(text=f"Align to Path: {'Yes' if use_rotation else 'No'}")
                    
                    col.separator()
                    col.operator("animpath.animate_object_along_path", 
                               text="Animate Object Along Path", icon='PLAY')
                    
                    start_frame = obj.get("start_frame", 1)
                    end_frame = obj.get("end_frame", 100)
                    col.label(text=f"Frames: {start_frame} - {end_frame}")
                    
                else:
                    box.label(text=f"⚠ Target object '{target_obj_name}' not found", icon='ERROR')
            else:
                box.label(text="No target object assigned", icon='INFO')
                box.label(text="Set target in properties above")
        
        else:
            layout.label(text="Select an Animation Path", icon='INFO')
            layout.label(text="to animate an object along it")

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
            box.label(text="(Auto-sync is active)", icon='INFO')
            
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

class ANIMPATH_PT_control_points_panel(Panel):
    """Control points information panel"""
    bl_label = "Control Points"
    bl_idname = "ANIMPATH_PT_control_points_panel"
    bl_parent_id = "ANIMPATH_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        
        if obj and obj.get("control_point_type"):
            box = layout.box()
            point_type = obj.get("control_point_type")
            box.label(text=f"Control Point: {point_type.title()}", icon='EMPTY_AXIS')
            
            col = box.column(align=True)
            col.label(text="Properties:")
            col.label(text=f"Type: {point_type}")
            if obj.get("frame"):
                col.label(text=f"Frame: {obj.get('frame', 'N/A')}")
            col.label(text=f"Pose: {obj.get('pose', 'N/A')}")
            col.label(text=f"Position: [{obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f}]")
            
            col.separator()
            col.label(text="Move this point to adjust curve shape", icon='INFO')
            col.label(text="Position auto-syncs with properties panel")
            
        elif obj and obj.get("is_animation_path"):
            box = layout.box()
            box.label(text="Path Control Points:", icon='CURVE_PATH')
            
            control_points = [child for child in obj.children if child.get("control_point_type")]
            
            if control_points:
                col = box.column(align=True)
                col.label(text="Available Control Points:")
                
                point_order = ["start", "end"]
                sorted_points = []
                for point_name in point_order:
                    for ctrl in control_points:
                        if ctrl.get("control_point_type") == point_name:
                            sorted_points.append(ctrl)
                            break
                
                for ctrl in sorted_points:
                    row = col.row()
                    point_type = ctrl.get("control_point_type", "unknown")
                    pose = ctrl.get("pose", "N/A")
                    
                    if point_type == "start":
                        row.label(text=f"🟢 Start: {pose}")
                    elif point_type == "end":
                        row.label(text=f"🔴 End: {pose}")
                    else:
                        row.label(text=f"{point_type.title()}: {pose}")
                
                col.separator()
                col.label(text="Instructions:", icon='INFO')
                col.label(text="• Control points auto-sync with properties")
                col.label(text="• Move points to adjust curve shape")
                col.label(text="• Changes update properties panel")
                col.label(text="• Use 'Animate Object Along Path'")
                col.label(text="  to apply movement to target object")
                
            else:
                box.label(text="No control points found")
        
        else:
            layout.label(text="Select a path or control point", icon='INFO')
            layout.separator()
            layout.label(text="Control Point Colors:")
            layout.label(text="🟢 Start point (green)")
            layout.label(text="🔴 End point (red)")
            layout.separator()
            layout.label(text="Workflow:")
            layout.label(text="1. Create animation path")
            layout.label(text="2. Assign target object")
            layout.label(text="3. Properties auto-sync when selected")
            layout.label(text="4. Animate object along path")

classes = [
    ANIMPATH_PT_main_panel,
    ANIMPATH_PT_animation_settings,
    ANIMPATH_PT_object_animation,
    ANIMPATH_PT_edit_panel,
    ANIMPATH_PT_control_points_panel,
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