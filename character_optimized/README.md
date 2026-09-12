# Lyra Vesper — Phase 3 Mobile-Ready Asset Package

This directory contains the **Phase 3 topology and mobile-runtime handoff** for Lyra Vesper, *The Lumen Huntress*. It is built from—not a replacement for—the authored Phase 2 source at [`../character_final/lyra_vesper_phase2.glb`](../character_final/lyra_vesper_phase2.glb).

The deliverables remain full 360° mesh assets with Lyra's anatomical body, indigo hunter suit and armor, asymmetric aurora mantle, comet-tail hair, facial treatment, and the complete **Aster Arc** energy bow. No billboard, generic mannequin, or Godot primitive assembly is used.

## Delivered files

| Item | Location | Purpose |
|---|---|---|
| Mobile LOD0 | `lyra_vesper_optimized.glb` | Primary runtime mesh for close/mid combat camera use. |
| Mobile LOD1 | [`../character_lod/lyra_vesper_lod1.glb`](../character_lod/lyra_vesper_lod1.glb) | Lower-cost matching mesh for distant/small on-screen heroes. |
| Metric manifest | `optimization_manifest.json` | Machine-readable source/LOD counts and runtime policy. |
| Texture package | `textures/` | Atlas-oriented base-color, ORM, normal, and emission PNG sources. |
| Visual evidence | `renders/` | Actual-GLB front, 3/4, rear, and LOD1 review renders. |
| Reproducible builder | `source/build_lyra_phase3.py` | Simplifies, packs UV/materials, generates normals/tangents, and validates. |
| Technical decisions | `TOPOLOGY_AND_MATERIALS.md` | UV, texture, normal/tangent, topology, and rig-handoff decisions. |
| QA record | `PHASE_3_QA.md` | Evidence, checks, limitations, and phase boundary. |

## Measured results

| Measure | Phase 2 authored source | Phase 3 LOD0 | Phase 3 LOD1 |
|---|---:|---:|---:|
| Triangles | 32,176 | **11,496** | **5,843** |
| Vertices after final tangent splits | 16,420 | **8,431** | **4,834** |
| Runtime mesh/draw groups | 12 | **3** | **3** |
| Runtime material groups | 12 | **3** | **3** |
| Embedded runtime textures | 36 | **8** | **8** |
| Geometry vertex/index buffer bytes | 691,744 | **473,664** | **267,092** |
| GLB bytes | 832,524 | **799,296** | **592,720** |

- LOD0 removes **64.27%** of source triangles, **31.53%** of geometry-upload bytes, and **75%** of material/draw groups while retaining all recognition anchors.
- LOD1 removes **81.84%** of source triangles and **61.39%** of geometry-upload bytes for the distant mobile-camera tier.
- Tangent generation splits UV/hard-edge vertices where necessary, which is why the final vertex reduction is smaller than the triangle reduction. The final counts—not the pre-tangent simplifier counts—are the runtime budgets.

## Mobile texture-residency budget

The GLBs embed only maps referenced at runtime. At an RGBA8-equivalent residency estimate before mipmaps, each loaded LOD uses approximately **17 MiB**:

| Material | Runtime maps | Allocation |
|---|---|---:|
| `M_Lyra_OpaqueAtlas` | 1024² base color, ORM, emission; 512² normal | 13 MiB |
| `M_Lyra_LumenEnergy` | 512² base color, normal | 2 MiB |
| `M_Lyra_AuroraMantle` | 512² base color, normal | 2 MiB |
| **Total per selected LOD** | 8 maps / 3 materials | **17 MiB** |

For comparison, Phase 2's 36 embedded 512² maps cost an approximately 36 MiB RGBA8-equivalent residency estimate. With conventional full mip chains, the equivalent estimates are roughly 22.7 MiB versus 48 MiB. Actual Godot import/transcode allocation still needs Phase 6/14 device profiling, but this establishes a transparent, lower texture-memory baseline rather than treating PNG file bytes as GPU memory.

The builder intentionally lets glTF-Transform fold all-solid maps into PBR factors. Therefore the energy emission and mantle ORM source PNGs remain in `textures/`, but do not consume an embedded runtime texture slot.

## Runtime material contract

1. **`M_Lyra_OpaqueAtlas`** — 4×4 guttered UV atlas for skin, face details, suit, armor, hardware, hair, and hair-tip emission.
2. **`M_Lyra_LumenEnergy`** — cyan bow string, compass core, arrows, shards, and other opaque energy geometry.
3. **`M_Lyra_AuroraMantle`** — the double-sided violet left-side mantle.

This is deliberately three draw groups, below the roadmap's 3–5 material budget. Every final primitive has `POSITION`, `NORMAL`, `TEXCOORD_0`, and `TANGENT`; all three materials bind their final normal maps.

## Rebuild and structural validation

Run these commands from the repository root. The virtual environment remains outside source control.

```bash
python3 -m venv /tmp/lyra-phase3-venv
/tmp/lyra-phase3-venv/bin/pip install -r character_optimized/source/requirements.txt
/tmp/lyra-phase3-venv/bin/python character_optimized/source/build_lyra_phase3.py
/tmp/lyra-phase3-venv/bin/python character_optimized/source/render_phase3_review.py

npx --yes @gltf-transform/cli@4.5.0 validate character_optimized/lyra_vesper_optimized.glb
npx --yes @gltf-transform/cli@4.5.0 validate character_lod/lyra_vesper_lod1.glb
python3 -m unittest discover -s tests -v
```

The build pins glTF-Transform 4.5.0, makes a temporary simplification pass only, packs final UVs/materials, generates area-weighted normals, invokes MikkTSpace tangents, repairs only zero tangents caused by degenerate UV corners, and runs strict glTF validation before writing manifests.

## Phase boundary

Phase 3 is complete as an optimized mesh/material/LOD handoff. Its rigging requirements are now fulfilled by the derived Phase 4 package in [`../character_rigged/`](../character_rigged/), which owns the armature, skin weights, bend-pose review, and named socket bones. This remains **not** a claim that the hero is playable art-final: Phase 5 owns animation and Phase 6 owns actual Godot import verification. See [`TOPOLOGY_AND_MATERIALS.md`](TOPOLOGY_AND_MATERIALS.md), [`PHASE_3_QA.md`](PHASE_3_QA.md), and [`../character_rigged/PHASE_4_QA.md`](../character_rigged/PHASE_4_QA.md) for the explicit handoff constraints.
