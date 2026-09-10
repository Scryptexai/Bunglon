class_name CombatUtil
extends RefCounted
## Cross-scene combat lookup helpers. Gameplay never depends on a visual mesh path.


static func get_damage_receiver(candidate: Node) -> DamageReceiver:
	if candidate == null or not is_instance_valid(candidate):
		return null
	if candidate is DamageReceiver:
		return candidate as DamageReceiver
	if candidate.has_method("get_damage_receiver"):
		var receiver: Variant = candidate.call("get_damage_receiver")
		if receiver is DamageReceiver:
			return receiver as DamageReceiver
	var direct: Node = candidate.get_node_or_null("Combat/DamageReceiver")
	if direct is DamageReceiver:
		return direct as DamageReceiver
	var nested: Node = candidate.get_node_or_null("DamageReceiver")
	if nested is DamageReceiver:
		return nested as DamageReceiver
	return null


static func get_combatant_root(candidate: Node) -> Node3D:
	if candidate == null or not is_instance_valid(candidate):
		return null
	if candidate is Node3D and candidate.is_in_group("targetable"):
		return candidate as Node3D
	var cursor: Node = candidate
	while cursor != null:
		if cursor is Node3D and cursor.is_in_group("targetable"):
			return cursor as Node3D
		cursor = cursor.get_parent()
	return null


static func get_team_id(candidate: Node) -> int:
	var root := get_combatant_root(candidate)
	if root != null and root.has_method("get_team_id"):
		return int(root.call("get_team_id"))
	var team: Node = root.get_node_or_null("Team") if root != null else null
	if team is TeamComponent:
		return (team as TeamComponent).team_id
	return -999


static func get_aim_position(candidate: Node) -> Vector3:
	if candidate == null or not is_instance_valid(candidate):
		return Vector3.ZERO
	if candidate.has_method("get_aim_position"):
		var aim_position: Variant = candidate.call("get_aim_position")
		if aim_position is Vector3:
			var resolved_aim: Vector3 = aim_position
			return resolved_aim
	if candidate is Node3D:
		return (candidate as Node3D).global_position + Vector3.UP * 1.2
	return Vector3.ZERO


static func is_valid_hostile(source: Node, candidate: Node) -> bool:
	var source_root := get_combatant_root(source)
	var target_root := get_combatant_root(candidate)
	if source_root == null or target_root == null or source_root == target_root:
		return false
	if get_team_id(source_root) == get_team_id(target_root):
		return false
	var receiver := get_damage_receiver(target_root)
	return receiver != null and receiver.is_targetable()
