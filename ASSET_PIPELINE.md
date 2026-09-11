# ASSET PIPELINE — Lyra Vesper

This is the authoritative asset pipeline for the 3D Hero Production Roadmap V1. It supersedes any implication that runtime primitive meshes can be a final hero.

## Phase 2 handoff status

The current authored handoff is [`character_final/lyra_vesper_phase2.glb`](character_final/lyra_vesper_phase2.glb). It is a valid non-primitive mesh/material package with provisional source textures. The `lyra_vesper_final.glb` name below remains reserved for the post-Phase-3 optimized, UV-reviewed asset; no Phase 2 file is misrepresented as mobile-final.

## Asset source of truth

| Layer | Canonical source | Deliverable used by Godot |
|---|---|---|
| Design | Original turnaround/reference sheet | PNG reference package in `concept/` |
| Modeling / rig / animation | Blender `.blend` source | `lyra_vesper_final.glb` |
| Texturing | Blender-compatible PBR texture source | PNG/KTX2/engine-imported texture assets |
| VFX | Godot scenes/shaders/flipbooks | pooled VFX scenes under `vfx/` |
| Audio | WAV masters and localized VO | WAV/OGG files under `audio/` |
| Balance | Godot `.tres` resources | `data/` resources |

## 1. Phase 1 reference package

The concept folder must contain these individual, reviewable files:

```text
concept/
├── lyra_turnaround_front.png
├── lyra_turnaround_back.png
├── lyra_turnaround_left.png
├── lyra_turnaround_right.png
├── lyra_three_quarter_front.png
├── lyra_three_quarter_back.png
├── lyra_face_sheet.png
├── lyra_weapon_sheet.png
└── lyra_costume_details.png
```

All views use one fixed proportion guide. The bow silhouette, left-side aurora mantle, ponytail, visor, and diamond chest core are mandatory recognition anchors.

## 2. Mesh and topology specification

### Final mesh composition

- Head and facial plane mesh; no featureless mannequin face.
- Athletic torso/body with closed underside/back geometry.
- Separate or cleanly segmented lightweight armor and suit panels.
- Five-finger hands when camera distance/animation need supports it; reduced finger geometry is acceptable only if silhouette/deformation remains clean.
- Boots, hair/ponytail, aurora mantle, quiver, accessories, and a separate energy-bow mesh.
- No `BoxMesh`, `SphereMesh`, `CapsuleMesh`, `CylinderMesh`, or unmodified primitive node in the final imported character hierarchy.

### Mobile budgets

| Asset | LOD0 target | LOD1 target | Notes |
|---|---:|---:|---|
| Hero + attached costume | 10k–16k triangles | 5k–8k triangles | Spend density on face, bow outline, hands, and mantle edge. |
| Energy bow | 1k–2k triangles | 500–900 triangles | Keep string/socket readable. |
| Hair + secondary silhouette | 1.5k–3k triangles | 700–1.5k triangles | Prefer cards/clean chunks where appropriate. |
| Bones | ≤ 55 deform bones | same | Helper/socket bones do not need skin weights. |
| Materials | 3–5 | 3–5 | Minimize draw calls. |

LOD2 is optional and should be added only if profiling shows multiple heroes significantly impact frame time.

## 3. UV and PBR texture package

Target one 1024² body/armor atlas and one 512² weapon atlas at the standard quality tier. Higher source-resolution painting is allowed; runtime texture output is determined per device tier.

```text
textures/
├── lyra_body_basecolor.png
├── lyra_body_normal.png
├── lyra_body_orm.png              # occlusion, roughness, metallic
├── lyra_body_emission.png
├── lyra_weapon_basecolor.png
├── lyra_weapon_normal.png
├── lyra_weapon_orm.png
└── lyra_weapon_emission.png
```

Material groups:

1. skin / face;
2. suit + armor atlas;
3. bow metal/leather;
4. opaque emissive energy;
5. optional transparent mantle only if its mobile overdraw is acceptable.

## 4. Rig, sockets, and export rules

### Required deform skeleton

```text
root
└── pelvis
    └── spine_01 → spine_02 → chest → neck → head
        ├── clavicle_l → upperarm_l → lowerarm_l → hand_l → fingers_l
        └── clavicle_r → upperarm_r → lowerarm_r → hand_r → fingers_r
    ├── thigh_l → calf_l → foot_l → toe_l
    └── thigh_r → calf_r → foot_r → toe_r
```

Secondary bones are limited to ponytail and mantle only where animation quality demands them. Export a stable naming map if a DCC naming convention differs from the Godot adapter.

### Required helpers

- `socket_weapon` — bow attachment.
- `socket_projectile` — exact projectile release origin.
- `socket_camera_body`, `socket_camera_chest`, `socket_camera_head`, `socket_aim` — camera and targeting anchors, or a documented mapping to Godot markers.

### GLB export settings

- Apply transforms; use meters.
- Use a `-Z` forward convention verified in Godot.
- Bake constraints and animations.
- Export normals/tangents and skin weights.
- Export actions as named clips; remove unused test actions.
- Avoid embedded source-only collections, blockout primitives, and unused materials.

## 5. Animation package naming

```text
animations/
├── idle
├── idle_variation
├── walk
├── run
├── turn_left
├── turn_right
├── start_run
├── stop_run
├── basic_attack
├── basic_attack_recovery
├── hit_light
├── hit_heavy
├── death
├── skill_01
├── skill_02
├── skill_03
├── ultimate
├── spawn
└── victory
```

Animation timing must export alongside a small manifest documenting semantic frame/event times: weapon draw, projectile release, dash start/end, hit window, and recovery unlock. Godot should consume event names rather than hard-coded frame numbers where possible.

## 6. Godot import and release checks

1. Import the final GLB into a clean Godot 4.x project.
2. Confirm all material slots, textures, skin, skeleton, and named clips appear without missing dependency warnings.
3. Instance the imported visual under the hero gameplay scene.
4. Bind sockets/markers and run every animation in an animation preview scene.
5. Inspect 360° at gameplay camera distance and close-up.
6. Profile the actual imported mesh—not an editor-only source scene—on representative Android hardware.

## Prohibited final-asset shortcuts

- Ship primitive GeometryInstance nodes as a hero model.
- Use a generic mannequin with only a color swap.
- Use concept art as a billboard instead of a mesh.
- Let visual mesh collision perform combat hit detection.
- Hide missing back/side geometry with camera placement.
