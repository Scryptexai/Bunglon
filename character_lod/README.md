# Lyra Vesper LOD Package

## Delivered LOD

| Asset | Triangles | Vertices after tangent splits | Runtime groups | Use |
|---|---:|---:|---:|---|
| [`../character_optimized/lyra_vesper_optimized.glb`](../character_optimized/lyra_vesper_optimized.glb) | 11,496 | 8,431 | 3 | LOD0: close/mid combat camera. |
| `lyra_vesper_lod1.glb` | 5,843 | 4,834 | 3 | LOD1: farther/smaller combat camera presentation. |

Both assets use the same three named material groups, UV convention, normals, MikkTSpace tangents, and complete Lyra/bow/mantle silhouette. They are separate GLB packages so one selected LOD can be loaded without paying for the other mesh's geometry.

## Selection policy

- Use **LOD0** while Lyra projects to **18% or more** of viewport height.
- Use **LOD1** below 18% projected height or beyond the mid-range combat camera distance.
- Cross-fade if the eventual renderer/quality setting supports it. Otherwise, switch during camera motion or an animation blend to avoid a noticeable pop.
- Do **not** load/render both mesh LODs at once for one hero except during an intentional cross-fade.
- No LOD2 is supplied. The current single-hero target has one substantial distant tier; add another tier only after Phase 14 profiling demonstrates that multiple on-screen heroes need it.

`lod_manifest.json` carries the threshold and measured LOD1 data for tooling. Runtime selection is intentionally not wired into the current Godot prototype: actual engine integration begins only in Phase 6 after the Phase 4 rig/skin and Phase 5 clips exist.

## Rigging status

Phase 4 has skinned the matching LOD0 and LOD1 derivatives in `../character_rigged/`, using the same named 54-joint palette and validating actual exported weights under bind, moderate aim/draw, and crouch inspection poses. The report confirms exact bind reproduction, normalized weights, and nonzero coverage for all deform chains on both densities. Phase 5 still needs to review production locomotion, sprint, dash, release, and hit/death clips; a distance LOD without matched animation review is not accepted as final runtime animation QA.
