class_name DemoFollowCamera
extends Camera3D
## Demo-only camera. It follows CameraTarget but never controls combat or targeting.

@export var follow_distance: float = 10.8
@export var follow_height: float = 6.8
@export var follow_smoothing: float = 7.0

var target: HeroCameraTarget


func set_target(next_target: HeroCameraTarget) -> void:
	target = next_target
	if target != null:
		global_position = _desired_position()
		look_at(target.get_chest_point(), Vector3.UP)


func _process(delta: float) -> void:
	if target == null or not is_instance_valid(target):
		return
	global_position = global_position.lerp(_desired_position(), minf(1.0, follow_smoothing * delta))
	look_at(target.get_chest_point(), Vector3.UP)


func _desired_position() -> Vector3:
	var focus := target.get_chest_point()
	var hero_forward := -target.global_transform.basis.z
	hero_forward.y = 0.0
	if hero_forward.length_squared() < 0.001:
		hero_forward = Vector3.FORWARD
	return focus - hero_forward.normalized() * follow_distance + Vector3.UP * follow_height
