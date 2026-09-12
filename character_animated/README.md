# Lyra Vesper — Phase 5 Authored Animation Action Set

This package is the **Phase 5 animation delivery** for Lyra Vesper, *The Lumen Huntress*. It derives directly from the locked Phase 4 skinned LODs and embeds actual standard glTF 2.0 skeletal animation data: 23 named `animations`, 523 `LINEAR` rotation samplers/channels, and 2,796 baked quaternion keys in each LOD. It is not a static pose gallery, a metadata-only clip list, a procedural Godot replacement, or a generic mannequin animation set.

The animations preserve the validated Phase 4 mesh topology, three material/PBR draw groups, normalized `JOINTS_0` / `WEIGHTS_0` streams, inverse-bind matrices, 54-joint skin palette, exact bone names, and helper socket hierarchy. Their names/order match `HeroAnimationDriver.CANONICAL_CLIPS`; gameplay movement remains in-place and authoritative outside this visual asset.

## Deliverables

| Item | Location | Purpose |
|---|---|---|
| Animated LOD0 | `lyra_vesper_animated.glb` | Production-action export for close/mid combat. |
| Animated LOD1 | `lyra_vesper_animated_lod1.glb` | Matching action export for the existing lower-density LOD tier. |
| Animation manifest | `animation_manifest.json` | Machine-readable names, durations, loops, direct tracks, semantic events, sources, and phase boundary. |
| Deterministic builder | `source/build_lyra_phase5.py` | Adds baked core-glTF animation samplers/channels to Phase 4 LOD0/LOD1. |
| CPU validation / renderer | `source/render_phase5_validation.py` | Samples the exported curves and evaluates real LBS deformation plus socket continuity. |
| Dependencies | `source/requirements.txt` | Pinned Python dependencies for the build and review tool. |
| Animation specification | `ANIMATION_SPECIFICATION.md` | Clip catalog, timing contract, root-motion and authored-motion policy. |
| Phase 5 QA record | `PHASE_5_QA.md` | Measured validation evidence and review scope. |
| Phase 6 handoff | `PHASE_6_HANDOFF.md` | Import/integration contract and deliberately deferred work. |
| Review images | `renders/` | Selected actual-GLB/LBS poses from locomotion, attacks, skills, ultimate, death, and LOD1. |
| Validation report | `validation/animation_report.json` | Export-derived per-clip deformation, event-time socket, and inverse-bind audits. |

## Measured package contract

| Measure | Animated LOD0 | Animated LOD1 |
|---|---:|---:|
| Triangles retained from Phase 4 | 11,496 | 5,843 |
| Vertices retained from Phase 4 | 8,431 | 4,834 |
| Mesh / material draw groups | 3 / 3 | 3 / 3 |
| Embedded textures | 8 | 8 |
| GLB nodes / skin palette joints | 58 / 54 | 58 / 54 |
| Named actions | 23 | 23 |
| Direct rotation channels / samplers | 523 / 523 | 523 / 523 |
| Baked quaternion keys | 2,796 | 2,796 |
| GLB bytes | 1,113,680 | 878,328 |

Every animation channel targets a Phase 4 hierarchy node's `rotation` property, uses `LINEAR` interpolation, starts at `0`, ends at the named clip duration, and contains normalized non-identity quaternion data. No translation animation channels are exported, including on `root`.

## Canonical action set

The exported animation names/order are intentionally identical in both LODs:

```text
idle, idle_variation, walk, run, turn_left, turn_right, start_run, stop_run,
basic_attack, basic_attack_recovery, attack_variant, charged_attack, hit_light,
hit_heavy, knockback, stun, death, victory, spawn, skill_01, skill_02,
skill_03, ultimate
```

The authored set covers idle/readiness, in-place locomotion, turns and movement transitions, standard/variant/charged bow attacks, reactions, death, spawn/victory, all three named skills, and ultimate. Bow actions animate both arms/hands and compact two-joint finger chains; locomotion and action poses include independent comet-tail and aurora-mantle secondary chains. See [`ANIMATION_SPECIFICATION.md`](ANIMATION_SPECIFICATION.md) for timings, events, and intent.

## Rebuild and validate

Run from the repository root. Keep the virtual environment outside the repository.

```bash
python3 -m venv /tmp/lyra-phase5-venv
/tmp/lyra-phase5-venv/bin/pip install -r character_animated/source/requirements.txt
/tmp/lyra-phase5-venv/bin/python character_animated/source/build_lyra_phase5.py
/tmp/lyra-phase5-venv/bin/python character_animated/source/render_phase5_validation.py

npx --yes @gltf-transform/cli@4.5.0 validate character_animated/lyra_vesper_animated.glb
npx --yes @gltf-transform/cli@4.5.0 validate character_animated/lyra_vesper_animated_lod1.glb
python3 -m unittest discover -s tests -v
```

The builder rejects changes to locked Phase 4 topology/material/skin contracts and audits the saved GLBs for exact action names/order, real rotation channels, `LINEAR` sampling, timing bounds, unit quaternions, event extras, loop/root-motion fields, and body/limb/finger/hair/mantle coverage. The review validator independently decodes the exported GLBs, samples actual key and event times, applies exported inverse-bind matrices and `JOINTS_0`/`WEIGHTS_0` with CPU linear-blend skinning, verifies helper-parent continuity at all semantic-event times, and writes the report/renders.

## Phase boundary

This is an animation asset handoff, not a claim that the live Godot prototype has been converted to use it. **Phase 6** owns real Godot 4 import, `AnimationPlayer` / `AnimationTree` mapping, runtime helper resolution, semantic-event dispatch, actual projectile/VFX attachment, and player/AI presentation integration. **Later phases** own combat gameplay validation, Android/mobile profiling, and final playtest sign-off. The event data is a timing contract for an adapter; it does not make visual mesh animation authoritative for collision or damage.
