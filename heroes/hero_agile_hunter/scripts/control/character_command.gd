class_name CharacterCommand
extends RefCounted
## Engine-neutral intent packet. Player, AI, network and replay all produce this shape.

var move_direction: Vector3 = Vector3.ZERO
var aim_direction: Vector3 = Vector3.ZERO
var request_attack: bool = false
var request_target_next: bool = false
var requested_abilities: Array[StringName] = []


func request_ability(slot: StringName) -> void:
	if not requested_abilities.has(slot):
		requested_abilities.append(slot)
