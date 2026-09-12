# Phase 6 — Godot Integration: Lyra Vesper

## Scope and ownership

Phase 6 replaces the active primitive/procedural hero presentation with the
Phase 5 authored animated GLB package while preserving the modular
`HeroCharacter` gameplay boundary.

`HeroPresentationAdapter` is the presentation-only owner under
`HeroCharacter/Visual`. It loads LOD0, validates LOD1 before use, finds the
imported `Skeleton3D` and `AnimationPlayer`, builds an `AnimationTree`, resolves
attachment helpers, and emits safe semantic presentation signals. It does not
move `CharacterBody3D`, select targets, instantiate authoritative projectiles,
apply damage, alter cooldowns, or set status effects.

| Gameplay owner | Phase 6 presentation consumer |
|---|---|
| `CharacterController` player/AI/external intent | `HeroAnimationDriver.request_action()` maps named action intent to the adapter. |
| `MovementController` physics/facing | Adapter plays `idle`, `walk`, `run`, turns, and action clips only. |
| `BasicAttack` / `HeroAbility` timing and projectile authority | Adapter’s manifest markers drive VFX/audio only. The gameplay timer remains the sole projectile/damage path. |
| `CameraTarget` facade | Reads imported camera/aim helper positions, with editor Marker3D fallbacks only for a failed/incomplete import. |

## Imported asset contract

The adapter requires the following from **both**:

- `res://character_animated/lyra_vesper_animated.glb` (LOD0)
- `res://character_animated/lyra_vesper_animated_lod1.glb` (LOD1)

| Contract | Required value |
|---|---|
| Skeleton | Exactly 54 imported bones, with equal ordered bone names on both LODs. |
| Clips | The 23 canonical names in `animation_manifest.json`; each has the manifest duration and its listed rotation-bone tracks. |
| Helpers | `socket_weapon`, `socket_projectile`, `socket_camera_body`, `socket_camera_chest`, `socket_camera_head`, `socket_aim`. Helpers may import as a node or as a skeleton bone; the adapter exposes them as `Node3D` attachments. |
| Materials | `M_Lyra_OpaqueAtlas`, `M_Lyra_LumenEnergy`, `M_Lyra_AuroraMantle`, with at least eight distinct imported texture references. |
| LOD replacement | Equal skeleton, clip timing, helper, material, and texture contracts. Failed validation leaves LOD0 active. |

### Axis conversion

The authored Phase 4/5 source is Z-up and uses `-Y` as Lyra/bow front. Godot
is Y-up with the gameplay-facing convention `-Z`. The adapter applies one
proper root basis, not a negative scale:

```text
local X → Godot LEFT
local Y → Godot BACK
local Z → Godot UP
(x, y, z) → (-x, z, y)
```

That conversion is intentionally only at the presentation boundary. It retains
right-handed orientation, makes the bow/projectile align to gameplay forward,
and leaves gameplay coordinates untouched.

### Observed Godot 4.3 importer conversion

The real-engine probe observed 54 bones and 47 `TYPE_ROTATION_3D` tracks for
every imported canonical clip. Godot preserves every authored manifest target:
dynamic source channels remain multi-key tracks, while identity-only source
channels can be collapsed to a single key and extra deform bones receive
one-key rest-pose tracks. The validation therefore checks the source target set,
its multi-key motion, rotation-target validity, and duration rather than
incorrectly requiring the source-channel count to equal Godot's expanded track
count. Raw imported GLB clips have no arbitrary glTF-extra loop metadata;
`HeroPresentationAdapter` applies the checked-in manifest loop policy before
activating its `AnimationTree`.

## Safe semantic events

`animation_manifest.json` is the source of visual event names and times.
`HeroPresentationAdapter` tracks fired markers by clip action iteration:

- a normal interruption clears the old action ledger;
- an explicit action restart starts a new iteration;
- an LOD swap preserves the active clip time and ledger, so passed markers do
  not replay;
- marker handlers only trigger VFX/audio presentation sinks.

Consequently, a `projectile_release` marker may animate sound/light feedback at
`socket_projectile` but cannot manufacture a duplicate projectile or damage
transaction. `BasicAttack` and the later Phase 9 ability timers query matching
manifest timestamps once to align their already-authoritative timelines; they do
not subscribe to the emitted presentation signal to perform `spawn_projectile`.

## Validation commands

Use a Godot 4.3+ executable after allowing the editor/project import to finish:

```bash
# Import source GLBs to Godot PackedScenes and parse project scripts/scenes.
godot --headless --path . --editor --quit

# Direct Godot importer coverage: skeleton, all clips/tracks/durations,
# material names/textures, helpers, and raw AnimationPlayer playback.
godot --headless --path . --script res://tests/godot/phase6_import_probe.gd

# Runtime replacement coverage: adapter, AnimationTree, helper motion,
# semantic event dedupe/restart/LOD swap, isolated preview, player and AI intent.
godot --headless --path . --script res://tests/godot/phase6_integration_smoke.gd

# Repository contract and authored package regression checks.
python3 -m unittest discover -s tests -v
```

The isolated asset review scene is
`res://heroes/hero_agile_hunter/scenes/lyra_presentation_preview.tscn`; it uses
the same adapter as the hero scene and therefore catches a visual replacement
that works only in a demo-specific branch.

## Recorded real-engine result

On 2026-09-12, the project was imported and exercised with a locally built
Godot `4.3.stable.custom_build.77dcf97d8` executable:

| Command / coverage | Result |
|---|---|
| `--headless --editor --quit` | Project/GLB import completed and all loaded scripts parsed after fixing the HUD type inference. |
| `phase6_import_probe.gd` | PASS: both GLBs instantiated as packed scenes; each reported one `AnimationPlayer`, one 54-bone `Skeleton3D`, three skinned mesh instances, all 23 clips with manifest durations/rotation targets, six helpers, three material names, eight textures, and moving `socket_projectile`. |
| `phase6_integration_smoke.gd` | PASS: isolated preview, proper axis orientation, active animation tree, 23 mapped clips, material/helper contracts, semantic release de-duplication, restart, LOD time-preserving swap, player `skill_02` intent, AI combat intent, and authoritative imported projectile origin. |
| `hero_character.tscn` / project main scene | Started for 180 / 300 frames respectively with no GDScript parse error, invalid call, or out-of-tree transform error. |

The local executable was intentionally compiled with no GPU renderer so it can
run in this sandbox. Its `No renderers available` and dummy mesh-storage
messages are expected headless-backend diagnostics, not adapter/test failures;
material and texture resource import was validated through Godot objects. A
normal Godot 4.3+ editor should open the isolated preview scene for visual
material/camera inspection.

## Deliberately out of scope

This phase does **not** claim Android/mobile device profiling, final VFX/SFX,
multiplayer or replay synchronization, or final gameplay balancing. The mobile
budgets remain documented targets for subsequent phase validation.
