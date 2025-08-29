from typing import Union, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum
import math
import bpy
import bmesh
from mathutils import Vector
from bpy_extras.object_utils import AddObjectHelper


class AnimationPath:
    """Manages animated movement paths with pose blending."""
    
    def __init__(self, start_pos, start_frame, end_pos, end_frame, 
                 start_pose, end_pose, anim, start_blend_frames=0, end_blend_frames=0, anim_speed_mult=1.0):
        self.start_pos = Vector(start_pos) if not isinstance(start_pos, Vector) else start_pos
        self.start_frame = start_frame
        self.end_pos = Vector(end_pos) if not isinstance(end_pos, Vector) else end_pos
        self.end_frame = end_frame
        self.start_pose = start_pose
        self.end_pose = end_pose
        self.anim = anim
        self.start_blend_frames = start_blend_frames
        self.end_blend_frames = end_blend_frames
        self.anim_speed_mult = anim_speed_mult
        
        if start_frame >= end_frame:
            raise ValueError("start_frame must be less than end_frame")
        
        total_frames = end_frame - start_frame
        if start_blend_frames + end_blend_frames > total_frames:
            raise ValueError("Blend frames cannot exceed total path duration")
    
    @property
    def duration(self):
        return self.end_frame - self.start_frame
    
    @property
    def main_anim_start_frame(self):
        return self.start_frame + self.start_blend_frames
    
    @property
    def main_anim_end_frame(self):
        return self.end_frame - self.end_blend_frames
    
    @property
    def main_anim_duration(self):
        return self.main_anim_end_frame - self.main_anim_start_frame
    
    def get_position_at_frame(self, frame):
        if frame <= self.start_frame:
            return self.start_pos.copy()
        elif frame >= self.end_frame:
            return self.end_pos.copy()
        
        t = (frame - self.start_frame) / self.duration
        return self.start_pos.lerp(self.end_pos, t)
    
    def get_animation_state_at_frame(self, frame):
        """Returns: (current_animation, blend_factor)"""
        if frame < self.start_frame:
            return (self.start_pose, 1.0)
        elif frame > self.end_frame:
            return (self.end_pose, 1.0)
        elif frame < self.main_anim_start_frame:
            blend_progress = (frame - self.start_frame) / self.start_blend_frames
            return ((self.start_pose, self.anim), blend_progress)
        elif frame <= self.main_anim_end_frame:
            return (self.anim, 1.0)
        else:
            blend_progress = (frame - self.main_anim_end_frame) / self.end_blend_frames
            return ((self.anim, self.end_pose), blend_progress)
    
    def is_active_at_frame(self, frame):
        return self.start_frame <= frame <= self.end_frame
    
    def create_blender_curve(self, name="AnimationPath"):
        parent_empty = bpy.data.objects.new(f"LAA_Path_{name}", None)
        parent_empty.empty_display_type = 'PLAIN_AXES'
        parent_empty.empty_display_size = 0.1
        parent_empty["is_laa_path_parent"] = True
        parent_empty["animation_path_name"] = name
        bpy.context.collection.objects.link(parent_empty)
        
        curve_data = bpy.data.curves.new(name, 'CURVE')
        curve_data.dimensions = '3D'
        curve_data.resolution_u = 8
        curve_data.bevel_depth = 0.01
        curve_data.use_path = True
        curve_data.path_duration = self.duration
        
        spline = curve_data.splines.new('NURBS')
        spline.points.add(4)
        spline.order_u = 4
        spline.use_endpoint_u = True
        
        direction = self.end_pos - self.start_pos
        for i in range(5):
            t = i / 4.0
            if i == 0:
                pos = self.start_pos
            elif i == 4:
                pos = self.end_pos
            else:
                pos = self.start_pos + direction * t
            spline.points[i].co = (pos.x, pos.y, pos.z, 1.0)
        
        curve_obj = bpy.data.objects.new(name, curve_data)
        curve_obj.color = (0.2, 0.8, 1.0, 1.0)
        curve_obj.show_wire = False
        curve_obj.hide_render = True
        
        curve_obj["start_frame"] = self.start_frame
        curve_obj["end_frame"] = self.end_frame
        curve_obj["start_pose"] = self.start_pose
        curve_obj["end_pose"] = self.end_pose
        curve_obj["anim"] = self.anim
        curve_obj["start_blend_frames"] = self.start_blend_frames
        curve_obj["end_blend_frames"] = self.end_blend_frames
        curve_obj["anim_speed_mult"] = self.anim_speed_mult
        curve_obj["is_animation_path"] = True
        curve_obj["laa_path_parent"] = parent_empty.name
        
        bpy.context.collection.objects.link(curve_obj)
        curve_obj.parent = parent_empty
        
        return curve_obj
    
    def create_control_points(self, curve_obj):
        """Create start and end control point empties"""
        control_points = []
        
        parent_empty_name = curve_obj.get("laa_path_parent")
        parent_empty = bpy.data.objects.get(parent_empty_name) if parent_empty_name else None
        
        if not parent_empty:
            parent_empty = bpy.data.objects.new(f"LAA_Path_{curve_obj.name}", None)
            parent_empty.empty_display_type = 'PLAIN_AXES'
            parent_empty.empty_display_size = 0.1
            parent_empty["is_laa_path_parent"] = True
            parent_empty["animation_path_name"] = curve_obj.name
            bpy.context.collection.objects.link(parent_empty)
            curve_obj["laa_path_parent"] = parent_empty.name
            curve_obj.parent = parent_empty
        
        points_data = [
            ("start", self.start_pos, self.start_pose, self.start_frame, 0.05, (0.0, 1.0, 0.0, 1.0)),
            ("end", self.end_pos, self.end_pose, self.end_frame, 0.05, (1.0, 0.0, 0.0, 1.0))
        ]
        
        for point_name, pos, pose, frame, size, color in points_data:
            empty = bpy.data.objects.new(f"{curve_obj.name}_{point_name}", None)
            empty.empty_display_type = 'SPHERE'
            empty.empty_display_size = size
            empty.location = pos
            empty.color = color
            empty.show_wire = True
            
            empty["animation_path_parent"] = curve_obj.name
            empty["control_point_type"] = point_name
            empty["pose"] = pose
            empty["frame"] = frame
            empty["laa_path_parent"] = parent_empty.name
            
            bpy.context.collection.objects.link(empty)
            empty.parent = parent_empty
            
            if point_name == "start":
                curve_obj["start_control_point"] = empty.name
            elif point_name == "end":
                curve_obj["end_control_point"] = empty.name
            
            control_points.append(empty)
        
        return control_points

    def update_curve_from_control_points(self, curve_obj):
        """Update curve geometry from control point positions - ONLY call manually"""
        control_points = {}
        
        start_point_name = curve_obj.get("start_control_point")
        end_point_name = curve_obj.get("end_control_point")
        
        if start_point_name:
            start_obj = bpy.data.objects.get(start_point_name)
            if start_obj:
                control_points["start"] = start_obj.location.copy()
        
        if end_point_name:
            end_obj = bpy.data.objects.get(end_point_name)
            if end_obj:
                control_points["end"] = end_obj.location.copy()
        
        if len(control_points) < 2:
            raise ValueError("Need start and end control points to update curve")
        
        curve_data = curve_obj.data
        spline = curve_data.splines[0]
        
        start_pos = control_points.get("start", self.start_pos)
        end_pos = control_points.get("end", self.end_pos)
        direction = end_pos - start_pos
        
        # **ONLY update curve geometry when explicitly called**
        # This prevents automatic resetting to straight lines
        for i in range(5):
            t = i / 4.0
            if i == 0:
                pos = start_pos
            elif i == 4:
                pos = end_pos
            else:
                pos = start_pos + direction * t
            spline.points[i].co = (pos.x, pos.y, pos.z, 1.0)
        
        # Update internal positions only if control points moved
        if "start" in control_points:
            self.start_pos = control_points["start"]
        if "end" in control_points:
            self.end_pos = control_points["end"]
    
    def update_positions_from_control_points(self, curve_obj):
        """Update internal positions from control points WITHOUT modifying curve geometry"""
        start_point_name = curve_obj.get("start_control_point")
        end_point_name = curve_obj.get("end_control_point")
        
        if start_point_name:
            start_obj = bpy.data.objects.get(start_point_name)
            if start_obj:
                self.start_pos = start_obj.location.copy()
        
        if end_point_name:
            end_obj = bpy.data.objects.get(end_point_name)
            if end_obj:
                self.end_pos = end_obj.location.copy()
    
    def get_position_from_curve(self, curve_obj, frame):
        """Get position along curve at specific frame"""
        if not curve_obj or not curve_obj.data.splines:
            return self.get_position_at_frame(frame)
        
        t = (frame - self.start_frame) / self.duration
        t = max(0.0, min(1.0, t))
        
        spline = curve_obj.data.splines[0]
        if len(spline.points) >= 5:
            point_index = t * (len(spline.points) - 1)
            index = int(point_index)
            frac = point_index - index
            
            if index >= len(spline.points) - 1:
                return Vector(spline.points[-1].co[:3])
            
            p1 = Vector(spline.points[index].co[:3])
            p2 = Vector(spline.points[index + 1].co[:3])
            return p1.lerp(p2, frac)
        
        return self.get_position_at_frame(frame)
    
    def __repr__(self):
        return (f"AnimationPath(start_pos={self.start_pos}, start_frame={self.start_frame}, "
                f"end_pos={self.end_pos}, end_frame={self.end_frame}, "
                f"start_pose={self.start_pose}, end_pose={self.end_pose}, "
                f"anim={self.anim}, start_blend_frames={self.start_blend_frames}, "
                f"end_blend_frames={self.end_blend_frames}, "
                f"anim_speed_mult={self.anim_speed_mult})")


def create_animation_path_from_properties(context):
    """Create AnimationPath from Blender scene properties"""
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
        end_blend_frames=props.end_blend_frames,
        anim_speed_mult=props.anim_speed_mult
    )
    
    return path