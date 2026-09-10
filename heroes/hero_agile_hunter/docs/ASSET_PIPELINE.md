# Asset Pipeline & Mobile Budget

## Current runnable asset layer

The repository includes a native Godot modular 3D hero built in `HeroVisual`:

- `Skeleton3D` with named root/hips/spine/chest/head/arms/legs/hand bones.
- Rigid modular mesh pieces attached to bones, an energy bow, accessories, projectile marker, materials, and procedural state poses.
- Ten small 22.05 kHz mono WAV cues for draw/release/projectile/hit/skill/ultimate/damage/death/footstep/callout routing.
- Event-driven mesh bursts for spawn, idle aura, attack, projectile hit, skills, ultimate, hit, evade, and death.

This makes the character scene valid/runnable in a clean Godot checkout. It is not dependent on a missing DCC export or third-party model.

## Final art hand-off

Replace the native assembly with a single authored `lyra_vesper.glb` while preserving these contracts:

| Asset | Required naming / contract |
|---|---|
| Hero model | `models/lyra_vesper.glb`, one atlas-friendly body/armor material layout. |
| Skeleton | Preserve equivalent `root`, `hips`, `spine`, `chest`, `head`, `hand_l`, `hand_r`, feet bones. |
| Weapon | Separate `weapons/lyra_energy_bow.glb` or a stable `Weapon` attachment node. |
| Projectile socket | A `ProjectileOrigin` Marker3D/socket at bow grip/string center. |
| Animation clips | idle, idle_variation, walk, run, turn_left, turn_right, start_run, stop_run, basic_attack, basic_attack_recovery, attack_variant, charged_attack, hit_light, hit_heavy, knockback, stun, death, victory, spawn, skill_01, skill_02, skill_03, ultimate. |
| Materials | Separate logical skin, clothing, armor, weapon metal, leather, and emissive energy surfaces. |
| VFX | Replace mesh burst emitters with authored particle/flipbook assets only after checking fill-rate. |
| Audio | Replace cue WAVs with mastered SFX and localized VO under the same semantic event IDs. |

The imported model should attach under `Visual/CharacterModel`; do not move gameplay collision/hurtbox nodes into the visual hierarchy.

## Recommended mobile budgets (one on-screen hero)

| Budget | Target | Notes |
|---|---:|---|
| Hero triangles, LOD0 | 8k–14k | Favor bow/mantle silhouette over micro-armor geometry. |
| Hero triangles, LOD1 | 4k–7k | Use beyond normal combat readability range. |
| Materials | 3–5 | Skin, suit/armor atlas, weapon, emissive, optional transparent mantle. |
| Texture resolution | 1k body atlas / 512 weapon | ETC2/ASTC on device; avoid many unique masks. |
| Bones | ≤ 55 | Current native rig is deliberately much lower; reserve bones for final facial/hair support. |
| Skinned meshes | 1–3 | Merge static accessories where possible. |
| Persistent particles | 0–2 systems | Idle aura should remain a low-cost mesh/decal-like effect. |
| Burst particles | ≤ 40 visible | Pool projectile/impact VFX; avoid fullscreen alpha layers. |
| Dynamic lights | 0 per hero | Use emissive and baked/environment lighting for readability. |
| Audio voices | 4 spatial players | Already reflected by the Audio subtree. |

## Import settings

- Use glTF 2.0 `.glb` for Godot 4 import.
- Bake transforms and set meters as units before export.
- Apply a single consistent forward direction (`-Z` in Godot) and test bow projectile socket alignment.
- Import 30 FPS or 60 FPS clips as appropriate; gameplay release timing must be driven by explicit animation events or the ability/basic-attack timeline, not visual frame guesses.
- Enable mesh LODs and compression appropriate to the target device tier.

## Asset ownership

```text
models/       mesh + rig source/export
textures/     source/processed texture inputs
materials/    reusable Godot materials/shaders
animations/   imported clip assets + AnimationTree blend setup
weapons/      bow model / variants
vfx/          effect scenes, materials, flipbooks
audio/        mastered SFX and localized VO
data/         balance resources, separate from every visual asset
```
