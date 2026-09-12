# Lyra Vesper — Phase 4 Rigging & Skinning Package

This directory is the **Phase 4 deformation handoff** for Lyra Vesper, *The Lumen Huntress*. Both exports are derived directly from the Phase 3 optimized meshes; they retain Lyra's authored full-body silhouette, asymmetric aurora mantle, comet-tail hair, costume/armor, and complete Aster Arc energy bow. They are not replacement mannequins, static duplicates, or gameplay primitive assemblies.

## Deliverables

| Item | Location | Purpose |
|---|---|---|
| Rigged LOD0 | `lyra_vesper_rigged.glb` | Primary close/mid-combat skinned mesh. |
| Rigged LOD1 | `lyra_vesper_rigged_lod1.glb` | Matching lower-density skinned mesh for the existing distant LOD tier. |
| Rig manifest | `rig_manifest.json` | Machine-readable skeleton, helper, skinning, and source-asset contract. |
| Rig builder | `source/build_lyra_phase4.py` | Rebuilds both standard glTF 2.0 skin exports from Phase 3. |
| CPU validation and renderer | `source/render_phase4_validation.py` | Evaluates actual exported LBS data and produces deterministic review evidence. |
| Deformation report | `validation/deformation_report.json` | Measured bind/draw/crouch audits for both LODs. |
| Review images | `renders/` | Actual-GLB bind and deformation review renders. |
| Rig specification | `RIG_SPECIFICATION.md` | Joint naming, hierarchy, sockets, weighting policy, and Phase 5 handoff. |
| QA record | `PHASE_4_QA.md` | Acceptance evidence, exact results, known limits, and phase boundary. |

## Measured runtime package

| Measure | Rigged LOD0 | Rigged LOD1 |
|---|---:|---:|
| Triangles retained from Phase 3 | 11,496 | 5,843 |
| Weighted vertices | 8,431 | 4,834 |
| Mesh / material draw groups | 3 / 3 | 3 / 3 |
| Embedded runtime textures | 8 | 8 |
| Deform joints | 48 | 48 |
| Skin-palette joints | 54 | 54 |
| GLB nodes (3 mesh nodes + 55 skeleton nodes) | 58 | 58 |
| GLB bytes | 877,896 | 642,548 |

The GLBs contain one conventional glTF `skin`, `JOINTS_0` (`UNSIGNED_BYTE VEC4`), normalized `WEIGHTS_0` (`UNSIGNED_BYTE VEC4`), and one float `MAT4` inverse-bind matrix for every palette joint. Every final vertex is weighted with no more than four influences. Existing `POSITION`, `NORMAL`, `TANGENT`, `TEXCOORD_0`, PBR material bindings, and the three-material mobile contract are retained.

## Rig at a glance

- **48 deform joints:** pelvis/spine/chest/neck/head; both clavicle/arm/hand chains; both thigh/calf/foot/toe chains; two joints for each of ten fingers; a 3-joint comet-tail chain; and a 3-joint asymmetric mantle chain.
- **6 named helpers:** `socket_weapon`, `socket_projectile`, `socket_camera_body`, `socket_camera_chest`, `socket_camera_head`, and `socket_aim`.
- **54 palette joints:** 48 deform joints plus the six helpers. Helpers have no vertex weight influence, but are held in the skin palette to preserve a standards-valid explicit hierarchy without empty-node validator findings.
- **Mobile-conscious limit:** 54 palette joints stays below the package's 55-joint budget.

See [`RIG_SPECIFICATION.md`](RIG_SPECIFICATION.md) for the full naming and attachment contract.

## Rebuild, validation, and contract checks

Run from the repository root. Keep the virtual environment outside the repository.

```bash
python3 -m venv /tmp/lyra-phase4-venv
/tmp/lyra-phase4-venv/bin/pip install -r character_rigged/source/requirements.txt
/tmp/lyra-phase4-venv/bin/python character_rigged/source/build_lyra_phase4.py
/tmp/lyra-phase4-venv/bin/python character_rigged/source/render_phase4_validation.py

npx --yes @gltf-transform/cli@4.5.0 validate character_rigged/lyra_vesper_rigged.glb
npx --yes @gltf-transform/cli@4.5.0 validate character_rigged/lyra_vesper_rigged_lod1.glb
python3 -m unittest discover -s tests -v
```

The builder rejects missing Phase 3 source assets, broken triangle streams, incomplete weighted-vertex coverage, unexpected palette/node counts, and loss of critical chains. The validator additionally decodes the GLB accessors, requires normalized weight rows and nonzero influence coverage for every deform joint, evaluates actual linear-blend skinning in bind/draw/crouch inspection poses, and writes evidence derived from the exported files.

## Phase boundary

Phase 4 is a rigging and skinning delivery. The static inspection poses are evidence only: **no named production animation clips are embedded or claimed complete.** Phase 5 owns the animation set and final animation polish. Real Godot 4 import/load and runtime attachment checks remain Phase 6 work; static glTF validation is not presented as an engine-import substitute. The existing LOD selection policy remains in [`../character_lod/README.md`](../character_lod/README.md).
