bl_info = {
    "name": "A.T.O.M.I.X. Engine — Universal Animation Exporter",
    "author": "AtomicX",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "File > Export > A.T.O.M.I.X. Universal Animation (.animation.json)",
    "description": "Exports Blender armature animations to universal A.T.O.M.I.X. / Bedrock animation JSON format (no combat phases)",
    "category": "Import-Export",
}

import bpy
import json
import math
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, FloatProperty, EnumProperty


class ATOMIX_OT_export_universal_animation(bpy.types.Operator, ExportHelper):
    """Export the active action to a universal A.T.O.M.I.X. .animation.json file"""
    bl_idname = "atomix.export_universal_animation"
    bl_label = "Export A.T.O.M.I.X. Universal Animation"
    filename_ext = ".animation.json"

    filter_glob: StringProperty(default="*.animation.json;*.json", options={'HIDDEN'})

    clip_name: StringProperty(
        name="Clip Identifier",
        description="Bedrock animation name, e.g. animation.entity.walk",
        default="animation.entity.walk"
    )

    loop_mode: EnumProperty(
        name="Loop Mode",
        items=[
            ('loop', "Loop", "Animation repeats continuously"),
            ('once', "Once", "Plays once and stops"),
            ('hold_on_last_frame', "Hold", "Freezes on the final frame")
        ],
        default='loop'
    )

    sample_rate: FloatProperty(
        name="Sample Interval (s)",
        description="Time step in seconds between exported keyframes (0.0416 for 24 FPS, 0.05 for 20 FPS)",
        default=0.05,
        min=0.01,
        max=0.5
    )

    export_custom_markers: BoolProperty(
        name="Export Sound / Particle Markers",
        description="Export Blender timeline markers as custom/sound/particle timeline events",
        default=True
    )

    scale_to_pixels: FloatProperty(
        name="Units to Model Pixels",
        description="Multiplier from Blender units (meters) to Minecraft model pixels (16)",
        default=16.0
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an Armature object to export.")
            return {'CANCELLED'}

        armature = obj
        scene = context.scene
        fps = scene.render.fps / scene.render.fps_base

        start_frame = scene.frame_start
        end_frame = scene.frame_end
        duration = max(0.0, (end_frame - start_frame) / fps)

        anim_data = {
            "format_version": "1.8.0",
            "animations": {
                self.clip_name: {
                    "animation_length": round(duration, 4),
                    "loop": True if self.loop_mode == 'loop' else (self.loop_mode if self.loop_mode == 'hold_on_last_frame' else False),
                    "bones": {}
                }
            }
        }
        clip = anim_data["animations"][self.clip_name]

        if self.export_custom_markers and scene.timeline_markers:
            timeline_events = {}
            for marker in scene.timeline_markers:
                if start_frame <= marker.frame <= end_frame:
                    marker_time = round((marker.frame - start_frame) / fps, 4)
                    time_key = f"{marker_time:.4f}".rstrip('0').rstrip('.') or "0.0"
                    timeline_events[time_key] = marker.name
            if timeline_events:
                clip["timeline"] = timeline_events

        bones_dict = clip["bones"]
        for pbone in armature.pose.bones:
            bones_dict[pbone.name] = {
                "rotation": {},
                "position": {},
                "scale": {}
            }

        current_frame = float(start_frame)
        step_frames = max(1.0, self.sample_rate * fps)
        orig_frame = scene.frame_current

        try:
            while current_frame <= end_frame + 1e-4:
                scene.frame_set(int(current_frame), subframe=current_frame - int(current_frame))
                context.view_layer.update()

                t = round((current_frame - start_frame) / fps, 4)
                time_key = f"{t:.4f}".rstrip('0').rstrip('.') or "0.0"

                for pbone in armature.pose.bones:
                    bone_channels = bones_dict[pbone.name]
                    mat_local = pbone.matrix_basis
                    loc, rot_quat, scl = mat_local.decompose()

                    euler = rot_quat.to_euler('ZYX')
                    rot_deg = [
                        round(-math.degrees(euler.x), 2),
                        round(-math.degrees(euler.y), 2),
                        round(math.degrees(euler.z), 2)
                    ]

                    pos_px = [
                        round(-loc.x * self.scale_to_pixels, 3),
                        round(loc.z * self.scale_to_pixels, 3),
                        round(loc.y * self.scale_to_pixels, 3)
                    ]

                    scl_val = [round(scl.x, 3), round(scl.z, 3), round(scl.y, 3)]

                    bone_channels["rotation"][time_key] = rot_deg
                    bone_channels["position"][time_key] = pos_px
                    bone_channels["scale"][time_key] = scl_val

                current_frame += step_frames
        finally:
            scene.frame_set(orig_frame)

        for bname in list(bones_dict.keys()):
            bdata = bones_dict[bname]
            if all(v == [0.0, 0.0, 0.0] for v in bdata["rotation"].values()):
                del bdata["rotation"]
            if all(v == [0.0, 0.0, 0.0] for v in bdata["position"].values()):
                del bdata["position"]
            if all(v == [1.0, 1.0, 1.0] for v in bdata["scale"].values()):
                del bdata["scale"]
            if not bdata:
                del bones_dict[bname]

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(anim_data, f, indent=2)

        self.report({'INFO'}, f"Exported A.T.O.M.I.X. universal animation to {self.filepath}")
        return {'FINISHED'}


def menu_func_export(self, context):
    self.layout.operator(ATOMIX_OT_export_universal_animation.bl_idname,
                         text="A.T.O.M.I.X. Universal Animation (.animation.json)")


def register():
    bpy.utils.register_class(ATOMIX_OT_export_universal_animation)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(ATOMIX_OT_export_universal_animation)


if __name__ == "__main__":
    register()
