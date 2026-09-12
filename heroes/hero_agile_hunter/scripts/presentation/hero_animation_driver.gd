class_name HeroAnimationDriver
extends Node
## Gameplay-intent facade for the imported Lyra presentation.
##
## Combat, movement, cooldown, collision, damage, and projectile simulation call this
## class exactly as before. The implementation delegates only named visual playback to
## HeroPresentationAdapter; no procedural bones or placeholder AnimationPlayer clips are
## retained on the active hero path.

signal action_changed(previous: StringName, current: StringName)
signal animation_state_changed(state_id: StringName)
signal semantic_event(event_id: StringName, clip_name: StringName, event_time_s: float, socket_position: Vector3)

const CANONICAL_CLIPS := [
	&"idle",
	&"idle_variation",
	&"walk",
	&"run",
	&"turn_left",
	&"turn_right",
	&"start_run",
	&"stop_run",
	&"basic_attack",
	&"basic_attack_recovery",
	&"attack_variant",
	&"charged_attack",
	&"hit_light",
	&"hit_heavy",
	&"knockback",
	&"stun",
	&"death",
	&"victory",
	&"spawn",
	&"skill_01",
	&"skill_02",
	&"skill_03",
	&"ultimate",
]

var visual: HeroPresentationAdapter
var movement: MovementController
var current_action: StringName = &""
var _action_total := 0.0
var _action_elapsed := 0.0
var _dead := false
var _last_locomotion: StringName = &""
var _connected_visual: HeroPresentationAdapter


func initialize(owner_visual: HeroPresentationAdapter, owner_movement: MovementController) -> void:
	visual = owner_visual
	movement = owner_movement
	if visual == null or not visual.is_import_ready():
		push_error("HeroAnimationDriver requires an initialized imported HeroPresentationAdapter.")
		return
	if _connected_visual != visual:
		if _connected_visual != null and _connected_visual.semantic_event.is_connected(_on_visual_semantic_event):
			_connected_visual.semantic_event.disconnect(_on_visual_semantic_event)
		visual.semantic_event.connect(_on_visual_semantic_event)
		_connected_visual = visual
	_last_locomotion = &""


func request_action(action_id: StringName, requested_duration: float) -> void:
	if _dead and action_id != &"death":
		return
	if visual == null or not visual.has_clip(action_id):
		push_warning("Lyra presentation received unsupported action %s." % action_id)
		return
	var previous := current_action
	current_action = action_id
	# Intent duration may be gameplay-shorter than the authored motion. Keep the visual
	# readable through the imported clip's end, while gameplay's own timers stay decisive.
	_action_total = maxf(maxf(0.01, requested_duration), visual.get_clip_duration(action_id))
	_action_elapsed = 0.0
	visual.play_clip(action_id, true)
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


func play_turn(left: bool) -> void:
	if not _dead:
		request_action(&"turn_left" if left else &"turn_right", 0.42)


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


func get_clip_duration(action_id: StringName) -> float:
	return visual.get_clip_duration(action_id) if visual != null else 0.0


func get_semantic_event_time(action_id: StringName, event_id: StringName, fallback: float = -1.0) -> float:
	return visual.get_semantic_event_time(action_id, event_id, fallback) if visual != null else fallback


func _process(delta: float) -> void:
	if visual == null or not visual.is_import_ready():
		return
	if not _dead and not current_action.is_empty():
		_action_elapsed += delta
		if _action_elapsed >= _action_total:
			var previous := current_action
			current_action = &""
			_action_total = 0.0
			_action_elapsed = 0.0
			action_changed.emit(previous, current_action)
	if current_action.is_empty():
		_present_locomotion()
	animation_state_changed.emit(current_state())


func _present_locomotion() -> void:
	var next_locomotion: StringName = &"idle"
	if movement != null:
		next_locomotion = movement.locomotion_state
	if next_locomotion == _last_locomotion:
		return
	_last_locomotion = next_locomotion
	visual.play_locomotion(next_locomotion)


func _on_visual_semantic_event(event_id: StringName, clip_name: StringName, event_time_s: float, socket_position: Vector3) -> void:
	# Forward only presentation facts. No gameplay object listens here to authorize hits,
	# damage, cooldowns, or projectile simulation.
	semantic_event.emit(event_id, clip_name, event_time_s, socket_position)
