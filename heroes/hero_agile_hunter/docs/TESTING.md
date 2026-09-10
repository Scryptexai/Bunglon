# Validation Checklist

## Automated checks

Run from project root:

```bash
python3 -m unittest discover -s tests -v
# When gdtoolkit is installed:
gdformat --check -l 160 heroes demo
gdlint heroes demo
```

The repository was statically checked with GDScript Toolkit. A local Godot executable was not present in the implementation sandbox, so final render/physics validation must be run in a Godot 4.x editor or CI runner.

## Godot runtime smoke test

1. Open `demo/scenes/demo_arena.tscn` and run it.
2. Confirm the Player Lyra has a cyan bow, asymmetric mantle, visor, chest core, and no missing meshes/materials.
3. Confirm the camera follows `CameraTarget/Chest`; rotate/move Lyra and verify combat systems never change camera ownership.
4. Move with `WASD`: idle → walk/run → stop should blend through responsive turns. Confirm Vantage increments while moving fast.
5. Press/hold `Space` near an enemy: check draw → projectile release → Hurtbox hit → health change; basic attacks must not require mesh collision.
6. Use each skill with a target selected (`Tab`):
   - Q fires three arrow fan.
   - E dashes and ignores an incoming hit during its phase window.
   - R roots the first enemy hit.
   - F has a clear locked cast, three projectiles, final radial burst, slow, and recovery.
7. Let the AI Lyra select and attack player. Confirm it uses the same `CharacterController`/combat core but `AIInputSource` rather than player input.
8. Kill either hero: target selection drops it, movement stops, ongoing abilities cancel, death VFX/audio play, and Hurtbox no longer resolves damage.
9. On a touch-capable build verify the directional / attack / ability buttons feed `PlayerInputSource` and do not bypass gameplay.

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
| AI mode | `control_mode = ai` never calls PlayerInputSource. |

## Production sign-off still required

- Profile draw calls, skinning, particle overdraw, and thermal behavior on representative low/mid/high Android targets.
- Replace synthesized cue audio with final mastered SFX/VO, then check mix and localization.
- Import production GLB/animations and map animation-event timing to gameplay release windows.
- Author a real test scene with navigation/obstacle geometry and test dash/projectile collision edge cases.
- Run multiplayer authority/replay tests if those input sources are enabled by the game layer.
