class_name DamageEvent
extends RefCounted
## Immutable-at-dispatch combat payload.
##
## Attack systems construct this payload, passive/ability systems may enrich it before
## dispatch, and DamageReceiver is the only component that resolves it into HP loss.

enum DamageType {
	PHYSICAL,
	ENERGY,
	TRUE,
}

var source: Node
var target: Node
var amount: float = 0.0
var damage_type: DamageType = DamageType.PHYSICAL
var critical: bool = false
var critical_multiplier: float = 1.0
var ability_id: StringName = &""
var attack_source: StringName = &""
var modifiers: Dictionary = {}
var metadata: Dictionary = {}
var status_payload: Dictionary = {}
var impact_position: Vector3 = Vector3.ZERO


func clone_for(new_target: Node) -> DamageEvent:
	var clone := DamageEvent.new()
	clone.source = source
	clone.target = new_target
	clone.amount = amount
	clone.damage_type = damage_type
	clone.critical = critical
	clone.critical_multiplier = critical_multiplier
	clone.ability_id = ability_id
	clone.attack_source = attack_source
	clone.modifiers = modifiers.duplicate(true)
	clone.metadata = metadata.duplicate(true)
	clone.status_payload = status_payload.duplicate(true)
	clone.impact_position = impact_position
	return clone


func final_raw_amount() -> float:
	return maxf(0.0, amount * (critical_multiplier if critical else 1.0))
