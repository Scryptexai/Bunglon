class_name HeroCameraTarget
extends Node3D
## Read-only follow/aim anchor service for an external camera system.


func get_body_point() -> Vector3:
	return _point_position("Body", global_position)


func get_chest_point() -> Vector3:
	return _point_position("Chest", global_position + Vector3.UP * 1.35)


func get_head_point() -> Vector3:
	return _point_position("Head", global_position + Vector3.UP * 2.05)


func get_aim_point() -> Vector3:
	return _point_position("AimPoint", global_position + Vector3.UP * 1.42)


func _point_position(point_name: String, fallback: Vector3) -> Vector3:
	var point := get_node_or_null(point_name) as Node3D
	return point.global_position if point != null else fallback
