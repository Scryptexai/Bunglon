# Phase 4 QA — Lyra Vesper Rigging & Skinning

**Scope:** standard glTF skin export, hierarchy and helper sockets, normalized weights, inverse bind matrices, CPU linear-blend-skinning validation, offline visual review, and regression contract coverage.

## Acceptance evidence

| Requirement | Evidence | Result |
|---|---|---|
| Actual Phase 3 character retained | `lyra_vesper_rigged.glb` and `lyra_vesper_rigged_lod1.glb` are rebuilt from the two documented Phase 3 GLBs; triangle counts remain 11,496 / 5,843 | Pass |
| Full authored 360° hero remains | Actual-GLB bind review in `renders/lyra_phase4_bind_three_quarter.png`; retained body, face, costume/armor, mantle, comet-tail hair, and complete Aster Arc | Pass |
| Standard deformation-capable rig | One glTF `skin` per asset with 54 joints, `JOINTS_0`, normalized `WEIGHTS_0`, and 54 inverse-bind matrices | Pass |
| Mobile joint budget | 48 deform joints + 6 named helper joints = 54 palette joints, within the ≤55 package budget | Pass |
| Full-body and limb coverage | Pelvis/spine/head, bilateral clavicle/arm/hand, thigh/calf/foot/toe chains all have nonzero decoded influences | Pass |
| Hand/finger coverage | Ten two-joint digit chains exist; all 20 finger joints have nonzero decoded influences in both LOD audits | Pass |
| Hair and asymmetric mantle coverage | Dedicated 3-joint hair and 3-joint mantle chains receive nonzero influences and are exercised in both deformation poses | Pass |
| Weapon and gameplay-neutral helpers | `socket_weapon`, `socket_projectile`, three camera anchors, and `socket_aim` have documented hierarchy responsibilities | Pass |
| Socket parent and motion audit | Actual hierarchy audit confirms every helper parent/palette entry; `socket_weapon` / `socket_projectile` move 0.430219 m / 0.113928 m in draw and body camera follows crouch 0.009766 m | Pass |
| Hard-surface stability policy | Small disconnected armor/accessory islands are cohesively attached; large anatomy/hair/mantle retain blended deformation | Pass |
| Bind correctness | CPU LBS bind pose moves 0 vertices / 0.000 m maximum for both exported assets | Pass |
| Meaningful deformation | CPU LBS aim/draw and crouch exercises move hundreds to thousands of actual exported vertices on both LODs | Pass |
| Structural glTF validation | glTF-Transform 4.5.0 validation reports no errors, warnings, infos, or hints for each GLB | Pass |
| Automated regression coverage | `tests/test_project_contract.py::test_phase_four_rigged_glbs_are_complete` validates files, hierarchy, skin accessors, matrices, weight rows, source metrics, evidence, and phase boundary | Pass (14-test suite) |

## Structural and numerical results

The exported data was decoded from the GLBs themselves; it is not a metadata-only report.

| Asset / pose | Vertices moved >1 mm | Mean displacement | Max displacement | Result |
|---|---:|---:|---:|---|
| LOD0 bind | 0 / 8,431 | 0.000000 m | 0.000000 m | Exact rest reproduction |
| LOD0 moderate aim/draw | 6,318 / 8,431 | 0.111746 m | 0.960574 m | Pass |
| LOD0 crouch | 8,431 / 8,431 | 0.201783 m | 0.527412 m | Pass |
| LOD1 bind | 0 / 4,834 | 0.000000 m | 0.000000 m | Exact rest reproduction |
| LOD1 moderate aim/draw | 3,641 / 4,834 | 0.122415 m | 0.960574 m | Pass |
| LOD1 crouch | 4,834 / 4,834 | 0.204983 m | 0.520489 m | Pass |

Both LOD audits decode weight sums with `min = max = mean = 1.0`. All 48 deform joints have a nonzero influence count. The decoded exported inverse-bind matrices reconstruct the explicit rest hierarchy with a maximum absolute float32 rounding error of **0.000000105 m** (well below the 0.000002 m validation tolerance). The six socket helpers are intentionally palette members with no vertex influence.

## Visual review evidence

| Asset / view | File | Review finding |
|---|---|---|
| LOD0 bind, three-quarter | `renders/lyra_phase4_bind_three_quarter.png` | Confirms original character, complete bow, tailored armor, mantle, comet-tail silhouette, and explicit skeleton overlay at rest. |
| LOD0 moderate aim/draw, three-quarter | `renders/lyra_phase4_draw_three_quarter.png` | Exercises spine, bilateral shoulders/elbows/wrists, all compact digit joints, right-hand bow carrier, tail, and mantle without a hard-surface plate shearing internally. |
| LOD0 crouch, three-quarter | `renders/lyra_phase4_crouch_three_quarter.png` | Exercises pelvis/spine, bilateral hip/knee/foot chains and the secondary hair/mantle chains. |
| LOD1 moderate aim/draw | `renders/lyra_phase4_lod1_draw_three_quarter.png` | Confirms matched lower-density mesh maintains the same rig/weapon relation. |
| LOD1 bind reference | `renders/lyra_phase4_lod1_bind_reference.png` | Confirms lower-density rest pose and silhouette. |
| LOD1 crouch reference | `renders/lyra_phase4_lod1_crouch_reference.png` | Confirms lower-density lower-body and secondary-chain deformation. |

The deterministic CPU review renderer reads face positions, UVs, `JOINTS_0`, `WEIGHTS_0`, hierarchy transforms, inverse bind matrices, material base-color textures, and triangle streams from the actual GLBs. It is suitable for structural/silhouette evidence in this environment. As with the Phase 3 review tool, Matplotlib's independent 3D collections can have imperfect global depth ordering on layered/double-sided geometry; it does not replace a real Godot or DCC render.

## Commands executed for this record

```bash
/tmp/lyra-phase4-venv/bin/python character_rigged/source/build_lyra_phase4.py
/tmp/lyra-phase4-venv/bin/python character_rigged/source/render_phase4_validation.py
npx --yes @gltf-transform/cli@4.5.0 validate character_rigged/lyra_vesper_rigged.glb
npx --yes @gltf-transform/cli@4.5.0 validate character_rigged/lyra_vesper_rigged_lod1.glb
python3 -m unittest discover -s tests -v
```

## Limitations and next-phase boundary

- The aim/draw and crouch configurations are deliberately static **QA poses**, evaluated by CPU linear-blend skinning. They are not embedded clips and are not represented as a finished animation set.
- No gameplay integration, player/AI compatibility, real `Skeleton3D` import, retargeting, AnimationTree setup, or mobile device profiling is claimed here. Godot engine validation belongs to Phase 6 and device profiling remains later production work.
- Phase 5 must author the named animation set and inspect these chains under production timing. It must preserve the documented names and use the sockets rather than introduce mesh-transform or duplicate-weapon workarounds.

## Conclusion

**Phase 4 passes as a measurable rigging and skinning handoff.** Lyra's actual mobile LOD0 and LOD1 meshes now contain a standard, bounded, deformation-capable skeleton and verified weight data ready for Phase 5 animation production—not a premature claim that the animation or Godot integration phases are complete.
