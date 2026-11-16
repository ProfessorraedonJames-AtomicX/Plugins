bl_info = {
    "name": "A.T.O.M.I.X. Engine — Universal Model & Bone Exporter (.geo.json)",
    "author": "AtomicX",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "File > Export > A.T.O.M.I.X. Model with Bones (.geo.json)",
    "description": "Exports Blender Armatures (bone hierarchy, pivots, rotations, sockets/locators) and bound Mesh cubes directly to Bedrock 1.12.0 .geo.json format for A.T.O.M.I.X. Engine",
    "category": "Import-Export",
}

import bpy
import json
import math
from mathutils import Vector, Matrix
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, IntProperty, FloatProperty, BoolProperty


def blender_to_bedrock_pos(vec, scale=16.0):
    """Converts Blender world coordinates (X-right, Y-back, Z-up in meters)
    to Bedrock model pixel coordinates (-X, Z, Y in 1/16th block pixels)."""
    return [
        round(-vec.x * scale, 4),
        round(vec.z * scale, 4),
        round(vec.y * scale, 4),
    ]


class ATOMIX_OT_export_geo_model(bpy.types.Operator, ExportHelper):
    """Export selected Armature (bones, cubes, and locators) to an A.T.O.M.I.X. .geo.json model file"""
    bl_idname = "atomix.export_geo_model"
    bl_label = "Export A.T.O.M.I.X. Model (.geo.json)"
    filename_ext = ".geo.json"

    filter_glob: StringProperty(default="*.geo.json;*.json", options={'HIDDEN'})

    geometry_identifier: StringProperty(
        name="Geometry Identifier",
        description="Bedrock geometry identifier (e.g. geometry.mymod.entity)",
        default="geometry.atomix.entity"
    )

    texture_width: IntProperty(
        name="Texture Width",
        description="UV texture width in pixels",
        default=64,
        min=16,
        max=4096
    )

    texture_height: IntProperty(
        name="Texture Height",
        description="UV texture height in pixels",
        default=64,
        min=16,
        max=4096
    )

    scale_to_pixels: FloatProperty(
        name="Units to Model Pixels",
        description="Multiplier from Blender units (meters) to Minecraft model pixels (16.0 = 1 meter is 16 pixels)",
        default=16.0,
        min=0.1,
        max=256.0
    )

    export_empties_as_locators: BoolProperty(
        name="Export Empties as Locators",
        description="Exports Empty objects parented to bones as Bedrock socket locators",
        default=True
    )

    def execute(self, context):
        # Find target Armature
        armature = context.active_object
        if not armature or armature.type != 'ARMATURE':
            armatures = [o for o in context.selected_objects if o.type == 'ARMATURE']
            armature = armatures[0] if armatures else None

        if not armature:
            self.report({'ERROR'}, "Please select an Armature object to export.")
            return {'CANCELLED'}

        scale = self.scale_to_pixels
        arm_mw = armature.matrix_world

        # Map bone names to cube list and locator dict
        bone_cubes = {b.name: [] for b in armature.data.bones}
        bone_locators = {b.name: {} for b in armature.data.bones}

        # Collect all meshes and empties associated with this armature
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                assigned_bone = None
                # 1. Direct bone parent
                if obj.parent == armature and obj.parent_type == 'BONE' and obj.parent_bone in bone_cubes:
                    assigned_bone = obj.parent_bone
                # 2. Armature modifier or object parent with vertex groups
                elif obj.parent == armature or any(m.type == 'ARMATURE' and m.object == armature for m in obj.modifiers):
                    if len(obj.vertex_groups) == 1 and obj.vertex_groups[0].name in bone_cubes:
                        assigned_bone = obj.vertex_groups[0].name
                    elif len(obj.vertex_groups) > 1:
                        # Split mesh by dominant vertex group per polygon/island or assign to primary bone
                        self._extract_weighted_mesh_boxes(obj, armature, bone_cubes, scale)
                        continue
                    elif armature.data.bones:
                        assigned_bone = armature.data.bones[0].name

                if assigned_bone:
                    cube_dict = self._mesh_to_cube(obj, scale)
                    if cube_dict:
                        bone_cubes[assigned_bone].append(cube_dict)

            elif self.export_empties_as_locators and obj.type == 'EMPTY':
                if obj.parent == armature and obj.parent_type == 'BONE' and obj.parent_bone in bone_locators:
                    world_pos = obj.matrix_world.translation
                    bone_locators[obj.parent_bone][obj.name] = blender_to_bedrock_pos(world_pos, scale)

        # Build Bedrock bones array in hierarchical order
        bones_list = []
        for bone in armature.data.bones:
            head_world = arm_mw @ bone.head_local
            pivot = blender_to_bedrock_pos(head_world, scale)

            bone_entry = {
                "name": bone.name,
                "pivot": pivot
            }
            if bone.parent:
                bone_entry["parent"] = bone.parent.name

            # Optional initial rest rotation stored in custom properties if present
            if "bedrock_rotation" in bone:
                rot = list(bone["bedrock_rotation"])
                if len(rot) == 3:
                    bone_entry["rotation"] = [round(float(x), 3) for x in rot]

            if bone_cubes[bone.name]:
                bone_entry["cubes"] = bone_cubes[bone.name]

            if bone_locators[bone.name]:
                bone_entry["locators"] = bone_locators[bone.name]

            bones_list.append(bone_entry)

        geo_json = {
            "format_version": "1.12.0",
            "minecraft:geometry": [
                {
                    "description": {
                        "identifier": self.geometry_identifier,
                        "texture_width": self.texture_width,
                        "texture_height": self.texture_height,
                        "visible_bounds_width": 4.0,
                        "visible_bounds_height": 4.0,
                        "visible_bounds_offset": [0.0, 1.5, 0.0]
                    },
                    "bones": bones_list
                }
            ]
        }

        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(geo_json, f, indent=2)

        self.report({'INFO'}, f"Exported A.T.O.M.I.X. model ({len(bones_list)} bones) to {self.filepath}")
        return {'FINISHED'}

    def _mesh_to_cube(self, obj, scale):
        mesh = obj.data
        if not mesh.vertices:
            return None

        mw = obj.matrix_world
        # Compute world-space bounding box of the mesh
        world_verts = [mw @ v.co for v in mesh.vertices]
        min_x = min(v.x for v in world_verts)
        max_x = max(v.x for v in world_verts)
        min_y = min(v.y for v in world_verts)
        max_y = max(v.y for v in world_verts)
        min_z = min(v.z for v in world_verts)
        max_z = max(v.z for v in world_verts)

        # In Bedrock: X is mirrored (-max_x is origin_x), Y is Blender Z, Z is Blender Y
        origin = [
            round(-max_x * scale, 4),
            round(min_z * scale, 4),
            round(min_y * scale, 4)
        ]
        size = [
            round(max(0.0, (max_x - min_x) * scale), 4),
            round(max(0.0, (max_z - min_z) * scale), 4),
            round(max(0.0, (max_y - min_y) * scale), 4)
        ]

        # Extract UV origin or per-face UVs if UV map exists
        uv_box = [0, 0]
        if mesh.uv_layers.active and mesh.uv_layers.active.data:
            uvs = [d.uv for d in mesh.uv_layers.active.data]
            min_u = min(uv.x for uv in uvs)
            max_v = max(uv.y for uv in uvs)
            uv_box = [
                int(round(min_u * self.texture_width)),
                int(round((1.0 - max_v) * self.texture_height))
            ]

        cube = {
            "origin": origin,
            "size": size,
            "uv": uv_box
        }
        if "inflate" in obj:
            cube["inflate"] = round(float(obj["inflate"]), 4)
        return cube

    def _extract_weighted_mesh_boxes(self, obj, armature, bone_cubes, scale):
        """Groups vertices by their highest-weight vertex group and builds a bounding cube per bone."""
        mesh = obj.data
        mw = obj.matrix_world
        group_names = {g.index: g.name for g in obj.vertex_groups}
        bone_verts = {}

        for v in mesh.vertices:
            best_group = None
            best_weight = 0.0
            for g in v.groups:
                gname = group_names.get(g.group)
                if gname in bone_cubes and g.weight > best_weight:
                    best_weight = g.weight
                    best_group = gname
            if best_group:
                bone_verts.setdefault(best_group, []).append(mw @ v.co)

        for bname, verts in bone_verts.items():
            if not verts:
                continue
            min_x = min(v.x for v in verts)
            max_x = max(v.x for v in verts)
            min_y = min(v.y for v in verts)
            max_y = max(v.y for v in verts)
            min_z = min(v.z for v in verts)
            max_z = max(v.z for v in verts)

            origin = [
                round(-max_x * scale, 4),
                round(min_z * scale, 4),
                round(min_y * scale, 4)
            ]
            size = [
                round(max(0.0, (max_x - min_x) * scale), 4),
                round(max(0.0, (max_z - min_z) * scale), 4),
                round(max(0.0, (max_y - min_y) * scale), 4)
            ]
            bone_cubes[bname].append({
                "origin": origin,
                "size": size,
                "uv": [0, 0]
            })


def menu_func_export_model(self, context):
    self.layout.operator(ATOMIX_OT_export_geo_model.bl_idname,
                         text="A.T.O.M.I.X. Model with Bones (.geo.json)")


def register():
    bpy.utils.register_class(ATOMIX_OT_export_geo_model)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export_model)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export_model)
    bpy.utils.unregister_class(ATOMIX_OT_export_geo_model)


if __name__ == "__main__":
    register()
