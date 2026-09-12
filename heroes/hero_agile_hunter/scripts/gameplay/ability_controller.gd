class_name AbilityController
extends Node
## Slot registry and casting gateway. Individual mechanics stay inside ability components.

signal ability_registered(slot_id: StringName, ability: HeroAbility)
signal ability_requested(slot_id: StringName, accepted: bool)

var hero: HeroCharacter
var active_ability: HeroAbility
var _abilities: Dictionary = {}


func initialize(context: Dictionary, ability_root: Node) -> void:
	hero = context.get("hero") as HeroCharacter
	_abilities.clear()
	if ability_root == null:
		push_error("AbilityController requires an Abilities node.")
		return
	for child: Node in ability_root.get_children():
		if child is HeroAbility:
			var ability := child as HeroAbility
			ability.initialize(context)
			ability.cast_started.connect(_on_ability_cast_started)
			ability.finished.connect(_on_ability_finished)
			ability.failed.connect(_on_ability_failed)
			_abilities[ability.slot_id] = ability
			ability_registered.emit(ability.slot_id, ability)


func try_activate(slot_id: StringName, target: Node3D, aim_direction: Vector3) -> bool:
	var ability := get_ability(slot_id)
	if ability == null:
		ability_requested.emit(slot_id, false)
		return false
	if active_ability != null and active_ability != ability and active_ability.phase != HeroAbility.Phase.READY:
		ability_requested.emit(slot_id, false)
		return false
	var accepted := ability.try_activate(target, aim_direction)
	ability_requested.emit(slot_id, accepted)
	return accepted


func is_basic_attack_allowed() -> bool:
	return active_ability == null or not active_ability.blocks_basic_attack


func get_ability(slot_id: StringName) -> HeroAbility:
	return _abilities.get(slot_id) as HeroAbility


func get_cooldown_ratio(slot_id: StringName) -> float:
	var ability := get_ability(slot_id)
	return ability.cooldown_ratio() if ability != null else 1.0


func cancel_all(reason: StringName = &"owner_disabled") -> void:
	for ability: Variant in _abilities.values():
		(ability as HeroAbility).cancel(reason)
	active_ability = null


func _on_ability_cast_started(ability: HeroAbility, _target: Node3D) -> void:
	active_ability = ability


func _on_ability_finished(ability: HeroAbility) -> void:
	if active_ability == ability:
		active_ability = null


func _on_ability_failed(ability: HeroAbility, _reason: StringName) -> void:
	if active_ability == ability and ability.phase == HeroAbility.Phase.READY:
		active_ability = null
