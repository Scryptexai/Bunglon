# Phase 7 — Controller & Command Integration

## Gate status

**Complete at the real Godot 4.3 command-boundary gate.** This phase validates the
first post-import gameplay-facing boundary: one live `HeroCharacter` can receive
player desktop/touch intent, AI intent, or an external/replay-style packet without
coupling movement, abilities, targeting, or the imported GLB to a specific device.
It does **not** claim final mobile-device UX, network authority, combat balance, or
GPU visual QA.

## Scope and ownership

```text
Desktop keys / touch HUD     AI policy       external/replay producer
           │                    │                    │
           └──── InputSource ───┴──── CharacterCommand snapshot
                                             │
                                      CharacterController
                         ┌───────────────────┴───────────────────┐
                    MovementController          Targeting / BasicAttack / AbilityController
                         │                                      │
                    CharacterBody3D                     HeroAnimationDriver
                                                               │
                                                    HeroPresentationAdapter
                                                    imported AnimationTree
```

- `PlayerInputSource` maps WASD/Space/Tab/Q/E/R/F and the demo HUD touch bridge to
  the same `CharacterCommand` shape. Directional input is camera-relative; attack is
  a hold, while target/ability requests are one-shot edges.
- `AIInputSource` remains an intent producer only. It never obtains a separate
  combat, movement, or visual implementation.
- `CharacterController` selects exactly one source per physics tick. It normalizes a
  disposable command snapshot to planar unit movement/aim and routes only the named
  requests to existing modular systems.
- `submit_external_command()` copies the packet on submission and consumes it once.
  A caller can reuse/mutate its own packet after submission without changing the
  queued authoritative tick.
- A live control-mode change and controller disable clear touch holds, queued touch
  taps, AI decision state, queued external packets, movement velocity, and combat
  facing. A real physical keyboard state remains live by design when player control
  resumes.

This keeps the boundaries explicit: neither input source nor `CharacterController`
spawns a projectile, applies damage, moves the imported visual, or reads a GLB
animation marker. `BasicAttack`, `HeroAbility`, `MovementController`, and
`HeroPresentationAdapter` retain their respective authoritative/presentation roles.

## Implementation

| Component | Phase 7 responsibility |
|---|---|
| `scripts/control/character_command.gd` | Provides `snapshot()` normalization, input isolation, and duplicate/empty ability filtering. |
| `scripts/control/player_input_source.gd` | Adds `clear_mobile_input()` so stale touch state cannot replay after a mode/enable transition. |
| `scripts/control/ai_input_source.gd` | Adds `reset_decision_state()` for deterministic source changes. |
| `scripts/control/character_controller.gd` | Owns source switching, external-packet copy/one-tick consumption, neutral reset, and safe routing to movement/targeting/combat. |
| `tests/godot/phase7_controller_smoke.gd` | Uses the actual hero scene and imported GLB adapter for engine-facing assertions. |

## Engine evidence

Run the importer first when starting from a physically clean project, then execute:

```bash
GODOT_BIN=/tmp/godot-src-4.3/bin/godot.linuxbsd.editor.x86_64
"$GODOT_BIN" --headless --path . --editor --quit
"$GODOT_BIN" --headless --path . --script res://tests/godot/phase7_controller_smoke.gd
```

The recorded Godot 4.3 run exited `0` and printed
`PHASE7_CONTROLLER_SMOKE result=PASS`. It verified:

1. planar normalized snapshot copying; vertical input removal; boolean retention;
   duplicate/empty ability filtering; and post-copy producer mutation isolation;
2. runtime desktop action registration and forward camera-relative command mapping;
3. touch movement, held attack, one-shot target/ability requests, and explicit touch
   reset behavior;
4. AI mode does not consume queued player input, and inactive player input cannot
   activate an ability;
5. live mode-change notification plus clearing stale mobile and external intent;
6. a fresh external packet activating the shared `PhaseStepAbility`, retaining the
   submitted aim for the authoritative dash, and driving the imported `skill_02`
   presentation clip.

The run necessarily reports the known rendererless Godot dummy-mesh diagnostics;
those are not a rendered visual review. Phase 6 remains the import/visual adapter
record in [`PHASE_6_GODOT_INTEGRATION.md`](PHASE_6_GODOT_INTEGRATION.md).

## Deliberate boundary and next work

This gate proves the command path, not final input product quality. Still required:

- physical Android touch, safe-area, resize/orientation, accessibility, remapping,
  controller/gamepad, and latency testing;
- explicit replay/network sequence/authority and packet-loss behavior;
- separate next-gate validation of basic-attack, ability, targeting, hitbox/projectile,
  AI decision, world-navigation, balance, and device performance behavior;
- GPU-capable visual review and Android profiling before final production sign-off.
