# Validation Checklist

## Automated checks

Run the static contract suite from the project root:

```bash
python3 -m unittest discover -s tests -v
# When gdtoolkit is installed:
gdformat --check -l 160 heroes demo tests
gdlint heroes demo tests
```

For real Godot 4.3 engine checks, import once before running scripts when beginning
from a clean workspace:

```bash
GODOT_BIN=/tmp/godot-src-4.3/bin/godot.linuxbsd.editor.x86_64
"$GODOT_BIN" --headless --path . --editor --quit
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase6_import_probe.gd
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase6_integration_smoke.gd
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase7_controller_smoke.gd
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase8_basic_attack_smoke.gd
```

The local Godot 4.3 editor/headless binary passed the Phase 6 importer/presentation
smokes, Phase 7 controller smoke, and Phase 8 basic-attack/projectile smoke. This
sandbox's engine is rendererless, so its expected dummy-mesh diagnostics are not a
GPU render or Android performance result. The exact assertions are retained in
[`PHASE_6_GODOT_INTEGRATION.md`](PHASE_6_GODOT_INTEGRATION.md),
[`PHASE_7_CONTROLLER_INTEGRATION.md`](PHASE_7_CONTROLLER_INTEGRATION.md), and
[`PHASE_8_BASIC_ATTACK_INTEGRATION.md`](PHASE_8_BASIC_ATTACK_INTEGRATION.md).

## Godot runtime smoke test

1. Open `demo/scenes/demo_arena.tscn` and run it in a GPU-capable Godot editor.
2. Confirm the Player Lyra has the imported cyan bow, asymmetric mantle, visor, chest
   core, and no missing meshes/materials.
3. Confirm the camera follows imported `socket_camera_chest`; rotate/move Lyra and
   verify combat systems never change camera ownership.
4. Move with `WASD`: idle → walk/run → stop should play responsive imported clips.
   Confirm Vantage increments while moving fast.
5. Press/hold `Space` near an enemy: check draw → authoritative projectile release →
   Hurtbox hit → health change; basic attacks must not require mesh collision.
6. Use each skill with a target selected (`Tab`):
   - Q fires three arrow fan.
   - E dashes and ignores an incoming hit during its phase window.
   - R roots the first enemy hit.
   - F has a clear locked cast, three projectiles, final radial burst, slow, and recovery.
7. Let the AI Lyra select and attack player. Confirm it uses the same
   `CharacterController`/combat core but `AIInputSource` rather than player input.
8. Change control mode in a test harness while touch actions/external packets are
   queued: stale holds/taps/packets must not replay under the new owner.
9. Kill either hero: target selection drops it, movement stops, ongoing abilities
   cancel, death VFX/audio play, and Hurtbox no longer resolves damage.
10. On a touch-capable build verify the directional / attack / ability buttons feed
    `PlayerInputSource`, respect safe areas/orientation, and do not bypass gameplay.

## Regression matrix

| Case | Expected result |
|---|---|
| No target + attack / targeted skill | No projectile/cost; UI remains responsive. |
| Target lost during basic windup | Attack cancels cleanly without a stale reference. |
| Target dies | `DamageReceiver.is_targetable()` becomes false and targeting reacquires/loss event fires. |
| Phase Step + incoming projectile | `StatusComponent.phase_shift` causes `DamageReceiver` to reject damage. |
| Root / stun status | Movement intent is accepted but `MovementController` resolves zero movement. |
| Multiple targets in ultimate impact | Initial hit applies once; radial hit excludes initial target to avoid double-damage. |
| Modifier removal | Source-scoped modifier key can be removed without rebuilding the HeroStats resource. |
| AI mode | `control_mode = ai` never calls `PlayerInputSource`. |
| Control-mode switch | Queued touch/external intent, velocity, and combat facing are cleared before the new source ticks. |
| External packet mutation | A packet is normalized/copied on submission; producer mutation after submit cannot alter the consumed command. |
| Direct friendly/far basic target | `BasicAttack` rejects it itself; no cooldown or pending projectile begins. |
| Basic release marker | One gameplay projectile comes from the timer/socket; the imported marker supplies cosmetic feedback only. |
| Target lost during basic windup | Pending target/event are cleared; no stale projectile or `attack_fired` report follows. |

## Production sign-off still required

- Run GPU-capable 360° visual review at gameplay/close-up distances using the imported
  GLBs; the rendererless engine smoke cannot supply this.
- Profile draw calls, skinning, particle overdraw, texture transcode/residency, input
  latency, and thermal behavior on representative low/mid/high Android targets.
- Validate physical touchscreen safe areas, orientation/resizing, accessibility,
  remapping, and optional controller/gamepad behavior.
- Author a real test scene with navigation/obstacle geometry and test dash/projectile
  collision edge cases.
- Run dedicated basic attack, ability, targeting, AI-decision, world-interaction,
  balance, multiplayer authority, and replay tests as their roadmap gates are reached.
- Replace synthesized cue audio with final mastered SFX/VO, then check mix and
  localization.
