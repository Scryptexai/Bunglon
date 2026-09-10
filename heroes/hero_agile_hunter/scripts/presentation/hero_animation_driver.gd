class_name HeroAnimationDriver
extends Node
## Animation-state adapter for the native rig.
##
## It exposes production clip names through AnimationPlayer, while procedural bone poses
## keep this repository self-contained. Replacing the native modules with imported clips
## only requires feeding the same state/action names into this component.

signal action_changed(previous: StringName, current: StringName)
signal animation_state_changed(state_id: StringName)

const CANONICAL_CLIPS := [
	"idle",
	"idle_variation",
	"walk",
	"run",
	"turn_left",
	"turn_right",
	"start_run",
	"stop_run",
	"basic_attack",
	"basic_attack_recovery",
	"attack_variant",
	"charged_attack",
	"hit_light",
	"hit_heavy",
	"knockback",
	"stun",
	"death",
	"victory",
	"spawn",
	"skill_01",
	"skill_02",
	"skill_03",
	"ultimate",
]

var visual: HeroVisual
var skeleton: Skeleton3D
var movement: MovementController
var animation_player: AnimationPlayer
var animation_tree: AnimationTree
var current_action: StringName = &""
var _action_total: float = 0.0
var _action_elapsed: float = 0.0
var _time: float = 0.0
var _dead: bool = false
var _previous_yaw: float = 0.0


func initialize(owner_visual: HeroVisual, owner_movement: MovementController) -> void:
	visual = owner_visual
	movement = owner_movement
	skeleton = visual.get_skeleton() if visual != null else null
	animation_player = get_node_or_null("AnimationPlayer") as AnimationPlayer
	animation_tree = get_node_or_null("AnimationTree") as AnimationTree
	_install_named_clips()
	if visual != null:
		visual.update_weapon_pose()


func request_action(action_id: StringName, duration: float) -> void:
	if _dead and action_id != &"death":
		return
	var previous := current_action
	current_action = action_id
	_action_total = maxf(0.01, duration)
	_action_elapsed = 0.0
	_play_named_clip(action_id)
	action_changed.emit(previous, current_action)


func play_hit(heavy: bool) -> void:
	if _dead:
		return
	request_action(&"hit_heavy" if heavy else &"hit_light", 0.22 if heavy else 0.14)


func play_death() -> void:
	_dead = true
	request_action(&"death", 9999.0)


func play_spawn() -> void:
	_dead = false
	request_action(&"spawn", 0.65)


func play_victory() -> void:
	if not _dead:
		request_action(&"victory", 1.3)


func current_state() -> StringName:
	if _dead:
		return &"death"
	if not current_action.is_empty():
		if movement != null and movement.horizontal_speed > 0.2:
			return &"attack_movement"
		return current_action
	if movement == null:
		return &"idle"
	return movement.locomotion_state


func _process(delta: float) -> void:
	if skeleton == null:
		return
	_time += delta
	if not _dead and not current_action.is_empty():
		_action_elapsed += delta
		if _action_elapsed >= _action_total:
			var previous := current_action
			current_action = &""
			_action_total = 0.0
			_action_elapsed = 0.0
			action_changed.emit(previous, current_action)
	_apply_pose()
	if visual != null:
		visual.update_weapon_pose()
	animation_state_changed.emit(current_state())


func _install_named_clips() -> void:
	if animation_player == null or animation_player.has_animation(&"hero/idle"):
		return
	var library := AnimationLibrary.new()
	for clip_name: String in CANONICAL_CLIPS:
		var clip := Animation.new()
		clip.length = 1.0
		clip.loop_mode = Animation.LOOP_LINEAR if clip_name in ["idle", "walk", "run"] else Animation.LOOP_NONE
		library.add_animation(StringName(clip_name), clip)
	animation_player.add_animation_library(&"hero", library)


func _play_named_clip(action_id: StringName) -> void:
	if animation_player == null:
		return
	var clip_path := StringName("hero/%s" % action_id)
	if animation_player.has_animation(clip_path):
		animation_player.play(clip_path)


func _apply_pose() -> void:
	skeleton.reset_bone_poses()
	if _dead:
		_apply_death_pose()
		return
	_apply_locomotion_pose()
	_apply_action_pose()


func _apply_locomotion_pose() -> void:
	if movement == null:
		_apply_idle_pose()
		return
	match movement.locomotion_state:
		&"run":
			_apply_run_pose(1.0)
		&"walk":
			_apply_run_pose(0.52)
		&"dash":
			_apply_dash_pose()
		_:
			_apply_idle_pose()


func _apply_idle_pose() -> void:
	var breath := sin(_time * 1.65)
	_set_bone_rotation(&"spine", Vector3.RIGHT, breath * 0.025)
	_set_bone_rotation(&"chest", Vector3.FORWARD, sin(_time * 0.84) * 0.035)
	_set_bone_rotation(&"head", Vector3.UP, sin(_time * 0.55) * 0.055)
	_set_bone_rotation(&"upper_arm_l", Vector3.FORWARD, -0.10)
	_set_bone_rotation(&"upper_arm_r", Vector3.FORWARD, 0.10)


func _apply_run_pose(intensity: float) -> void:
	var stride := sin(_time * (10.0 if intensity > 0.7 else 6.0))
	_set_bone_rotation(&"upper_leg_l", Vector3.RIGHT, stride * 0.62 * intensity)
	_set_bone_rotation(&"upper_leg_r", Vector3.RIGHT, -stride * 0.62 * intensity)
	_set_bone_rotation(&"lower_leg_l", Vector3.RIGHT, maxf(0.0, -stride) * 0.48 * intensity)
	_set_bone_rotation(&"lower_leg_r", Vector3.RIGHT, maxf(0.0, stride) * 0.48 * intensity)
	_set_bone_rotation(&"upper_arm_l", Vector3.RIGHT, -stride * 0.38 * intensity)
	_set_bone_rotation(&"upper_arm_r", Vector3.RIGHT, stride * 0.22 * intensity)
	_set_bone_rotation(&"chest", Vector3.UP, stride * 0.09 * intensity)


func _apply_dash_pose() -> void:
	_set_bone_rotation(&"spine", Vector3.RIGHT, deg_to_rad(-22.0))
	_set_bone_rotation(&"chest", Vector3.RIGHT, deg_to_rad(-18.0))
	_set_bone_rotation(&"upper_leg_l", Vector3.RIGHT, deg_to_rad(28.0))
	_set_bone_rotation(&"upper_leg_r", Vector3.RIGHT, deg_to_rad(-20.0))
	_set_bone_rotation(&"upper_arm_l", Vector3.RIGHT, deg_to_rad(-35.0))
	_set_bone_rotation(&"upper_arm_r", Vector3.RIGHT, deg_to_rad(-35.0))


func _apply_action_pose() -> void:
	if current_action.is_empty():
		_apply_turn_pose()
		return
	var progress := clampf(_action_elapsed / maxf(0.01, _action_total), 0.0, 1.0)
	match current_action:
		&"basic_attack", &"attack_variant", &"charged_attack", &"skill_01", &"skill_03":
			_apply_bow_pose(progress, current_action)
		&"skill_02":
			_apply_dash_pose()
		&"ultimate":
			_apply_ultimate_pose(progress)
		&"hit_light":
			_set_bone_rotation(&"chest", Vector3.RIGHT, sin(progress * PI) * 0.22)
		&"hit_heavy":
			_set_bone_rotation(&"spine", Vector3.RIGHT, sin(progress * PI) * 0.40)
			_set_bone_rotation(&"head", Vector3.RIGHT, sin(progress * PI) * 0.18)
		&"victory":
			_set_bone_rotation(&"upper_arm_r", Vector3.FORWARD, deg_to_rad(62.0))
			_set_bone_rotation(&"forearm_r", Vector3.RIGHT, deg_to_rad(-42.0))
		&"spawn":
			_set_bone_rotation(&"spine", Vector3.RIGHT, deg_to_rad(-10.0) * (1.0 - progress))


func _apply_bow_pose(progress: float, action_id: StringName) -> void:
	var draw := sin(clampf(progress * 1.65, 0.0, 1.0) * PI * 0.5)
	if progress > 0.62:
		draw *= 1.0 - clampf((progress - 0.62) / 0.25, 0.0, 1.0)
	var precision := 1.15 if action_id == &"skill_03" else 1.0
	if action_id == &"charged_attack":
		precision = 1.3
		draw = minf(1.0, draw * 1.18)
	_set_bone_rotation(&"chest", Vector3.UP, deg_to_rad(-16.0) * precision)
	_set_bone_rotation(&"upper_arm_l", Vector3.FORWARD, deg_to_rad(-46.0))
	_set_bone_rotation(&"forearm_l", Vector3.RIGHT, deg_to_rad(-34.0))
	_set_bone_rotation(&"upper_arm_r", Vector3.FORWARD, deg_to_rad(34.0) * draw)
	_set_bone_rotation(&"forearm_r", Vector3.RIGHT, deg_to_rad(52.0) * draw)
	_set_bone_rotation(&"head", Vector3.UP, deg_to_rad(-7.0))


func _apply_ultimate_pose(progress: float) -> void:
	var arc := sin(progress * PI)
	_set_bone_rotation(&"spine", Vector3.RIGHT, deg_to_rad(-12.0) * arc)
	_set_bone_rotation(&"chest", Vector3.UP, deg_to_rad(-24.0))
	_set_bone_rotation(&"upper_arm_l", Vector3.FORWARD, deg_to_rad(-72.0) * arc)
	_set_bone_rotation(&"upper_arm_r", Vector3.FORWARD, deg_to_rad(62.0) * arc)
	_set_bone_rotation(&"forearm_r", Vector3.RIGHT, deg_to_rad(45.0) * arc)


func _apply_turn_pose() -> void:
	if movement == null or movement.character == null:
		return
	var yaw_delta := wrapf(movement.character.rotation.y - _previous_yaw, -PI, PI)
	_previous_yaw = movement.character.rotation.y
	if absf(yaw_delta) > 0.001:
		_set_bone_rotation(&"chest", Vector3.UP, clampf(-yaw_delta * 3.5, -0.20, 0.20))


func _apply_death_pose() -> void:
	_set_bone_rotation(&"root", Vector3.FORWARD, deg_to_rad(82.0))
	_set_bone_rotation(&"spine", Vector3.RIGHT, deg_to_rad(-24.0))
	_set_bone_rotation(&"upper_leg_l", Vector3.RIGHT, deg_to_rad(34.0))
	_set_bone_rotation(&"upper_leg_r", Vector3.RIGHT, deg_to_rad(-28.0))
	_set_bone_rotation(&"upper_arm_l", Vector3.RIGHT, deg_to_rad(46.0))
	_set_bone_rotation(&"upper_arm_r", Vector3.RIGHT, deg_to_rad(-38.0))


func _set_bone_rotation(bone_name: StringName, axis: Vector3, angle: float) -> void:
	var index := skeleton.find_bone(bone_name)
	if index >= 0:
		skeleton.set_bone_pose_rotation(index, Quaternion(axis.normalized(), angle))
