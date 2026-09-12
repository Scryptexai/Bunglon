# Models

Lyra Vesper’s active runtime model is the authored Phase 5 glTF package, not a
procedural Godot mesh assembly:

- `../../character_animated/lyra_vesper_animated.glb` — LOD0, 54-bone skinned
  character, 23 named clips, embedded PBR textures, and helper bones.
- `../../character_animated/lyra_vesper_animated_lod1.glb` — matching reduced
  geometry LOD with the same skeleton, clip timing, and helper contract.
- `../../character_animated/animation_manifest.json` — source of the canonical
  clip durations, loop policy, semantic presentation markers, and helper
  contract.

`HeroPresentationAdapter` instantiates these files below `HeroCharacter/Visual`
at runtime. It refuses a LOD swap unless Godot has imported matching skeleton,
clip, helper, material, and texture contracts. Keep the authored source axis
contract (X horizontal, Y depth, Z up; bow/front is `-Y`) in exported GLB files;
the adapter applies the documented Godot conversion at the presentation root.

The model directory remains the place for future source exports and variants.
Do not restore a primitive or generated runtime fallback here.
