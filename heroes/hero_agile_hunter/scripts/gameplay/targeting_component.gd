class_name TargetingComponent
extends Node
## Target selection is independent from attack and works for player, AI, replay, or network input.

signal target_changed(previous: Node3D, current: Node3D)
signal target_lost(previous: Node3D)

@export var acquisition_radius: float = 26.0
@export var rescan_interval: float = 0.15

var character: Node3D
var sensor: DetectionSensor
var current_target: Node3D
var selected_target: Node3D
var _rescan_remaining: float = 0.0


func initialize(owner_character: Node3D, detection_sensor: DetectionSensor) -> void:
	character = owner_character
	sensor = detection_sensor


func _physics_process(delta: float) -> void:
	if character == null:
		return
	_rescan_remaining -= delta
	if _rescan_remaining > 0.0:
		return
	_rescan_remaining = rescan_interval
	_refresh_target()


func get_target(max_range: float = -1.0) -> Node3D:
	var range_limit := acquisition_radius if max_range < 0.0 else max_range
	if _is_candidate_valid(selected_target, range_limit):
		return selected_target
	if _is_candidate_valid(current_target, range_limit):
		return current_target
	return acquire_nearest(range_limit)


func acquire_nearest(max_range: float = -1.0) -> Node3D:
	var range_limit := acquisition_radius if max_range < 0.0 else max_range
	var best: Node3D
	var best_score := INF
	for candidate: Node3D in _collect_candidates():
		if not _is_candidate_valid(candidate, range_limit):
			continue
		var distance := character.global_position.distance_squared_to(candidate.global_position)
		var priority := float(candidate.get_meta("target_priority", 0.0))
		var score := distance - priority * 100.0
		if score < best_score:
			best = candidate
			best_score = score
	_set_current_target(best)
	return best


func select_target(target: Node3D) -> bool:
	if not _is_candidate_valid(target, acquisition_radius):
		return false
	selected_target = target
	_set_current_target(target)
	return true


func clear_selected_target() -> void:
	selected_target = null
	_refresh_target()


func select_next_target() -> Node3D:
	var candidates: Array[Node3D] = []
	for candidate: Node3D in _collect_candidates():
		if _is_candidate_valid(candidate, acquisition_radius):
			candidates.append(candidate)
	if candidates.is_empty():
		_set_current_target(null)
		return null
	candidates.sort_custom(
		func(a: Node3D, b: Node3D) -> bool:
			return character.global_position.distance_squared_to(a.global_position) < character.global_position.distance_squared_to(b.global_position)
	)
	var index := candidates.find(current_target)
	var next_target := candidates[(index + 1) % candidates.size()]
	selected_target = next_target
	_set_current_target(next_target)
	return next_target


func has_enemy_in_range(range_limit: float) -> bool:
	return get_target(range_limit) != null


func _refresh_target() -> void:
	if _is_candidate_valid(selected_target, acquisition_radius):
		_set_current_target(selected_target)
		return
	selected_target = null
	if not _is_candidate_valid(current_target, acquisition_radius):
		acquire_nearest(acquisition_radius)


func _collect_candidates() -> Array[Node3D]:
	var candidates: Array[Node3D] = []
	if sensor != null:
		for candidate: Node3D in sensor.get_candidates():
			if not candidates.has(candidate):
				candidates.append(candidate)
	# The group fallback keeps targeting usable with authored, streamed, or non-physics targets.
	for candidate: Node in get_tree().get_nodes_in_group("targetable"):
		var root := CombatUtil.get_combatant_root(candidate)
		if root != null and not candidates.has(root):
			candidates.append(root)
	return candidates


func _is_candidate_valid(candidate: Node3D, range_limit: float) -> bool:
	if candidate == null or not is_instance_valid(candidate) or character == null:
		return false
	if not CombatUtil.is_valid_hostile(character, candidate):
		return false
	return character.global_position.distance_to(candidate.global_position) <= range_limit


func _set_current_target(next_target: Node3D) -> void:
	if current_target == next_target:
		return
	var previous := current_target
	current_target = next_target
	target_changed.emit(previous, current_target)
	if previous != null and current_target == null:
		target_lost.emit(previous)
