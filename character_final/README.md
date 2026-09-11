# Lyra Vesper — Phase 2 3D Character Asset

This directory is the **Phase 2 actual 3D mesh handoff** for Lyra Vesper. It replaces the idea that a runtime assembly of Godot primitives could be a final character.

## Delivered asset

| Item | Location | Purpose |
|---|---|---|
| Canonical mesh package | `lyra_vesper_phase2.glb` | glTF 2.0 binary mesh, PBR materials, provisional texture maps, and named components. |
| Mesh manifest | `asset_manifest.json` | Reproducible counts, bounds, materials, and part inventory. |
| Source generator | `source/build_lyra_phase2.py` | Rebuilds the GLB, texture maps, and offline turntable proof. |
| Anatomical source notice | `source/MAKEHUMAN_CC0_NOTICE.md` | Provenance for the CC0 anatomical base mesh. |
| Texture sources | `textures/` | 512² provisional base color, normal, ORM, and emission maps. |
| Turntable proof | `renders/` | Offline front, three-quarter, and rear inspection renders of the actual GLB composition. |

## What is in the GLB

The exported model contains a complete adult humanoid body with modeled head, face, torso, arms, articulated hands, legs, feet, custom hair, fitted clothing, armor, asymmetric mantle, quiver, and the separate **Aster Arc** energy bow.

The visual identity is project-specific:

- `MESH_CometTail_*` — high blue-black, cyan-tipped comet-tail hair;
- `MESH_AuroraMantle_Left` — violet asymmetric shoulder mantle;
- `MESH_ChestCore*` and `MESH_TorsoLumen_*` — luminous hunter suit identifiers;
- `MESH_AsterArc_*` — crescent/compass energy-bow components;
- `MESH_Lyra_BaseSuit` and `MESH_Lyra_HeadAndHands` — full anatomical body split into suit and skin regions.

The `.glb` has **59 mesh nodes**, **12 PBR material families**, **48 embedded texture images**, UV coordinates on every mesh primitive, and no Godot `BoxMesh`, `SphereMesh`, `CapsuleMesh`, or `CylinderMesh` nodes. It is an actual interchange asset, not a screenshot or a billboard.

## Provenance and originality

The anatomy begins from a CC0 MakeHuman mesh retained at `source/makehuman_base_cc0.obj`. It is used as an anatomical starting surface, transformed and stylized by the generator. Lyra's design identity, costume layers, armor, facial treatment, hair, mantle, weapon, material language, texture generation, and source composition are original project work. The full CC0 provenance is documented in `source/MAKEHUMAN_CC0_NOTICE.md` and retained in the OBJ header.

This is not an unmodified generic mannequin: the source body is reshaped and split into custom suit/skin material regions, then combined with project-authored mesh components. The separate component naming is intentional so Phase 3 can retopologize, merge draw-call groups, and prepare a clean production rig without losing Lyra-specific design parts.

## Scope boundary: what remains for later phases

This is a **Phase 2 mesh/material/texturing deliverable**, not a false claim that the whole production roadmap is complete.

- **Phase 3:** clean production topology, formal UV review, texture-atlas consolidation, decimation/LOD exports, draw-call reduction, and mobile memory audit.
- **Phase 4:** skeleton, skin weights, socket bones, and deformation poses.
- **Phase 5:** authored animation clips.
- **Phase 6:** Godot import validation; Godot is unavailable in this implementation environment, so no runtime import claim is made here.

The current preliminary 512² texture maps are intentionally separated by material for authoring review. Base color, ORM, and emission are embedded in the GLB; normal maps stay as source files until Phase 3 generates final tangents against the final UV layout. They are not the final mobile texture memory layout; Phase 3 must consolidate them to the budget defined in `ASSET_PIPELINE.md`.

## Rebuild / validation

```bash
python3 -m venv /tmp/lyra-mesh-venv
/tmp/lyra-mesh-venv/bin/pip install -r character_final/source/requirements.txt
/tmp/lyra-mesh-venv/bin/python character_final/source/build_lyra_phase2.py
npx --yes @gltf-transform/cli inspect character_final/lyra_vesper_phase2.glb
```

The generator validates GLB export/reload, non-placeholder names, component count, triangle count, and texture/UV presence. The repository's Python contract test additionally validates the binary glTF structure without needing Blender or Godot.
