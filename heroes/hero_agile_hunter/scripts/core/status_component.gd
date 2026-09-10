class_name StatusComponent
extends Node
## General status container used by movement, damage and future buff/debuff systems.

signal status_applied(status_id: StringName, duration: float, magnitude: float)
signal status_expired(status_id: StringName)

var _effects: Dictionary = {}


func apply_status(status_id: StringName, duration: float, magnitude: float = 1.0, source: Node = null) -> void:
	var existing: Dictionary = _effects.get(status_id, {})
	_effects[status_id] = {
		"remaining": maxf(float(existing.get("remaining", 0.0)), duration),
		"magnitude": maxf(magnitude, float(existing.get("magnitude", 0.0))),
		"source": source,
	}
	status_applied.emit(status_id, duration, magnitude)


func remove_status(status_id: StringName) -> void:
	if _effects.erase(status_id):
		status_expired.emit(status_id)


func has_status(status_id: StringName) -> bool:
	return _effects.has(status_id)


func get_magnitude(status_id: StringName, fallback: float = 0.0) -> float:
	var effect: Dictionary = _effects.get(status_id, {})
	return float(effect.get("magnitude", fallback))


func is_movement_locked() -> bool:
	return has_status(&"root") or has_status(&"stun") or has_status(&"death")


func movement_multiplier() -> float:
	if has_status(&"slow"):
		return clampf(1.0 - get_magnitude(&"slow"), 0.1, 1.0)
	return 1.0


func is_damage_immune() -> bool:
	return has_status(&"phase_shift") or has_status(&"invulnerable")


func _physics_process(delta: float) -> void:
	var ids: Array = _effects.keys()
	for status_id: Variant in ids:
		var effect: Dictionary = _effects[status_id]
		effect["remaining"] = float(effect["remaining"]) - delta
		if float(effect["remaining"]) <= 0.0:
			_effects.erase(status_id)
			status_expired.emit(status_id)
		else:
			_effects[status_id] = effect
