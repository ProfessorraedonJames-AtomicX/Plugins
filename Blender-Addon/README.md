# A.T.O.M.I.X. Blender Add-on Suite (Model + Bones, Universal Animation & Combat Animation)

This package includes 3 dedicated Python scripts for Blender (3.6+ / 4.0+ / 5.0+):

1. `atomix_model_exporter.py` — **Model & Bone Exporter (`.geo.json`)**:
   - Exports your Blender `ARMATURE` bone hierarchy, pivots, rest rotations, bound mesh cubes (via bone parenting or vertex groups), and `EMPTY` socket locators directly to Bedrock 1.12.0 `.geo.json` format.
   - Menu: **File > Export > A.T.O.M.I.X. Model with Bones (.geo.json)**

2. `atomix_blender_addon.py` — **AtomiX Engine Universal Animation Exporter (`.animation.json`)**:
   - Exports universal non-combat skeletal animations (idle, walk, run, fly, swim, emotes, machinery) to `.animation.json`.
   - Menu: **File > Export > A.T.O.M.I.X. Universal Animation (.animation.json)**

3. `atomix_combat_blender_addon.py` — **AtomiX Combat Fighting Animation & Moveset Tools**:
   - Adds the **AtomiX Combat** sidebar panel in the 3D Viewport (press `N`) to insert fighting phase markers (`phase:windup`, `phase:strike`, `phase:hitstop`, `phase:recover`, `phase:parry`, `phase:neutral`) and export universal fighting animations + `.pack.json` movesets for any entity or custom entity.
   - Menu: **File > Export > A.T.O.M.I.X. Combat Fighting Animation (.animation.json)**

## Installation
1. In Blender, go to **Edit > Preferences > Add-ons**.
2. Click **Install...** and select each `.py` file (`atomix_model_exporter.py`, `atomix_blender_addon.py`, `atomix_combat_blender_addon.py`).
3. Check the boxes to enable all three add-ons.
