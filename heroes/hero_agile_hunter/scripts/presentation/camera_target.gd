class_name HeroCameraTarget
extends Node3D
## Read-only follow/aim anchor service for an external camera system.
##
## Phase 6 binds this facade to imported Lyra helper bones. The editor-authored Marker3D
## children remain only as resilient fallbacks when inspecting an incomplete asset import.

var _visual_adapter: HeroPresentationAdapter


func bind_visual(next_visual: HeroPresentationAdapter) -> void:
	_visual_adapter = next_visual


func get_body_point() -> Vector3:
	return _imported_or_fallback(&"socket_camera_body", "Body", global_position)


func get_chest_point() -> Vector3:
	return _imported_or_fallback(&"socket_camera_chest", "Chest", global_position + Vector3.UP * 1.35)


func get_head_point() -> Vector3:
	return _imported_or_fallback(&"socket_camera_head", "Head", global_position + Vector3.UP * 2.05)


func get_aim_point() -> Vector3:
	return _imported_or_fallback(&"socket_aim", "AimPoint", global_position + Vector3.UP * 1.42)


func _imported_or_fallback(helper_name: StringName, fallback_name: String, fallback: Vector3) -> Vector3:
	if _visual_adapter != null and _visual_adapter.is_import_ready():
		var helper := _visual_adapter.get_helper(helper_name)
		if helper != null:
			return helper.global_position
	return _point_position(fallback_name, fallback)


func _point_position(point_name: String, fallback: Vector3) -> Vector3:
	var point := get_node_or_null(point_name) as Node3D
	return point.global_position if point != null else fallback
