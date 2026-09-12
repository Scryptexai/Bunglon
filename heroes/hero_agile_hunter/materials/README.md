# Materials

The active Lyra visual imports its authored Phase 5 PBR material groups directly
from both animated GLB packages:

- `M_Lyra_OpaqueAtlas`
- `M_Lyra_LumenEnergy`
- `M_Lyra_AuroraMantle`

Their embedded texture contract contains the authored albedo, normal,
metallic-roughness, emissive, and supporting maps. Godot’s glTF importer
extracts embedded images during project import; `HeroPresentationAdapter`
checks the imported material names and texture references before it accepts a
LOD candidate.

Gameplay code never constructs these materials and visual material changes may
never affect hit detection, damage, cooldowns, or projectile authority. Future
platform-specific compression (for example ETC2 or ASTC) belongs in Godot
import/export configuration after device validation, not in a procedural
runtime-material replacement.
