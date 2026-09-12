# Weapons

Lyra’s active Aster Arc energy bow is authored inside the Phase 5 animated GLB
package and follows the imported `socket_weapon` helper. The authoritative
projectile presentation origin is the matching imported `socket_projectile`
helper, resolved by `HeroPresentationAdapter` under `HeroCharacter/Visual`.

`HeroCharacter` reads that helper when it creates its one authoritative gameplay
projectile. The adapter never creates a duplicate projectile from a visual
release marker. Any future bow variant must retain the `socket_weapon` →
`socket_projectile` attachment contract, stay readable in idle/draw/release,
and pass the Phase 6 Godot helper/animation probe.
