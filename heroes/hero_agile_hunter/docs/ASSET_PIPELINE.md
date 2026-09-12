# Asset Pipeline & Mobile Budget

## Active Phase 6 Godot asset layer

Lyra Vesper now runs from the authored Phase 5 glTF package rather than a
procedural or primitive runtime character:

| Asset / integration point | Active contract |
|---|---|
| LOD0 | `character_animated/lyra_vesper_animated.glb`, an authored 54-bone skinned hero with 23 canonical clips. |
| LOD1 | `character_animated/lyra_vesper_animated_lod1.glb`, only eligible after imported skeleton, clips, timing, helper, material, and texture contracts match LOD0. |
| Animation data | `character_animated/animation_manifest.json` supplies durations, loop policy, and presentation semantic markers. |
| Runtime owner | `scripts/presentation/hero_presentation_adapter.gd`, attached to `HeroCharacter/Visual`; it owns only visual import, animation playback, helper resolution, and LOD selection. |
| Isolated review | `scenes/lyra_presentation_preview.tscn` displays the same adapter independently of combat gameplay. |
| Engine validation | `tests/godot/phase6_import_probe.gd` and `tests/godot/phase6_integration_smoke.gd` exercise Godot’s imported scene, clips, materials, helpers, LOD replacement, and player/AI intent bridge. |

The adapter exposes `socket_weapon`, `socket_projectile`,
`socket_camera_body`, `socket_camera_chest`, `socket_camera_head`, and
`socket_aim` as imported `BoneAttachment3D` helpers. `HeroCharacter` and its
camera target read these helpers so visual attachment follows the animated
skeleton. The attack/ability systems remain authoritative for target choice,
projectile instantiation, collision, damage, cooldowns, and status effects.
A manifest marker is a safe presentation signal only; it cannot create damage
or a second projectile.

## Godot 4 glTF import and coordinate conversion

Import the `.glb` files through Godot 4’s normal glTF scene importer with
animation import enabled. Keep the default extracted embedded-texture behavior
and untrimmed 30 FPS animation sampling used by the authored package. Do not
check generated `.godot` import artifacts into source control.

Godot 4.3 expands the source channel representation during import: it emits 47
rotation tracks per canonical clip, preserves the manifest's authored targets
and multi-key movement, and adds/collapses one-key rest-pose tracks as needed.
The adapter applies manifest loop policy because raw glTF animation extras do
not become arbitrary Godot loop metadata.

The authored package uses **X horizontal, Y depth, Z up**, with Lyra’s bow/front
facing source `-Y`. Godot gameplay uses Y up and forward `-Z`. At the
presentation root, `HeroPresentationAdapter` applies the proper orthonormal
basis with local axes:

```text
source X → Godot LEFT
source Y → Godot BACK
source Z → Godot UP
(x, y, z) → (-x, z, y)
```

This is a rotation (not a negative-scale mirror), keeps the bow/projectile
forward in Godot `-Z`, and keeps head/camera helpers above body helpers. Do not
bake a competing root-axis correction into a replacement GLB without updating
this contract and its engine tests.

## Animation and LOD rules

- The accepted canonical set is: `idle`, `idle_variation`, `walk`, `run`,
  `turn_left`, `turn_right`, `start_run`, `stop_run`, `basic_attack`,
  `basic_attack_recovery`, `attack_variant`, `charged_attack`, `hit_light`,
  `hit_heavy`, `knockback`, `stun`, `death`, `victory`, `spawn`, `skill_01`,
  `skill_02`, `skill_03`, and `ultimate`.
- `HeroAnimationDriver` maps gameplay actions into these named clips. The
  imported `AnimationPlayer` and runtime `AnimationTree` belong to the
  adapter; no gameplay node is reparented into the visual hierarchy.
- Semantic marker clocks are keyed by animation action iteration. They are
  reset by an explicit restart, retained across an LOD swap, and discarded on
  interruption so late/duplicate visual effects do not occur.
- A distance-policy swap preserves active clip/time where possible. If LOD1
  fails validation, LOD0 stays active and an import warning is emitted.

## Recommended mobile budgets (one on-screen hero)

| Budget | Target | Notes |
|---|---:|---|
| Hero triangles, LOD0 | 8k–14k | Favor bow/mantle silhouette over micro-armor geometry. |
| Hero triangles, LOD1 | 4k–7k | Use beyond normal combat readability range. |
| Materials | 3–5 | Current authored package imports three PBR groups. |
| Texture resolution | 1k body atlas / 512 weapon | ETC2/ASTC on device; avoid many unique masks. |
| Bones | ≤ 55 | Lyra imports 54 bones, including helper bones. |
| Skinned meshes | 1–3 | Merge static accessories where possible. |
| Persistent particles | 0–2 systems | Idle aura should remain a low-cost mesh/decal-like effect. |
| Burst particles | ≤ 40 visible | Pool projectile/impact VFX; avoid fullscreen alpha layers. |
| Dynamic lights | 0 per hero | Use emissive and baked/environment lighting for readability. |
| Audio voices | 4 spatial players | Already reflected by the Audio subtree. |

These are production targets, not an Android profiling result. Device profiling,
final VFX/SFX, multiplayer/replay synchronization, and final balance remain
later roadmap phases.

## Asset ownership

```text
character_final/      source/build pipeline and intermediate authored exports
character_animated/   accepted animated LOD0/LOD1 GLB packages + manifest
models/               future model variants and source-export notes
textures/             source/processed texture inputs
materials/            reusable Godot materials/shaders
animations/           imported clip assets + AnimationTree blend setup
weapons/              bow model / variants
vfx/                  effect scenes, materials, flipbooks
audio/                mastered SFX and localized VO
data/                 balance resources, separate from every visual asset
```
