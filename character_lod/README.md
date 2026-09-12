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

`lod_manifest.json` carries the threshold and measured LOD1 data for tooling. Runtime selection is intentionally not wired into the current Godot prototype: actual engine integration begins in Phase 6, where the matching animated LODs must be imported and swapped safely during real animation playback.

## Rigging and animation status

Phase 4 skinned the matching LOD0 and LOD1 derivatives in `../character_rigged/`, using the same named 54-joint palette and validating actual exported weights under bind, moderate aim/draw, and crouch inspection poses. Phase 5 now provides matching action exports in [`../character_animated/`](../character_animated/): both LODs have the same 23 named clips, sampler timing, event extras, and animation curve payload, with CPU LBS/socket checks at authored key and semantic-event times. See [`../character_animated/ANIMATION_SPECIFICATION.md`](../character_animated/ANIMATION_SPECIFICATION.md) and [`../character_animated/PHASE_5_QA.md`](../character_animated/PHASE_5_QA.md). This evidence is asset-level only; real import/LOD-swap behavior remains a Phase 6 Godot check.
