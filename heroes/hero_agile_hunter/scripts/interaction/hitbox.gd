class_name Hitbox
extends Area3D
## Stateless radial hit query. Area3D remains available for authored collision windows;
## radial queries use Hurtbox positions so the visual mesh is never combat authority.

signal hit_applied(target: Node3D, event: DamageEvent)


func apply_radial_damage(center: Vector3, radius: float, event: DamageEvent, max_targets: int = -1, ignored_target: Node3D = null) -> int:
	var applied := 0
	for candidate: Node in get_tree().get_nodes_in_group("hurtbox"):
		var hurtbox := candidate as Hurtbox
		if hurtbox == null:
			continue
		var target := hurtbox.get_combatant()
		if target == ignored_target or not CombatUtil.is_valid_hostile(event.source, target):
			continue
		if target.global_position.distance_to(center) > radius:
			continue
		var per_target := event.clone_for(target)
		per_target.impact_position = target.global_position
		if hurtbox.receive_damage(per_target):
			applied += 1
			hit_applied.emit(target, per_target)
			if max_targets > 0 and applied >= max_targets:
				break
	return applied
