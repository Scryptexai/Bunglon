# ASSET PIPELINE — Lyra Vesper

This is the authoritative asset pipeline for the 3D Hero Production Roadmap V1. It supersedes any implication that runtime primitive meshes can be a final hero.

## Phase 2–4 handoff status

The authored source handoff remains [`character_final/lyra_vesper_phase2.glb`](character_final/lyra_vesper_phase2.glb). It is preserved as the detailed non-primitive source package. Phase 3 provides its runtime-ready derived companions: [`character_optimized/lyra_vesper_optimized.glb`](character_optimized/lyra_vesper_optimized.glb) (LOD0) and [`character_lod/lyra_vesper_lod1.glb`](character_lod/lyra_vesper_lod1.glb).

The Phase 3 package has 11,496 LOD0 triangles, 5,843 LOD1 triangles, three material/draw groups, packed UVs, normal maps, MikkTSpace tangents, and a documented selection policy. Phase 4 now provides matching skinned derivatives: [`character_rigged/lyra_vesper_rigged.glb`](character_rigged/lyra_vesper_rigged.glb) and [`character_rigged/lyra_vesper_rigged_lod1.glb`](character_rigged/lyra_vesper_rigged_lod1.glb). Each retains the Phase 3 material/mesh contract and contains 48 deform joints, 54 palette joints, standard normalized weights, inverse-bind matrices, and six named attachment helpers. See [`character_rigged/README.md`](character_rigged/README.md) and [`character_rigged/PHASE_4_QA.md`](character_rigged/PHASE_4_QA.md) for measurable skinning evidence. It is rigged—not a false claim that the Phase 5 animation set or real Godot import validation has happened.

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
| Skin palette | ≤ 55 joints | same | Phase 4 uses 48 deform joints + 6 helper joints; helpers have no vertex weights. |
| Materials | 3–5 | 3–5 | Minimize draw calls. |

LOD2 is optional and should be added only if profiling shows multiple heroes significantly impact frame time.

**Validated Phase 3 outcome:** LOD0 is 11,496 triangles and LOD1 is 5,843 triangles, both use three runtime material/draw groups. The P3 geometry retains the complete character/bow/mantle asset rather than using a body-only or billboard LOD. Device profiling still owns the final threshold/quality-tier adjustment.

## 3. UV and PBR texture package

The validated Phase 3 standard tier uses a 1024² opaque body/armor/hair atlas (base color, ORM, and emission) with a 512² microdetail normal map, plus 512² energy and mantle map families. Higher source-resolution painting is allowed; runtime texture output is determined per device tier.

```text
character_optimized/textures/
├── lyra_mobile_opaque_basecolor.png   # 1024², embedded
├── lyra_mobile_opaque_orm.png         # 1024², embedded
├── lyra_mobile_opaque_emission.png    # 1024², embedded
├── lyra_mobile_opaque_normal.png      # 512², embedded
├── lyra_mobile_energy_*.png           # 512² family; non-solid maps embedded
└── lyra_mobile_mantle_*.png           # 512² family; non-solid maps embedded
```

Validated Phase 3 runtime material groups:

1. `M_Lyra_OpaqueAtlas` — skin/face, suit, armor, bow shell/hardware, hair, and hair-tip emission in one guttered atlas;
2. `M_Lyra_LumenEnergy` — opaque cyan bow/core/string/projectile energy;
3. `M_Lyra_AuroraMantle` — double-sided violet mantle, isolated so it does not force that state on the body.

This is three groups, within the roadmap's 3–5 material budget. Normal maps are bound only after the final P3 UVs, normals, and MikkTSpace tangents exist.

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

### Validated Phase 4 rig contract

The completed Phase 4 export uses `JOINTS_0` unsigned-byte `VEC4`, normalized unsigned-byte `WEIGHTS_0`, and a float `MAT4` inverse bind entry for every palette joint. The 48 deform joints cover full body, both two-joint-per-digit hand chains, comet-tail hair, and asymmetric mantle. The six helpers are `socket_weapon`, `socket_projectile`, `socket_camera_body`, `socket_camera_chest`, `socket_camera_head`, and `socket_aim`. Small disconnected armor/accessory topology islands are cohesively attached to avoid internal plate shear, while anatomy, hair, and mantle retain blend deformation. Exact names and rest-parenting are frozen in [`character_rigged/RIG_SPECIFICATION.md`](character_rigged/RIG_SPECIFICATION.md).

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
