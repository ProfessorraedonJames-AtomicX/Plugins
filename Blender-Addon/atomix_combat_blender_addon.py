bl_info = {
    "name": "A.T.O.M.I.X. Combat — Universal Fighting Animation & Moveset Tools",
    "author": "AtomicX",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > AtomiX Combat | File > Export > A.T.O.M.I.X. Combat Animation",
    "description": "Authors universal fighting animations (windup, strike, recover, parry, hitstop) and exports combat movesets for any entity or custom entity",
    "category": "Animation",
}

import bpy
import json
import math
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty, EnumProperty


class ATOMIXCOMBAT_OT_insert_phase(bpy.types.Operator):
    """Insert an A.T.O.M.I.X. Combat phase marker at the current frame"""
    bl_idname = "atomixcombat.insert_phase"
    bl_label = "Insert Combat Phase Marker"

    phase_type: EnumProperty(
        name="Phase",
        items=[
            ('phase:windup', "Windup (Startup)", "Attack startup window before hitbox is active"),
            ('phase:strike', "Strike (Active Hitbox)", "Active damage window where weapon/limb hitboxes sweep"),
            ('phase:hitstop', "Hit-Stop (Impact Freeze)", "Impact freeze-frame trigger"),
            ('phase:recover', "Recover (Combo / Cancel)", "Recovery window where next combo input buffer triggers"),
            ('phase:parry', "Parry (Deflection Window)", "Active parry deflection window"),
            ('phase:neutral', "Neutral (End)", "Returns fighter to neutral state")
        ],
        default='phase:strike'
    )

    def execute(self, context):
        scene = context.scene
        frame = scene.frame_current
        marker = scene.timeline_markers.new(name=self.phase_type, frame=frame)
        self.report({'INFO'}, f"Inserted {marker.name} at frame {frame}")
        return {'FINISHED'}


class ATOMIXCOMBAT_OT_export_fighting_animation(bpy.types.Operator, ExportHelper):
    """Export fighting animation (.animation.json) and optional .pack.json moveset mapping for any entity or custom entity"""
    bl_idname = "atomixcombat.export_fighting_animation"
    bl_label = "Export A.T.O.M.I.X. Fighting Animation"
    filename_ext = ".animation.json"

    filter_glob: StringProperty(default="*.animation.json;*.json", options={'HIDDEN'})

    target_entity: StringProperty(
        name="Target Entity / Model ID",
        description="Universal entity or custom model ID (e.g. minecraft:player, mymod:knight, mymod:giant_ant)",
        default="mymod:fighter"
    )

    clip_name: StringProperty(
        name="Combat Clip Name",
        description="Bedrock animation clip identifier (e.g. animation.fighter.slash_1)",
        default="animation.fighter.slash_1"
    )

    state_name: StringProperty(
        name="Combat State Key",
        description="Logical state name used by CombatMoveset / ComboNode (e.g. slash_1, heavy_slam, dodge_roll)",
        default="slash_1"
    )

    root_motion: BoolProperty(
        name="Enable Root Motion Lunge",
        description="Extract forward lunge/roll displacement from the root bone",
        default=True
    )

    export_pack_json: BoolProperty(
        name="Also Export .pack.json",
        description="Generate a companion .pack.json file alongside the animation file",
        default=True
    )

    sample_rate: FloatProperty(
        name="Sample Interval (s)",
        default=0.0416,
        min=0.01,
        max=0.25
    )

    scale_to_pixels: FloatProperty(
        name="Units to Model Pixels",
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
                    "loop": False,
                    "bones": {}
                }
            }
        }
        clip = anim_data["animations"][self.clip_name]

        timeline_events = {}
        for marker in sorted(scene.timeline_markers, key=lambda m: m.frame):
            if start_frame <= marker.frame <= end_frame:
                marker_time = round((marker.frame - start_frame) / fps, 4)
                time_key = f"{marker_time:.4f}".rstrip('0').rstrip('.') or "0.0"
                timeline_events[time_key] = marker.name

        if not timeline_events:
            # Auto-populate default combat phases if animator forgot markers
            t_windup = "0.0"
            t_strike = f"{round(duration * 0.25, 3):.3f}".rstrip('0').rstrip('.') or "0.1"
            t_recover = f"{round(duration * 0.60, 3):.3f}".rstrip('0').rstrip('.') or "0.3"
            timeline_events[t_windup] = "phase:windup"
            timeline_events[t_strike] = "phase:strike"
            timeline_events[t_recover] = "phase:recover"

        clip["timeline"] = timeline_events

        bones_dict = clip["bones"]
        for pbone in armature.pose.bones:
            bones_dict[pbone.name] = {"rotation": {}, "position": {}, "scale": {}}

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

        if self.export_pack_json:
            pack_path = self.filepath.replace(".animation.json", ".pack.json")
            if pack_path == self.filepath:
                pack_path = self.filepath + ".pack.json"
            ns = self.target_entity.split(":")[0] if ":" in self.target_entity else "mymod"
            pack_data = {
                "target": self.target_entity,
                "priority": 20,
                "states": {
                    self.state_name: {
                        "file": f"{ns}:combat_moves",
                        "clip": self.clip_name,
                        "fade": 0.08,
                        "speed": 1.0,
                        "root_motion": self.root_motion
                    }
                }
            }
            with open(pack_path, 'w', encoding='utf-8') as pf:
                json.dump(pack_data, pf, indent=2)

        self.report({'INFO'}, f"Exported A.T.O.M.I.X. Combat animation to {self.filepath}")
        return {'FINISHED'}


class ATOMIXCOMBAT_PT_sidebar(bpy.types.Panel):
    bl_label = "AtomiX Combat Tools"
    bl_idname = "ATOMIXCOMBAT_PT_sidebar"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AtomiX Combat"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Combat Timeline Phases:")
        col = layout.column(align=True)
        for code, label in [
            ('phase:windup', "1. Windup (Startup)"),
            ('phase:strike', "2. Strike (Hitbox Active)"),
            ('phase:hitstop', "3. Hit-Stop (Impact Freeze)"),
            ('phase:recover', "4. Recover (Combo Cancel)"),
            ('phase:parry', "5. Parry (Deflect Window)"),
            ('phase:neutral', "6. Neutral (End)")
        ]:
            op = col.operator("atomixcombat.insert_phase", text=label)
            op.phase_type = code

        layout.separator()
        layout.operator("atomixcombat.export_fighting_animation", icon='EXPORT')


def menu_func_export(self, context):
    self.layout.operator(ATOMIXCOMBAT_OT_export_fighting_animation.bl_idname,
                         text="A.T.O.M.I.X. Combat Fighting Animation (.animation.json)")


classes = (
    ATOMIXCOMBAT_OT_insert_phase,
    ATOMIXCOMBAT_OT_export_fighting_animation,
    ATOMIXCOMBAT_PT_sidebar,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
