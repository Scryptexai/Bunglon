class_name DetectionSensor
extends Area3D
## Physics-assisted candidate cache. TargetingComponent owns scoring and final selection.

signal candidate_entered(candidate: Node3D)
signal candidate_exited(candidate: Node3D)

var _candidates: Array[Node3D] = []


func _ready() -> void:
	area_entered.connect(_on_area_entered)
	area_exited.connect(_on_area_exited)
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)


func get_candidates() -> Array[Node3D]:
	var valid: Array[Node3D] = []
	for candidate: Node3D in _candidates:
		if is_instance_valid(candidate):
			valid.append(candidate)
	_candidates = valid
	return valid


func _register(candidate: Node) -> void:
	var root := CombatUtil.get_combatant_root(candidate)
	if root == null or _candidates.has(root):
		return
	_candidates.append(root)
	candidate_entered.emit(root)


func _unregister(candidate: Node) -> void:
	var root := CombatUtil.get_combatant_root(candidate)
	if root == null or not _candidates.has(root):
		return
	_candidates.erase(root)
	candidate_exited.emit(root)


func _on_area_entered(area: Area3D) -> void:
	_register(area)


func _on_area_exited(area: Area3D) -> void:
	_unregister(area)


func _on_body_entered(body: Node3D) -> void:
	_register(body)


func _on_body_exited(body: Node3D) -> void:
	_unregister(body)
