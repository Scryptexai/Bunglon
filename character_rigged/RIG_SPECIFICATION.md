# Lyra Vesper Phase 4 — Rig Specification and Phase 5 Handoff

## Coordinate and export contract

- **Asset origin:** `character_optimized/lyra_vesper_optimized.glb` (LOD0) and `character_lod/lyra_vesper_lod1.glb` (LOD1).
- **Coordinate convention:** X is left/right, Y is depth, Z is up; positions are meter-scale rest positions.
- **Export:** glTF 2.0 binary (`.glb`), one skin per selected LOD asset, no required extensions.
- **Skin data:** `JOINTS_0` is unsigned-byte `VEC4`; `WEIGHTS_0` is normalized unsigned-byte `VEC4`; each skin has 54 float `MAT4` inverse-bind matrices.
- **LBS convention:** vertices are evaluated by standard linear-blend skinning using the supplied inverse-bind matrices and the named hierarchy below.

The same hierarchy, palette ordering, helper names, and material contract are generated for both LODs. Do not retopologize, repack UVs, substitute materials, or rename bones in one LOD only.

## Hierarchy

`root` is the non-deforming skeleton motion root. The following indenting represents parentage.

```text
root
├─ pelvis
│  ├─ spine_01
│  │  └─ spine_02
│  │     └─ chest
│  │        ├─ neck
│  │        │  └─ head
│  │        │     ├─ hair_root
│  │        │     │  └─ hair_mid
│  │        │     │     └─ hair_tip
│  │        │     └─ socket_camera_head
│  │        ├─ clavicle_l → upperarm_l → lowerarm_l → hand_l
│  │        │  ├─ thumb_01_l → thumb_02_l
│  │        │  ├─ index_01_l → index_02_l
│  │        │  ├─ middle_01_l → middle_02_l
│  │        │  ├─ ring_01_l → ring_02_l
│  │        │  └─ pinky_01_l → pinky_02_l
│  │        ├─ clavicle_r → upperarm_r → lowerarm_r → hand_r
│  │        │  ├─ thumb_01_r → thumb_02_r
│  │        │  ├─ index_01_r → index_02_r
│  │        │  ├─ middle_01_r → middle_02_r
│  │        │  ├─ ring_01_r → ring_02_r
│  │        │  ├─ pinky_01_r → pinky_02_r
│  │        │  └─ socket_weapon → socket_projectile
│  │        ├─ mantle_root → mantle_mid → mantle_tip
│  │        ├─ socket_camera_chest
│  │        └─ socket_aim
│  ├─ thigh_l → calf_l → foot_l → toe_l
│  ├─ thigh_r → calf_r → foot_r → toe_r
│  └─ socket_camera_body
```

There are **48 deform joints**: 6 torso/head, 8 arm/hand, 8 leg/foot, 20 finger, 3 hair, and 3 mantle joints. The remaining six named nodes are attachment helpers. Exact rest positions, roles, and parent fields are available to tooling in [`rig_manifest.json`](rig_manifest.json).

## Socket responsibilities

| Helper | Parent | Rest position | Intended Phase 5/6 responsibility |
|---|---|---:|---|
| `socket_weapon` | `hand_r` | `(1.14, -0.14, 2.22)` | Aster Arc grip / held-weapon attachment. |
| `socket_projectile` | `socket_weapon` | `(0.44, -0.31, 2.22)` | Arrow, ray, or charged-projectile release origin. |
| `socket_camera_body` | `pelvis` | `(0.00, 0.00, 1.60)` | Stable body-level follow-camera anchor. |
| `socket_camera_chest` | `chest` | `(0.00, -0.08, 2.47)` | Combat framing / chest-centered follow anchor. |
| `socket_camera_head` | `head` | `(0.00, -0.10, 3.15)` | Look-at or close presentation anchor. |
| `socket_aim` | `chest` | `(0.00, -0.55, 2.30)` | Aim/targeting reference, not a projectile emitter. |

The world-space rest positions are descriptive; because helpers are normal child nodes, their exported local transforms preserve the parent-relative location and follow the parent during a pose. `socket_weapon` and `socket_projectile` deliberately share the right-hand chain that carries the rigid Aster Arc geometry.

## Weighting policy

The source mesh intentionally joins many separately authored costume and accessory pieces into three runtime draw groups. A uniform generic gradient across such disconnected islands produces visible hard-surface shearing. The builder therefore uses the following deterministic policy:

1. **Large connected anatomy** (120 or more vertices, or a broad multi-axis island retained below that count by LOD1) receives local inverse-distance blend weights from the articulated body chain.
2. **Comet-tail hair** always uses the dedicated `hair_root` / `hair_mid` / `hair_tip` chain; the high rear tail remains deformable rather than being attached as a static prop.
3. **Aurora mantle** always uses its dedicated `mantle_root` / `mantle_mid` / `mantle_tip` chain plus its chest/clavicle support joints.
4. **Small disconnected hard-surface, facial, quiver, and costume islands** receive one cohesive nearest appropriate deform joint, preventing a rigid plate from shearing internally during an arm or torso bend.
5. **Finger-region geometry** receives normalized weights over the two nearest compact digit chains (up to four joints), keeping every two-joint digit chain live while permitting small finger bends.
6. **Aster Arc geometry and the release-arrow region** use a rigid `hand_r` influence. The narrow release-region test intentionally excludes the nearby right-hand/finger vertices.

The exported weights are quantized to 8-bit normalized components. The quantizer corrects the dominant component so every row sums exactly to 255 encoded units (1.0 after decode). Every LOD0 and LOD1 deform joint has at least one nonzero decoded influence; helpers intentionally have none.

## Animator handoff

Phase 5 should use `root` for locomotion/root-motion policy and animate the named deform bones, not object-level mesh transforms. Preserve the held-bow relation by posing `hand_r` and its ancestors; do not detach the Aster Arc into a separate static visual. Use `socket_projectile` for timing-aligned projectile release, and choose one of the camera/aim helpers rather than hard-coded world offsets.

Recommended high-risk checks before accepting a Phase 5 clip:

- Inspect shoulders, elbows, wrists, and both hands through aim, draw, release, reload, dash, hit reaction, and death.
- Keep finger bends restrained at this mobile two-joint-per-digit resolution; verify the release hand and bow grip silhouette at gameplay camera distance.
- Inspect the comet-tail and asymmetric mantle through turns, sprint, air time, and abrupt stops; they are skinned chains, not simulation claims.
- Keep the armor and small accessory islands cohesive. If a future clip exposes an attachment problem, correct the source weighting policy and rebuild both LODs instead of adding a second mesh transform workaround.
- Retain the Phase 3 material/PBR/tangent streams and match any animation export to this exact skeleton naming contract.

## Explicit non-goals of this handoff

This package contains no exported `animations` array and no assertion that a draw, idle, locomotion, ability, hit, or death action is production-ready. Those clips, retargeting choices, root-motion decisions, and real Godot import verification belong to the next production phases.
