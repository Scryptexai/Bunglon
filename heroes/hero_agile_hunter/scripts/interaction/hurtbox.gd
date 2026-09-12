class_name Hurtbox
extends Area3D
## Collision surface that receives damage. It deliberately knows nothing about attacks.

var damage_receiver: DamageReceiver


func initialize(receiver: DamageReceiver) -> void:
	damage_receiver = receiver
	add_to_group("hurtbox")


func receive_damage(event: DamageEvent) -> bool:
	if damage_receiver == null:
		return false
	return damage_receiver.receive_damage(event)


func get_combatant() -> Node3D:
	return CombatUtil.get_combatant_root(self)
