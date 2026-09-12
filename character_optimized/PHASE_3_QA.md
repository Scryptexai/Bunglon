# Phase 3 QA — Lyra Vesper Topology & Game Readiness

**Scope:** derived mobile topology, packed UV/material layout, final runtime normal/tangent streams, LOD decision, static validation, and offline visual review.

## Acceptance evidence

| Requirement | Evidence | Result |
|---|---|---|
| Full non-primitive 360° character remains | `lyra_vesper_optimized.glb` plus front/3/4/rear actual-GLB renders | Pass |
| Lyra recognition anchors remain | Renders show body/anatomy, asymmetric mantle, crest/ponytail, armor, chest core, and complete Aster Arc bow | Pass |
| LOD0 mobile polygon budget | 11,496 triangles, within 10k–16k target | Pass |
| LOD1 mobile polygon budget | 5,843 triangles, within 5k–8k target | Pass |
| Geometry reduction | LOD0 64.27% fewer triangles than 32,176-triangle Phase 2 source; LOD1 81.84% fewer | Pass |
| Material/draw-group reduction | 12 source groups → 3 runtime material/draw groups (75% reduction) | Pass |
| UV layout | `TEXCOORD_0` on every final primitive; 4×4 guttered opaque atlas documented | Pass |
| Normal/tangent readiness | `NORMAL` and MikkTSpace `TANGENT` on every final primitive; all materials bind normal textures | Pass |
| Texture-cost decision | 17 MiB RGBA8-equivalent per selected LOD vs Phase 2's 36 MiB estimate (52.78% reduction); source and policy in README | Pass |
| Geometry upload decision | 691,744 source vertex/index bytes → 473,664 LOD0 (31.53% lower) / 267,092 LOD1 (61.39% lower) | Pass |
| LOD policy | `character_lod/lod_manifest.json` and `character_lod/README.md` define 18% projected-height transition | Pass |
| Structural glTF validity | `npx --yes @gltf-transform/cli@4.5.0 validate` reports no errors, warnings, infos, or hints for both GLBs | Pass |
| Automated regression coverage | `tests/test_project_contract.py::test_phase_three_mobile_optimized_glbs_are_complete` validates structure/budgets/maps/review evidence | Pending final repository test run |

## Visual review evidence

| Asset/view | File | Review finding |
|---|---|---|
| LOD0 front | `renders/lyra_phase3_lod0_front.png` | Facial treatment, chest core, armor blocks, mantle, bow/compass, and full legs/boots visible. |
| LOD0 3/4 | `renders/lyra_phase3_lod0_three_quarter.png` | Asymmetric mantle, curved bow silhouette, ponytail arc, cyan accents, and body volume remain distinct. |
| LOD0 rear | `renders/lyra_phase3_lod0_back.png` | Closed rear body, mantle, quiver, bow, ponytail, and back-of-costume coverage visible. |
| LOD1 3/4 | `renders/lyra_phase3_lod1_three_quarter.png` | Reduced micro-detail but retained hunter silhouette, bow, mantle, crest, armor, and full anatomy. |

The renderer samples the actual embedded GLB textures per face and draws the actual final triangle streams. It is a deterministic CPU/Matplotlib review tool because this environment has no working Blender/Godot/EGL renderer. Independent Matplotlib 3D collections can have imperfect global depth ordering for layered/double-sided material review; it is adequate for coverage/silhouette evidence but does not replace actual engine visual QA.

## Reproducibility and validation commands

```bash
python3 -m venv /tmp/lyra-phase3-venv
/tmp/lyra-phase3-venv/bin/pip install -r character_optimized/source/requirements.txt
/tmp/lyra-phase3-venv/bin/python character_optimized/source/build_lyra_phase3.py
/tmp/lyra-phase3-venv/bin/python character_optimized/source/render_phase3_review.py

npx --yes @gltf-transform/cli@4.5.0 validate character_optimized/lyra_vesper_optimized.glb
npx --yes @gltf-transform/cli@4.5.0 validate character_lod/lyra_vesper_lod1.glb
python3 -m unittest discover -s tests -v
```

## Intentional next-phase boundaries

- No armature, skin weights, socket bones, deformation-pose verification, animation clips, or gameplay scripts are added here. They belong to Phase 4–6 and must not be faked by this topology package.
- The normals/tangents are final for this P3 UV/layout. The microdetail normal maps are procedurally derived from final packed texture detail, not claimed as a high-poly sculpt bake. A future high-poly rebake must use this MikkTSpace/UV contract or update both in one validated export.
- This Phase 3 report does not itself substitute for engine verification. Phase 6 subsequently tested real Godot 4 import/load on the derived animated LOD package; see [`../heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md`](../heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md).
- Android/target-device timing, memory residency after engine import, thermal behavior, and multi-hero LOD switching remain Phase 14 profiling tasks.

## Conclusion

**Phase 3 passes as a measurable optimized topology/material/LOD handoff.** It was handed forward to the matching Phase 4 rigging package in `../character_rigged/`; it is not being misrepresented as an animated or Godot-verified final hero.
