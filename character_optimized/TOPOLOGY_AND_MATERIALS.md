# Phase 3 Technical Handoff — Topology, UVs, Materials, Normals, and LOD

## Scope and source authority

`character_final/lyra_vesper_phase2.glb` remains the high-detail authored source/interchange handoff. This Phase 3 package is a **derived runtime topology** intended for a Godot 4.x mobile action/MOBA target. The builder never edits or overwrites the Phase 2 asset.

The optimized meshes are not generic replacement geometry. They simplify the authored Lyra asset while preserving the full character volume and the gameplay-readable anchors: face/visor treatment, comet-tail silhouette, asymmetric left mantle, shoulder/boot armor outline, chest core, quiver, and the complete Aster Arc bow (curved limbs, gold compass, cyan string/core, and attached energy shapes).

## Runtime topology layout

| Runtime mesh | Material | Purpose | LOD0 triangles | LOD1 triangles |
|---|---|---|---:|---:|
| `MESH_ArmorBoot_L` | `M_Lyra_OpaqueAtlas` | Joined opaque body, head, suit, armor, hair, hardware, face details, bow shell, and quiver geometry. The historical name is retained by the joining tool; it is not an armor-only primitive. | 11,290 | 5,637 |
| `MESH_ShinLumen_L` | `M_Lyra_LumenEnergy` | Joined energy string/core/arrow/shard geometry. Historical name retained after joining. | 150 | 150 |
| `MESH_AuroraMantle_Left` | `M_Lyra_AuroraMantle` | Double-sided asymmetric violet mantle. | 56 | 56 |
| **Total** | **3 runtime materials** | Full hero asset | **11,496** | **5,843** |

The three retained mesh names originate from the source groups selected by glTF-Transform's material join; the authoritative runtime role is the material assignment and table above. Named source components remain available in the Phase 2 asset for Phase 4 rigging reference.

### Simplification policy

- **LOD0** uses meshoptimizer simplification ratio `0.35`, error `0.010`, after the Phase 2 source has been welded/deduplicated by glTF-Transform. Its final 11,496-triangle count falls inside the 10k–16k main-hero budget in `ASSET_PIPELINE.md`.
- **LOD1** uses ratio `0.18`, error `0.020`; the final 5,843-triangle count falls inside the 5k–8k distant-hero budget.
- The bow's distinctive long limbs, compass ring, cyan elements, crest/ponytail, mantle edge, body outline, hands, and boot/shoulder silhouette are not removed as a class. At LOD1, micro-detail is reduced first while the recognisable bow-and-mantle outline remains.
- The LOD1 energy/mantle groups stay at their small but silhouette-important count instead of being discarded. This avoids a misleading body-only distance model.
- No LOD2 is supplied yet. A third tier should be justified by actual Phase 14 multi-hero device profiling, not invented prematurely.

Material joining reduces runtime submissions to three groups. It does not turn the character into one generic primitive: the resulting opaque mesh contains disconnected, authored component topology and the complete non-primitive 360° geometry.

## UV atlas plan

### Opaque 4×4 atlas

`M_Lyra_OpaqueAtlas` packs the opaque Phase 2 families in a 1024² atlas with a four-pixel gutter around each occupied cell. The builder remaps each source primitive's `TEXCOORD_0` values into its destination cell before geometry joins, so distinct skin, hair, metal, and facial colors are retained despite one runtime material.

| Cell | Source family |
|---|---|
| row 0 / columns 0–3 | cobalt armor, eye white, deep-teal iris, rose lip |
| row 1 / columns 0–3 | constellation freckles, pale-gold hardware, blue-black hair, cyan hair tip |
| row 2 / columns 0–1 | midnight-indigo suit, umber skin |
| remaining cells | intentionally empty reserve for later cosmetic variation/rebake |

The associated base-color, ORM, and emission maps are 1024². The detail normal is 512² because it supports micro-relief rather than silhouette; independent texture resolution is valid because the same UV coordinates are sampled.

### Dedicated energy and mantle maps

The energy and mantle remain separate 512² map families. They avoid making the whole opaque atlas double-sided or treating all body pixels as emissive. The build emits base color, ORM source, normal, and emission source PNGs for each family. Only non-solid maps remain embedded in the GLB; glTF-Transform folds solid energy-emission/mantle-ORM maps into material factors without a visual/semantic loss.

### Godot import/color-space handoff

- Treat **base-color and emission** maps as sRGB color data.
- Treat **ORM and normal** maps as linear/non-color data. The ORM channel convention is occlusion / roughness / metallic; do not gamma-correct it.
- `M_Lyra_AuroraMantle` is deliberately **opaque + double-sided**, not alpha-blended. Keep it in a separate material because the two-sided state should not apply to Lyra's body.
- The GLBs require no glTF extensions. They retain PNG sources for safe interchange; Phase 6/14 can select Godot-imported ASTC (preferred target devices) or ETC2 fallback texture compression only after testing the real renderer/device tier.
- Preserve the four-pixel edge-dilated gutters if atlases are rebaked. Replacing them with black/transparent empty gutters can create dark mip seams.

## PBR and tangent-space decision

All final primitives contain these attributes:

```text
POSITION  — float VEC3
NORMAL    — generated after final UV/material joining
TEXCOORD_0 — final P3 packed UVs
TANGENT   — MikkTSpace VEC4
```

1. The builder generates area-weighted smooth vertex normals **after** topology simplification and UV remapping. This is important: normals authored before a mesh join or vertex split can no longer match the final runtime stream.
2. It invokes glTF-Transform's MikkTSpace tangent generator after those normals and final UVs exist. MikkTSpace is the tangent convention recommended by the glTF specification and used by conventional normal-map bakers.
3. The original Phase 2 normal maps were intentionally flat placeholders. P3 derives non-flat detail normals from the packed final color detail, making them valid tangent-space microdetail maps for this target. This is not represented as a high-poly sculpt bake.
4. Rare vertices used only by degenerate UV triangles receive a deterministic perpendicular unit-tangent fallback after the MikkTSpace pass. The current build repairs zero LOD1 tangent vectors only; regular tangent vectors remain generated output. This prevents invalid zero tangent vectors and passes strict glTF validation.
5. All three runtime materials bind a normal texture. A later high-poly rebake may replace the PNG pixels, but it must preserve this UV/tangent convention or regenerate tangents together with the bake.

## Later skinning/deformation handoff

Phase 3 intentionally does **not** add a pretend skeleton or weights. Phase 4 must skin LOD0 first, using the Phase 2 component inventory and design references to protect shoulders, elbows, wrists, hips, knees, neck, fingers, face, ponytail, and mantle behavior.

Before Phase 4 signs off, the rigging artist must:

1. preserve the Phase 3 UV/material layout or rebake it if topology changes;
2. review bind pose, full draw pose, elbow/knee bends, crouch, sprint, dash, aim, and release;
3. transfer or regenerate LOD1 weights from the approved LOD0 skeleton and compare silhouette through those poses;
4. add the required deform bones and `socket_weapon` / `socket_projectile` helpers without putting gameplay scripts in the GLB;
5. rerun strict glTF validation and the P3 structural contract after any mesh export.

This is a real topology/readiness boundary: the P3 mesh is optimized, textured, normal/tangent-capable, and LOD-defined, while skinning correctness remains a separate Phase 4 deliverable rather than an unsupported claim.
