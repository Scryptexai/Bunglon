class_name CharacterCommand
extends RefCounted
## Engine-neutral intent packet. Player, AI, network and replay all produce this shape.
##
## Commands are disposable frame snapshots. Controller-side normalization keeps an
## external/replay producer from injecting vertical, oversized, or non-finite movement
## into the authoritative locomotion layer.

var move_direction: Vector3 = Vector3.ZERO
var aim_direction: Vector3 = Vector3.ZERO
var request_attack: bool = false
var request_target_next: bool = false
var requested_abilities: Array[StringName] = []


func request_ability(slot: StringName) -> void:
	if not slot.is_empty() and not requested_abilities.has(slot):
		requested_abilities.append(slot)


func snapshot() -> CharacterCommand:
	var copied := CharacterCommand.new()
	copied.move_direction = _planar_unit(move_direction)
	copied.aim_direction = _planar_unit(aim_direction)
	copied.request_attack = request_attack
	copied.request_target_next = request_target_next
	for slot: StringName in requested_abilities:
		copied.request_ability(slot)
	return copied


static func _planar_unit(direction: Vector3) -> Vector3:
	if not direction.is_finite():
		return Vector3.ZERO
	direction.y = 0.0
	return direction.normalized() if direction.length_squared() > 0.0001 else Vector3.ZERO
