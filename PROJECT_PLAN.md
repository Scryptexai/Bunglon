# PROJECT PLAN — Lyra Vesper 3D Hero Production

**Roadmap:** 3D Hero Production Roadmap V1

**Engine target:** Godot 4.x

**Hero:** Lyra Vesper — *The Lumen Huntress*

**Archetype:** Agile ranged hunter / marksman

**Current authoritative phase:** **Phase 5 — Authored Animation Action Set (complete at asset-validation gate; ready for Phase 6 Godot import/integration)**

> **Important scope correction**: the current native Godot mesh assembly in this repository is an implementation prototype only. Because it is composed from Godot primitive meshes, it is explicitly **not eligible as the final character asset** under the new roadmap. It must be replaced in Phase 2–6 by an authored, textured, rigged 3D character export. No further gameplay work is considered a substitute for that asset-production gate.

## 1. Outcome and non-negotiable quality bar

The final deliverable is one original, playable mobile-MOBA hero—not a mannequin and not a blockout. Lyra must retain a recognizable silhouette from all gameplay distances:

- tall asymmetric cyan energy bow;
- indigo lightweight armor over an athletic humanoid body;
- violet aurora mantle on the left side;
- swept dark ponytail/crest;
- cyan visor and diamond chest core.

The final asset must be a real mesh with authored topology, UVs, materials/textures, skin weights, skeleton, and baked animations. Primitive objects may only exist in a private blockout collection and must not be present in the shipped scene/model.

## 2. Tool and environment decision

### Tools currently detected in the implementation environment

| Tool | Status | Decision |
|---|---|---|
| Python 3.11 | Available | Use for validation, asset manifests, and optional format checks. |
| Godot 4 editor/headless | Not installed | Required for Phase 6 runtime import and Phase 7–16 execution validation. |
| Blender | Not installed | Required for Phase 2–5 final modeling, UV, rigging, and animation. |
| Image generation | Available | Use only for original concept/turnaround reference, never as a substitute for 3D geometry. |

### Chosen production pipeline

```text
Original 2D concept sheet
    ↓
Blender scene (.blend): authored base mesh + garment/hair/weapon meshes
    ↓
Retopology, UV atlas, PBR textures, LOD meshes
    ↓
Blender armature + skin weights + hand-authored animation actions
    ↓
GLB export (one canonical asset package)
    ↓
Godot import → Hero visual scene → AnimationTree → gameplay sockets/events
    ↓
Desktop smoke test → Android/mobile profiling → polish → QA sign-off
```

**Canonical interchange format:** glTF 2.0 binary (`.glb`). It retains mesh, skin, skeleton, PBR material assignments, and baked animation clips in one deterministic package compatible with Godot 4.

## 3. Asset generation method

### Concept and reference method — Phase 1

Create one locked orthographic reference package for the same Lyra design:

- front, back, left, right;
- 3/4 front and 3/4 back;
- face sheet at readable scale;
- bow sheet with drawn/string/projectile-socket view;
- costume detail sheet for mantle, chest core, visor, and armor segmentation.

The reference package locks proportions, color language, and silhouette before modeling begins. It is not gameplay content.

### Mesh method — Phase 2–3

Create an authored Blender mesh from topology, not by shipping primitive objects:

1. Block out proportional volumes privately, then convert/rebuild into continuous editable topology.
2. Model head, body, hands, boots, hair, armor panels, mantle, quiver, and bow as intentional meshes.
3. Retopologize for clean deformation loops at shoulders, elbows, wrists, hips, knees, neck, and face.
4. Create UV islands and a compact mobile PBR atlas.
5. Bake normal/AO/curvature from the high-detail source where needed.
6. Produce LOD0 and LOD1; LOD2 is optional based on on-device profiling.

A final acceptance review checks the GLB in a 360-degree turntable and rejects visible primitive silhouettes, missing backsides, open seams, broken normals, or untextured placeholder surfaces.

**Phase 3 result:** the derived runtime package now provides a 11,496-triangle LOD0 and 5,843-triangle LOD1, three runtime material/draw groups, guttered atlas UVs, generated normals, and MikkTSpace tangents. The complete evidence and non-engine limitations are retained in `character_optimized/README.md`, `character_optimized/TOPOLOGY_AND_MATERIALS.md`, and `character_optimized/PHASE_3_QA.md`.

### Rigging and animation method — Phase 4–5

Use a custom Blender armature (or a controlled Rigify-derived export rig), then bake to a compact deform rig for export. The final deform rig has these required bones:

- root, pelvis, spine chain, chest, neck, head;
- clavicle/shoulder, upper arm, forearm, hand, finger chains;
- thigh, shin, foot, toe;
- hair/ponytail and mantle secondary bones only where they materially improve silhouette;
- `socket_weapon`, `socket_projectile`, and optional `socket_camera_aim` helper bones.

Skin weights are hand-reviewed in bend, crouch, aim, run, and draw poses. Animation is authored as named Blender Actions with anticipation → action → impact → recovery, then baked in the GLB export. Root motion policy is **in-place** for gameplay locomotion; movement remains authoritative in Godot.

**Phase 4 result:** the documented Phase 3 LOD0 and LOD1 assets now have matching standard glTF skins with 48 deform joints, 54 palette joints, six named attachment helpers, normalized four-influence weights, and inverse-bind matrices. Actual exported LBS data passes bind, moderate aim/draw, and crouch evaluation; the hard-surface island policy keeps small disconnected armor/accessory parts cohesive. See [`character_rigged/README.md`](character_rigged/README.md), [`character_rigged/RIG_SPECIFICATION.md`](character_rigged/RIG_SPECIFICATION.md), and [`character_rigged/PHASE_4_QA.md`](character_rigged/PHASE_4_QA.md).

**Phase 5 result:** matching animated LOD0/LOD1 GLBs now embed the complete 23-action set as 523 real core-glTF `LINEAR` rotation channels/samplers with 2,796 baked quaternion keys per LOD. The action export remains in-place (zero translation channels), preserves the frozen Phase 4 skin/material/socket contracts, and supplies semantic event timings for bow releases, ability windows, locomotion, reactions, and recovery. Exported-asset CPU LBS/event-time socket validation and visual evidence are documented in [`character_animated/README.md`](character_animated/README.md), [`character_animated/ANIMATION_SPECIFICATION.md`](character_animated/ANIMATION_SPECIFICATION.md), and [`character_animated/PHASE_5_QA.md`](character_animated/PHASE_5_QA.md). This is not a claim that real Godot import or gameplay-event hookup is finished.

## 4. Godot integration decision — Phase 6 onward

- Import `lyra_vesper.glb` into `heroes/hero_agile_hunter/models/`.
- Instance its generated scene under `HeroCharacter/Visual/CharacterModel`.
- Bind `socket_projectile` to the existing gameplay `ProjectileOrigin` marker or adapt the marker in a visual-only adapter.
- Use imported `AnimationPlayer` clips as the source for `AnimationTree` states.
- Keep `CharacterBody3D`, `Hurtbox`, `Hitbox`, `TargetingComponent`, `DamageEvent`, and controller code outside imported visual nodes.
- Animation events call semantic gameplay hooks (release projectile, dash start, ultimate damage window); gameplay never infers damage from mesh collision.

## 5. Folder architecture at final delivery

```text
Hero/
├── concept/
│   ├── lyra_turnaround_front.png
│   ├── lyra_turnaround_back.png
│   ├── lyra_turnaround_left.png
│   ├── lyra_turnaround_right.png
│   ├── lyra_three_quarter_front.png
│   ├── lyra_three_quarter_back.png
│   ├── lyra_face_sheet.png
│   ├── lyra_weapon_sheet.png
│   └── lyra_costume_details.png
├── source/                         # Blender source / source-control policy dependent
├── models/
│   ├── lyra_vesper_final.glb
│   ├── lyra_vesper_optimized.glb
│   └── lyra_vesper_lod1.glb
├── textures/
├── materials/
├── animations/
├── weapons/
├── vfx/
├── audio/
├── data/
├── scenes/
├── scripts/
└── docs/
```

The existing `heroes/hero_agile_hunter/` structure can be retained during migration, but the above is the release contract. No external visual asset is allowed to become a gameplay dependency.

## 6. Phase gates and pass criteria

| Phase | Deliverable / gate | Status |
|---:|---|---|
| 0 | This plan, root asset pipeline, root architecture | **Complete** |
| 1 | Full multi-angle reference package + locked design | **Complete — see `character_design.md`, `concept/`, and `references/`** |
| 2 | Authored 360° non-primitive character + bow mesh | **Complete — `character_final/lyra_vesper_phase2.glb`** |
| 3 | UV, PBR textures, optimized mesh, normal/tangent streams, and LOD decision | **Complete — `character_optimized/lyra_vesper_optimized.glb`, `character_lod/lyra_vesper_lod1.glb`, and Phase 3 QA** |
| 4 | Deformation-tested skeleton and skinning | **Complete — `character_rigged/lyra_vesper_rigged.glb`, matched LOD1, socket contract, and Phase 4 QA** |
| 5 | Authored animation action set | **Complete — `character_animated/` has real named GLB animation curves, timings, LBS/socket evidence, and QA** |
| 6 | Godot import verification with real GLB | Ready next; requires a real Godot 4.x editor/runtime import gate |
| 7–13 | Controller, combat, ability, targeting, AI connection | Existing code is prototype only; revalidate after Phase 6 |
| 14 | Device profiling / mobile budget audit | Not started |
| 15 | Polish pass | Not started |
| 16 | Final QA evidence | Not started |
| 17 | Final packaged Hero deliverable | Not started |

## 7. Dependency order

1. **Lock design reference** before changing meshes.
2. **Create and validate mesh/UV/materials** before rigging.
3. **Freeze skeleton/socket naming** before animation export.
4. **Import real GLB in Godot** before attaching gameplay events.
5. **Validate controller/combat/skills** against imported animation timing.
6. **Profile mobile** before visual polish.
7. **Run final QA** only with the final non-primitive asset package.

This order prevents expensive rework such as reauthoring combat timing after a bow socket, bone hierarchy, or animation length changes.

## 8. Test strategy

- **Source validation:** verify GLB exists, required clips exist, texture limits conform, and scene resource paths resolve.
- **DCC validation:** 360° render, topology/deformation poses, UV checker, material check, and exported animation review.
- **Godot validation:** headless import parse plus interactive movement/attack/skill/death test.
- **Mobile validation:** GPU/CPU frame profile, draw-call count, texture memory, skinning cost, particle overdraw, and thermal run.
- **Regression tests:** retained data/combat/targeting tests plus Phase 5 export-level sampler/channel, timing/event, in-place-root-motion, LOD-parity, and LBS/socket-report checks; engine-facing event tests follow real Phase 6 import.

## 9. Explicit definition of done

The work is done only when Phase 16 passes **with the final authored GLB asset**. A procedural assembly of cubes/cylinders/capsules, a single concept image, or a functioning controller alone does not satisfy this plan.
