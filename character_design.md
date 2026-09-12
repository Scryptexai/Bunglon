# CHARACTER DESIGN — Lyra Vesper, The Lumen Huntress

**Production phase:** 1 — Character Design

**Design status:** Reference package complete; this document is the modeling lock for Phase 2.

**Role:** Agile ranged hunter / marksman

**Art direction:** Original stylized 3D mobile-MOBA hero; readable at gameplay distance and credible at close inspection.

> The visual reference package is original project concept art. It communicates construction and intent for the 3D asset; it is not a final 3D model, a texture, or a license to use primitive meshes as final geometry.

## 1. Character premise

Lyra Vesper is a long-range pathfinder who hunts by reading residual light left in a battlefield. Her energy bow turns those traces into precision bolts. Her visual design must communicate **speed, aim discipline, and celestial navigation**—not a heavy knight, generic sci-fi soldier, or an existing game character.

The design uses four permanent recognition anchors:

1. **Comet-tail ponytail:** a high, heavy blue-black ponytail sweeping into a cyan-lit tapered arc.
2. **Asymmetric aurora mantle:** a violet star-speckled short mantle anchored on her left shoulder only.
3. **Crescent compass bow:** an open asymmetric vertical crescent with a circular star-compass riser and three floating cyan shards.
4. **Diamond chest core:** a bright cyan diamond set in pale-gold hardware at the sternum.

A player should recognize Lyra from the ponytail + mantle + bow outline even when materials and facial detail are not visible.

## 2. Visual identity and proportions

| Attribute | Locked decision |
|---|---|
| Age presentation | Adult woman; assured, focused, athletic—not childlike or sexualized. |
| Body language | Compact runner’s posture: light forward readiness, level shoulders, long stable legs. |
| Hero proportions | Approximately 7.25 heads high; mobile-MOBA readable head, hands, boots, and weapon silhouette. |
| Face | Oval face, high cheekbones, a narrow straight nose, strong brows, and a reserved expression. |
| Facial mark | Fine constellation freckles travel across the left cheekbone. |
| Hair | Deep blue-black, swept asymmetric fringe, high comet-tail ponytail with cyan tips. |
| Vision tech | Thin cyan lens/visor accent around the right eye with small pale-gold ear hardware. |
| Weapon stance | Bow is tall, almost body-height, held on the right side in neutral views. |

## 3. Costume construction

### Head and neck

The face remains readable; no helmet obscures it. The swept fringe creates a deliberate diagonal across the forehead. A high narrow collar frames the neck without limiting an archer’s head turn.

### Torso and mantle

The base is a midnight-indigo fitted hunt suit with visible panel breaks following the ribcage and waist. The glowing diamond core sits above a tapering cyan energy channel. The **left-only** mantle attaches with a pale-gold clasp and falls behind the arm; its inner surface reads as a restrained violet aurora/starlight pattern. It is short enough not to hide leg movement or weapon release.

### Arms and hands

Cobalt forearm guards have pale-gold perimeter plates and cyan inset channels. Gloves remain compact and articulated; the bow hand must read clearly in a close-up and stay practical for finger/hand rigging.

### Waist and legs

A slim belt supports a compact photon-arrow quiver/cell pack at the rear-right hip. The legs use matte indigo panels with cyan lines that direct the eye downward into layered cobalt shin guards. Boots have a stable, lightweight silhouette with low heel and split armor panels—not heavy greaves.

## 4. Material and color language

| Purpose | Color / material | Runtime intention |
|---|---|---|
| Base suit | Midnight indigo `#171B45`, matte technical weave | Largest contiguous read; low specular noise. |
| Armor | Cobalt `#314C99`, satin painted composite | Segmented protection at limbs and selected torso zones. |
| Mantle | Aurora violet `#7446BC`, woven fabric with sparse inner star flecks | Left-side motion and asymmetry; avoid alpha-heavy overdraw if possible. |
| Energy | Lumen cyan `#54E8FF`, controlled emissive | Chest core, bow string, line accents, projectile cues. |
| Hardware | Pale gold `#D6BA71`, brushed metal | Small focal trim and attachment points. |
| Skin | Warm umber `#9B674D`, stylized soft PBR | Natural facial contrast against blue/violet costume. |
| Hair | Blue-black `#111A42`, cyan-tinted ends | Large graphic silhouette, not transparent individual strands. |

The palette intentionally reserves cyan emission for gameplay-readable energy sources. Do not add broad cyan glow to unrelated armor panels.

## 5. Weapon: Aster Arc

**Aster Arc** is Lyra’s original energy bow. Its construction language must be preserved:

- tall asymmetric crescent outer profile;
- midnight-indigo inner frame and pale-gold blade-like outer edge;
- circular star-compass riser centered at the grip;
- taut cyan energy string rather than a conventional physical string;
- three small cyan light shards that hover near the upper limb;
- a clear release point for an arrow/projectile socket.

The bow is neither a plain recurve bow nor a rifle. It should remain legible in an icon, at gameplay camera distance, and during draw/release animation.

## 6. Required reference package

All required Phase 1 views are available under `references/`.

| View | File | Modeling use |
|---|---|---|
| Key concept | `concept/lyra_master_concept.png` | Overall intended finish, material balance, and heroic read. |
| Front | `references/lyra_turnaround_front.png` | Centerline, chest core, torso/leg panel layout, bow scale. |
| Back | `references/lyra_turnaround_back.png` | Ponytail attachment, mantle back, rear armor, quiver, boot backs. |
| Left | `references/lyra_turnaround_left.png` | Mantle silhouette and profile depth. |
| Right | `references/lyra_turnaround_right.png` | Quiver, non-mantle profile, bow relationship to body. |
| 3/4 front | `references/lyra_three_quarter_front.png` | Face, body depth, layered armor, bow grip. |
| 3/4 back | `references/lyra_three_quarter_back.png` | Rear construction, mantle fall, hair and bow clearance. |
| Face | `references/lyra_face_sheet.png` | Facial planes, freckles, lens accent, fringe, ear hardware. |
| Weapon | `references/lyra_weapon_sheet.png` | Separate Aster Arc mesh, material zones, energy string. |
| Costume details | `references/lyra_costume_details.png` | Core, mantle clasp/fabric, gauntlet, shin boot construction. |

The front image contains generated annotation artifacts around empty studio space; those are **not** lettering or decals on Lyra and must not be modeled or textured. This written specification controls any disagreement between views.

## 7. Phase 2 modeling handoff

### Must model

- complete front, side, back, underside, and 360-degree body geometry;
- separate or cleanly segmented head, hair, suit, armor, mantle, boots, quiver, accessories, and Aster Arc;
- face with eye sockets/lids, nose bridge, lips, and readable freckle texture zone;
- closed geometry and purposeful topology at all body bends;
- an actual mesh and materials/UVs.

### Must not do

- ship a Godot primitive assembly or an unmodified generic mannequin;
- model only the camera-facing front;
- replace the bow with a generic bow/rifle;
- symmetrize away the left mantle or ponytail asymmetry;
- hide unresolved anatomy under a cape or armor slab;
- turn the face into an anonymous smooth mask.

## 8. Phase 1 acceptance review

- [x] Original agile ranged-hunter identity is defined.
- [x] Humanoid body, face, hair, costume, weapon, and material language are specified.
- [x] Front, back, left, right, 3/4 front, and 3/4 back references exist.
- [x] Face, weapon, and costume-detail references exist.
- [x] Silhouette has three independent anchors: ponytail, left mantle, Aster Arc.
- [x] Color/material language supports mobile-MOBA readability.
- [x] Phase 2 handoff explicitly rejects primitive/blocky final characters.

**Phase 1 result:** Pass. The design was handed off to the authored Phase 2 mesh at [`character_final/lyra_vesper_phase2.glb`](character_final/lyra_vesper_phase2.glb), then to the measured Phase 3 runtime LODs in [`character_optimized/`](character_optimized/) and [`character_lod/`](character_lod/), the Phase 4 skinned LOD package in [`character_rigged/`](character_rigged/), and Phase 5 animated exports in [`character_animated/`](character_animated/). Phase 6 has completed the Godot engine-import presentation gate; its implementation/evidence is in [`heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md`](heroes/hero_agile_hunter/docs/PHASE_6_GODOT_INTEGRATION.md).
