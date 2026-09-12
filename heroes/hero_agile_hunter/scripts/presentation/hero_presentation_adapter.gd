class_name HeroPresentationAdapter
extends Node3D
## Imported-animation presentation boundary for Lyra Vesper.
##
## Gameplay asks HeroAnimationDriver for a named action. This adapter owns the imported
## Phase 5 GLB hierarchy, its AnimationPlayer/AnimationTree, visual-only semantic events,
## attachment helpers, and safe LOD replacement. It never moves CharacterBody3D, creates
## damage, or spawns an authoritative projectile.

signal import_contract_validated(lod_level: int, valid: bool, issues: PackedStringArray)
signal import_ready
signal lod_swapped(previous_lod: int, current_lod: int, clip_name: StringName, clip_time_s: float)
signal clip_started(clip_name: StringName, restart: bool)
signal semantic_event(event_id: StringName, clip_name: StringName, event_time_s: float, socket_position: Vector3)

const MANIFEST_PATH := "res://character_animated/animation_manifest.json"
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
const REQUIRED_HELPERS := [
	&"socket_weapon",
	&"socket_projectile",
	&"socket_camera_body",
	&"socket_camera_chest",
	&"socket_camera_head",
	&"socket_aim",
]
const REQUIRED_MATERIALS := [
	&"M_Lyra_OpaqueAtlas",
	&"M_Lyra_LumenEnergy",
	&"M_Lyra_AuroraMantle",
]
const EVENT_EPSILON := 0.0005

@export_file("*.glb") var lod0_asset_path := "res://character_animated/lyra_vesper_animated.glb"
@export_file("*.glb") var lod1_asset_path := "res://character_animated/lyra_vesper_animated_lod1.glb"
@export_enum("automatic", "lod0", "lod1") var lod_policy := "automatic"
@export var lod_switch_distance: float = 24.0
@export var lod_reference_path: NodePath
@export_range(0.0, 0.5, 0.01) var transition_seconds: float = 0.10
# Phase 4/5 source meshes use X horizontal, Y depth, Z up; Lyra's front is -Y.
# Godot uses Y up and its character-facing convention is -Z, so convert once at
# the presentation boundary: (x, y, z) → (-x, z, y). This is a proper basis
# conversion (not a scale mirror) and keeps the bow pointing at gameplay forward.
@export var apply_phase45_axis_conversion := true

var _initialized := false
var _lod1_contract_safe := false
var _active_lod := -1
var _active_visual: Node3D
var _skeleton: Skeleton3D
var _animation_player: AnimationPlayer
var _animation_tree: AnimationTree
var _state_machine_playback: AnimationNodeStateMachinePlayback
var _clip_contracts: Dictionary = {}
var _lod_contracts: Dictionary = {}
var _clip_to_imported: Dictionary = {}
var _helpers: Dictionary = {}
var _active_clip: StringName = &""
var _active_imported_clip: StringName = &""
var _semantic_clock_s := 0.0
var _semantic_cycle := 0
var _fired_event_keys: Dictionary = {}


func initialize() -> void:
	if _initialized:
		return
	_load_manifest_contract()
	if _clip_contracts.is_empty():
		push_error("Lyra presentation cannot initialize without animation_manifest.json.")
		return

	var lod0_candidate := _build_lod_candidate(0)
	_store_candidate_contract(0, lod0_candidate)
	if not bool(lod0_candidate.get("valid", false)):
		_report_candidate_failure(0, lod0_candidate)
		_free_candidate(lod0_candidate)
		return
	_install_candidate(lod0_candidate, false)

	var lod1_candidate := _build_lod_candidate(1)
	_store_candidate_contract(1, lod1_candidate)
	_lod1_contract_safe = bool(lod1_candidate.get("valid", false)) and _lod_contracts_match(0, 1)
	if not _lod1_contract_safe:
		_report_candidate_failure(1, lod1_candidate)
		push_warning("Lyra LOD1 is disabled because its imported skeleton, clips, timing, helpers, or materials do not match LOD0.")
	_free_candidate(lod1_candidate)

	_initialized = true
	import_ready.emit()
	play_clip(&"idle", true)


func is_import_ready() -> bool:
	return _initialized and _active_visual != null and _animation_player != null and _skeleton != null


func get_active_lod() -> int:
	return _active_lod


func is_lod1_contract_safe() -> bool:
	return _lod1_contract_safe


func get_skeleton() -> Skeleton3D:
	return _skeleton


func get_animation_player() -> AnimationPlayer:
	return _animation_player


func get_animation_tree() -> AnimationTree:
	return _animation_tree


func get_active_clip() -> StringName:
	return _active_clip


func get_active_clip_time() -> float:
	return _semantic_clock_s


func get_clip_duration(clip_name: StringName) -> float:
	var contract: Dictionary = _clip_contracts.get(clip_name, {})
	return float(contract.get("duration_s", 0.0))


func get_semantic_event_time(clip_name: StringName, event_id: StringName, fallback: float = -1.0) -> float:
	var contract: Dictionary = _clip_contracts.get(clip_name, {})
	var events: Array = contract.get("events", [])
	for event_data: Dictionary in events:
		if StringName(event_data.get("name", "")) == event_id:
			return float(event_data.get("time_s", fallback))
	return fallback


func get_helper(helper_name: StringName) -> Node3D:
	return _helpers.get(helper_name) as Node3D


func get_projectile_origin() -> Node3D:
	return get_helper(&"socket_projectile")


func get_weapon_socket() -> Node3D:
	return get_helper(&"socket_weapon")


func get_camera_body_socket() -> Node3D:
	return get_helper(&"socket_camera_body")


func get_camera_chest_socket() -> Node3D:
	return get_helper(&"socket_camera_chest")


func get_camera_head_socket() -> Node3D:
	return get_helper(&"socket_camera_head")


func get_aim_socket() -> Node3D:
	return get_helper(&"socket_aim")


func get_material_names() -> PackedStringArray:
	var contract: Dictionary = _lod_contracts.get(_active_lod, {})
	var names: Array = contract.get("material_names", [])
	var result := PackedStringArray()
	for material_name: String in names:
		result.append(material_name)
	return result


func get_import_contract(lod_level: int) -> Dictionary:
	var contract: Dictionary = _lod_contracts.get(lod_level, {})
	return contract.duplicate(true)


func has_clip(clip_name: StringName) -> bool:
	return _clip_to_imported.has(clip_name)


func play_locomotion(locomotion_state: StringName) -> bool:
	match locomotion_state:
		&"walk", &"run", &"idle":
			return play_clip(locomotion_state)
		&"dash":
			# Phase Step normally requests skill_02 itself. This fallback keeps a visual
			# loop alive if gameplay's dash state outlasts the one-shot presentation.
			return play_clip(&"run")
		_:
			return play_clip(&"idle")


func play_clip(clip_name: StringName, restart: bool = false, resume_time_s: float = -1.0, preserve_event_ledger: bool = false) -> bool:
	if not is_import_ready() or not has_clip(clip_name):
		return false
	if clip_name == _active_clip and not restart and resume_time_s < 0.0:
		return true

	var duration := get_clip_duration(clip_name)
	if duration <= 0.0:
		push_warning("Lyra requested a clip without a manifest duration: %s" % clip_name)
		return false
	var resume := clampf(resume_time_s, 0.0, duration) if resume_time_s >= 0.0 else 0.0
	if _is_looping(clip_name) and duration > 0.0:
		resume = fposmod(resume, duration)

	var previous_clip := _active_clip
	_active_clip = clip_name
	_active_imported_clip = StringName(_clip_to_imported.get(clip_name, ""))
	if not preserve_event_ledger:
		_semantic_cycle = 0
		_fired_event_keys.clear()
	_semantic_clock_s = resume

	_start_imported_playback(clip_name, restart or previous_clip.is_empty(), resume)
	clip_started.emit(clip_name, restart)
	return true


func set_lod_level(requested_lod: int) -> bool:
	if requested_lod == _active_lod:
		return true
	if requested_lod < 0 or requested_lod > 1:
		push_warning("Lyra received an unsupported LOD level: %d" % requested_lod)
		return false
	if requested_lod == 1 and not _lod1_contract_safe:
		return false

	var candidate := _build_lod_candidate(requested_lod)
	_store_candidate_contract(requested_lod, candidate)
	if not bool(candidate.get("valid", false)) or not _lod_contracts_match(0, requested_lod):
		_report_candidate_failure(requested_lod, candidate)
		_free_candidate(candidate)
		return false

	var previous_lod := _active_lod
	var preserved_clip := _active_clip
	var preserved_time := _semantic_clock_s
	var preserved_cycle := _semantic_cycle
	var preserved_events := _fired_event_keys.duplicate()
	_install_candidate(candidate, true)
	_semantic_cycle = preserved_cycle
	_fired_event_keys = preserved_events
	if not preserved_clip.is_empty():
		play_clip(preserved_clip, true, preserved_time, true)
	lod_swapped.emit(previous_lod, _active_lod, preserved_clip, preserved_time)
	return true


func _process(delta: float) -> void:
	if not is_import_ready():
		return
	_ensure_state_machine_playback()
	_update_automatic_lod()
	_advance_semantic_clock(delta)


func _load_manifest_contract() -> void:
	var raw_manifest := FileAccess.get_file_as_string(MANIFEST_PATH)
	var parsed: Variant = JSON.parse_string(raw_manifest)
	if not (parsed is Dictionary):
		push_error("Unable to parse Lyra animation manifest at %s." % MANIFEST_PATH)
		return
	var manifest: Dictionary = parsed
	var animation_contract: Dictionary = manifest.get("animation_contract", {})
	var clips: Array = animation_contract.get("clips", [])
	for raw_clip: Variant in clips:
		if not (raw_clip is Dictionary):
			continue
		var clip: Dictionary = raw_clip
		var clip_name := StringName(clip.get("name", ""))
		if clip_name.is_empty():
			continue
		var events: Array = []
		for raw_event: Variant in clip.get("semantic_events", []):
			if raw_event is Dictionary:
				var event_data: Dictionary = raw_event
				events.append(event_data.duplicate(true))
		var rotation_tracks: Array = clip.get("direct_rotation_tracks", [])
		_clip_contracts[clip_name] = {
			"duration_s": float(clip.get("duration_s", 0.0)),
			"loop": bool(clip.get("loop", false)),
			"rotation_tracks": rotation_tracks.duplicate(),
			"events": events,
		}
	for required_clip: StringName in CANONICAL_CLIPS:
		if not _clip_contracts.has(required_clip):
			push_error("Lyra animation manifest is missing canonical clip %s." % required_clip)
			_clip_contracts.clear()
			return


func _build_lod_candidate(lod_level: int) -> Dictionary:
	var issues := PackedStringArray()
	var asset_path := lod0_asset_path if lod_level == 0 else lod1_asset_path
	var packed := load(asset_path) as PackedScene
	if packed == null:
		issues.append("Could not load %s as an imported PackedScene." % asset_path)
		return _invalid_candidate(lod_level, issues)
	var instance := packed.instantiate() as Node3D
	if instance == null:
		issues.append("Could not instantiate imported visual %s." % asset_path)
		return _invalid_candidate(lod_level, issues)

	var players := _nodes_of_type(instance, "AnimationPlayer")
	var skeletons := _nodes_of_type(instance, "Skeleton3D")
	if players.size() != 1:
		issues.append("Expected exactly one imported AnimationPlayer, found %d." % players.size())
	if skeletons.size() != 1:
		issues.append("Expected exactly one imported Skeleton3D, found %d." % skeletons.size())
	if not issues.is_empty():
		return _candidate(lod_level, instance, null, null, {}, [], 0, issues)

	var player := players[0] as AnimationPlayer
	var skeleton := skeletons[0] as Skeleton3D
	var clip_map: Dictionary = {}
	var clip_lengths: Dictionary = {}
	for canonical_name: StringName in CANONICAL_CLIPS:
		var imported_name := _find_imported_clip(player, canonical_name)
		if imported_name.is_empty():
			issues.append("Missing imported clip %s." % canonical_name)
			continue
		var animation := player.get_animation(imported_name)
		if animation == null or animation.get_track_count() == 0:
			issues.append("Imported clip %s has no animation tracks." % canonical_name)
			continue
		var expected_duration := get_clip_duration(canonical_name)
		if not is_equal_approx(animation.length, expected_duration):
			issues.append("Imported clip %s duration %.4f does not match manifest %.4f." % [canonical_name, animation.length, expected_duration])
		var clip_contract: Dictionary = _clip_contracts.get(canonical_name, {})
		var expected_tracks: Array = clip_contract.get("rotation_tracks", [])
		if not _animation_matches_rotation_contract(animation, skeleton, expected_tracks):
			issues.append("Imported clip %s does not preserve its manifest skeleton rotation tracks." % canonical_name)
		clip_map[canonical_name] = imported_name
		clip_lengths[canonical_name] = animation.length

	var bone_names: Array = []
	if skeleton.get_bone_count() != 54:
		issues.append("Expected 54 imported skeleton bones, found %d." % skeleton.get_bone_count())
	for bone_index: int in skeleton.get_bone_count():
		bone_names.append(String(skeleton.get_bone_name(bone_index)))
	for helper_name: StringName in REQUIRED_HELPERS:
		if skeleton.find_bone(helper_name) < 0 and instance.find_child(String(helper_name), true, false) == null:
			issues.append("Missing imported helper %s." % helper_name)

	var material_names := _material_names(instance)
	for material_name: StringName in REQUIRED_MATERIALS:
		if not material_names.has(String(material_name)):
			issues.append("Missing imported material group %s." % material_name)
	var texture_count := _material_texture_count(instance)
	if texture_count < 8:
		issues.append("Expected at least eight imported material textures, found %d." % texture_count)

	return _candidate(lod_level, instance, player, skeleton, clip_map, bone_names, texture_count, issues, material_names, clip_lengths)


func _candidate(
	lod_level: int,
	instance: Node3D,
	player: AnimationPlayer,
	skeleton: Skeleton3D,
	clip_map: Dictionary,
	bone_names: Array,
	texture_count: int,
	issues: PackedStringArray,
	material_names: Array = [],
	clip_lengths: Dictionary = {}
) -> Dictionary:
	return {
		"lod_level": lod_level,
		"instance": instance,
		"player": player,
		"skeleton": skeleton,
		"clip_map": clip_map,
		"bone_names": bone_names,
		"clip_lengths": clip_lengths,
		"material_names": material_names,
		"texture_count": texture_count,
		"issues": issues,
		"valid": issues.is_empty(),
	}


func _invalid_candidate(lod_level: int, issues: PackedStringArray) -> Dictionary:
	return _candidate(lod_level, null, null, null, {}, [], 0, issues)


func _store_candidate_contract(lod_level: int, candidate: Dictionary) -> void:
	var issues: PackedStringArray = candidate.get("issues", PackedStringArray())
	_lod_contracts[lod_level] = {
		"valid": bool(candidate.get("valid", false)),
		"bone_names": candidate.get("bone_names", []).duplicate(),
		"clip_lengths": candidate.get("clip_lengths", {}).duplicate(),
		"material_names": candidate.get("material_names", []).duplicate(),
		"texture_count": int(candidate.get("texture_count", 0)),
		"helpers": REQUIRED_HELPERS.duplicate(),
		"issues": issues.duplicate(),
	}
	import_contract_validated.emit(lod_level, bool(candidate.get("valid", false)), issues)


func _install_candidate(candidate: Dictionary, preserve_existing_state: bool) -> void:
	var old_visual := _active_visual
	var old_player := _animation_player
	var old_tree := _animation_tree
	if old_player != null:
		old_player.stop(true)
	if old_tree != null and is_instance_valid(old_tree):
		old_tree.queue_free()

	_active_visual = candidate.get("instance") as Node3D
	_animation_player = candidate.get("player") as AnimationPlayer
	_skeleton = candidate.get("skeleton") as Skeleton3D
	var candidate_clip_map: Dictionary = candidate.get("clip_map", {})
	_clip_to_imported = candidate_clip_map.duplicate()
	_active_lod = int(candidate.get("lod_level", 0))
	_helpers.clear()
	_active_visual.name = "LyraAnimatedLOD%d" % _active_lod
	if apply_phase45_axis_conversion:
		var axis_conversion := Basis(Vector3.LEFT, Vector3.BACK, Vector3.UP)
		# Preserve any future authored root transform instead of replacing it outright.
		_active_visual.basis = axis_conversion * _active_visual.basis
	add_child(_active_visual)
	_apply_manifest_loop_modes()
	_resolve_runtime_helpers()
	_build_animation_tree()

	if old_visual != null and is_instance_valid(old_visual):
		old_visual.queue_free()
	if not preserve_existing_state:
		_active_clip = &""
		_active_imported_clip = &""
		_semantic_clock_s = 0.0
		_semantic_cycle = 0
		_fired_event_keys.clear()


func _apply_manifest_loop_modes() -> void:
	if _animation_player == null:
		return
	for clip_name: StringName in CANONICAL_CLIPS:
		var imported_name := StringName(_clip_to_imported.get(clip_name, ""))
		var animation := _animation_player.get_animation(imported_name)
		if animation != null:
			# Godot 4.3 imports named glTF clips but does not turn arbitrary glTF
			# animation extras into loop metadata. The checked-in manifest is the
			# deliberate conversion layer and remains the semantic-event authority.
			animation.loop_mode = Animation.LOOP_LINEAR if _is_looping(clip_name) else Animation.LOOP_NONE


func _resolve_runtime_helpers() -> void:
	for helper_name: StringName in REQUIRED_HELPERS:
		var existing := _active_visual.find_child(String(helper_name), true, false) as Node3D
		if existing != null:
			_helpers[helper_name] = existing
			continue
		var bone_index := _skeleton.find_bone(helper_name)
		if bone_index < 0:
			push_error("Lyra active visual lost helper %s after validation." % helper_name)
			continue
		var attachment := BoneAttachment3D.new()
		attachment.name = "Resolved%s" % _pascal_case(String(helper_name))
		attachment.bone_name = String(helper_name)
		_skeleton.add_child(attachment)
		_helpers[helper_name] = attachment


func _build_animation_tree() -> void:
	_animation_tree = AnimationTree.new()
	_animation_tree.name = "AnimationTree"
	var state_machine := AnimationNodeStateMachine.new()
	state_machine.allow_transition_to_self = true
	for clip_index: int in CANONICAL_CLIPS.size():
		var clip_name: StringName = CANONICAL_CLIPS[clip_index]
		var animation_node := AnimationNodeAnimation.new()
		animation_node.animation = StringName(_clip_to_imported.get(clip_name, ""))
		state_machine.add_node(clip_name, animation_node, Vector2(float(clip_index % 6) * 240.0, float(clip_index / 6) * 110.0))
	for from_clip: StringName in CANONICAL_CLIPS:
		for to_clip: StringName in CANONICAL_CLIPS:
			if from_clip == to_clip:
				continue
			var transition := AnimationNodeStateMachineTransition.new()
			transition.advance_mode = AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED
			transition.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_IMMEDIATE
			transition.reset = true
			transition.xfade_time = transition_seconds
			state_machine.add_transition(from_clip, to_clip, transition)
	_animation_tree.tree_root = state_machine
	add_child(_animation_tree)
	_animation_tree.anim_player = _animation_tree.get_path_to(_animation_player)
	_animation_tree.active = true
	_state_machine_playback = _animation_tree.get("parameters/playback") as AnimationNodeStateMachinePlayback


func _ensure_state_machine_playback() -> void:
	if _animation_tree == null or not _animation_tree.active or _state_machine_playback != null:
		return
	_state_machine_playback = _animation_tree.get("parameters/playback") as AnimationNodeStateMachinePlayback
	if _state_machine_playback != null and not _active_clip.is_empty():
		_state_machine_playback.start(_active_clip)
		if _semantic_clock_s > 0.0:
			_animation_tree.advance(_semantic_clock_s)


func _start_imported_playback(clip_name: StringName, restart: bool, resume_time_s: float) -> void:
	if _state_machine_playback != null:
		if _state_machine_playback.get_current_node().is_empty() or restart:
			_state_machine_playback.start(clip_name)
		else:
			_state_machine_playback.travel(clip_name, false)
		if resume_time_s > 0.0:
			_animation_tree.advance(resume_time_s)
		return
	if _animation_player == null:
		return
	_animation_player.play(_active_imported_clip, transition_seconds)
	if resume_time_s > 0.0:
		_animation_player.seek(resume_time_s, true, true)


func _advance_semantic_clock(delta: float) -> void:
	if _active_clip.is_empty():
		return
	var duration := get_clip_duration(_active_clip)
	if duration <= 0.0:
		return
	var from_time := _semantic_clock_s
	var target_time := from_time + maxf(0.0, delta)
	if _is_looping(_active_clip):
		while target_time >= duration:
			_emit_events_between(from_time, duration)
			target_time -= duration
			from_time = 0.0
			_semantic_cycle += 1
		_emit_events_between(from_time, target_time)
		_semantic_clock_s = target_time
		return
	_semantic_clock_s = minf(target_time, duration)
	_emit_events_between(from_time, _semantic_clock_s)


func _emit_events_between(from_time_s: float, to_time_s: float) -> void:
	var contract: Dictionary = _clip_contracts.get(_active_clip, {})
	var events: Array = contract.get("events", [])
	for event_index: int in events.size():
		var event_data: Dictionary = events[event_index]
		var event_time := float(event_data.get("time_s", -1.0))
		if event_time < from_time_s - EVENT_EPSILON or event_time > to_time_s + EVENT_EPSILON:
			continue
		var event_key := "%d:%d" % [_semantic_cycle, event_index]
		if _fired_event_keys.has(event_key):
			continue
		_fired_event_keys[event_key] = true
		var event_id := StringName(event_data.get("name", ""))
		if event_id.is_empty():
			continue
		var origin := get_projectile_origin()
		var socket_position := origin.global_position if origin != null else global_position
		semantic_event.emit(event_id, _active_clip, event_time, socket_position)


func _update_automatic_lod() -> void:
	if not _lod1_contract_safe:
		return
	var desired_lod := _active_lod
	match lod_policy:
		"lod0":
			desired_lod = 0
		"lod1":
			desired_lod = 1
		_:
			var reference := get_node_or_null(lod_reference_path) as Node3D
			if reference == null:
				reference = get_viewport().get_camera_3d()
			if reference != null:
				desired_lod = 1 if global_position.distance_to(reference.global_position) >= lod_switch_distance else 0
	if desired_lod != _active_lod:
		set_lod_level(desired_lod)


func _lod_contracts_match(first_lod: int, second_lod: int) -> bool:
	var first: Dictionary = _lod_contracts.get(first_lod, {})
	var second: Dictionary = _lod_contracts.get(second_lod, {})
	if not bool(first.get("valid", false)) or not bool(second.get("valid", false)):
		return false
	if first.get("bone_names", []) != second.get("bone_names", []):
		return false
	if first.get("material_names", []) != second.get("material_names", []):
		return false
	if int(first.get("texture_count", 0)) != int(second.get("texture_count", 0)):
		return false
	if first.get("helpers", []) != second.get("helpers", []):
		return false
	var first_lengths: Dictionary = first.get("clip_lengths", {})
	var second_lengths: Dictionary = second.get("clip_lengths", {})
	for clip_name: StringName in CANONICAL_CLIPS:
		if not first_lengths.has(clip_name) or not second_lengths.has(clip_name):
			return false
		if not is_equal_approx(float(first_lengths[clip_name]), float(second_lengths[clip_name])):
			return false
	return true


func _is_looping(clip_name: StringName) -> bool:
	var contract: Dictionary = _clip_contracts.get(clip_name, {})
	return bool(contract.get("loop", false))


func _find_imported_clip(player: AnimationPlayer, canonical_name: StringName) -> StringName:
	for candidate: StringName in player.get_animation_list():
		var candidate_text := String(candidate)
		if candidate == canonical_name or candidate_text.get_file() == String(canonical_name):
			return candidate
	return &""


func _animation_matches_rotation_contract(animation: Animation, skeleton: Skeleton3D, expected_tracks: Array) -> bool:
	# Godot 4.3's glTF importer emits one-key rest-pose tracks for extra deform bones
	# and collapses authored identity-only channels to one key. The manifest lists the
	# source channels, so require every source target to remain present, every imported
	# track to remain a valid rotation target, and at least one source channel to carry
	# actual multi-key motion. This accepts Godot's lossless static-track optimization.
	if animation.get_track_count() < expected_tracks.size():
		return false
	var expected_names: Dictionary = {}
	for expected_name: Variant in expected_tracks:
		expected_names[String(expected_name)] = true
	var found_expected_names: Dictionary = {}
	var dynamic_expected_track_count := 0
	for track_index: int in animation.get_track_count():
		if animation.track_get_type(track_index) != Animation.TYPE_ROTATION_3D:
			return false
		var track_path := String(animation.track_get_path(track_index))
		var bone_name := track_path.get_slice(":", 1) if track_path.contains(":") else track_path
		# The glTF root may be addressed directly as `root`; all other targets must
		# resolve to a real imported skeleton bone.
		if bone_name != "root" and skeleton.find_bone(bone_name) < 0:
			return false
		if expected_names.has(bone_name):
			found_expected_names[bone_name] = true
			if animation.track_get_key_count(track_index) > 1:
				dynamic_expected_track_count += 1
	return found_expected_names.size() == expected_names.size() and dynamic_expected_track_count > 0


func _nodes_of_type(root_node: Node, type_name: String) -> Array:
	var results: Array = []
	if root_node.is_class(type_name):
		results.append(root_node)
	for descendant: Node in root_node.find_children("*", type_name, true, false):
		results.append(descendant)
	return results


func _material_names(root_node: Node) -> Array:
	var names: Array = []
	for node: Node in _nodes_of_type(root_node, "MeshInstance3D"):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		for surface_index: int in mesh_instance.mesh.get_surface_count():
			var material := mesh_instance.get_active_material(surface_index)
			if material == null or material.resource_name.is_empty() or names.has(material.resource_name):
				continue
			names.append(material.resource_name)
	names.sort()
	return names


func _material_texture_count(root_node: Node) -> int:
	var texture_ids: Dictionary = {}
	for node: Node in _nodes_of_type(root_node, "MeshInstance3D"):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		for surface_index: int in mesh_instance.mesh.get_surface_count():
			var material := mesh_instance.get_active_material(surface_index)
			if material == null:
				continue
			for property_info: Dictionary in material.get_property_list():
				if int(property_info.get("type", TYPE_NIL)) != TYPE_OBJECT:
					continue
				var property_name := String(property_info.get("name", ""))
				if not property_name.ends_with("texture"):
					continue
				var texture := material.get(property_name) as Texture2D
				if texture != null:
					texture_ids[texture.get_instance_id()] = true
	return texture_ids.size()


func _pascal_case(value: String) -> String:
	var result := ""
	for segment: String in value.split("_", false):
		result += segment.capitalize()
	return result


func _report_candidate_failure(lod_level: int, candidate: Dictionary) -> void:
	var issues: PackedStringArray = candidate.get("issues", PackedStringArray())
	if issues.is_empty():
		return
	push_error("Lyra LOD%d import contract failed: %s" % [lod_level, "; ".join(issues)])


func _free_candidate(candidate: Dictionary) -> void:
	var instance := candidate.get("instance") as Node
	if instance != null and is_instance_valid(instance) and instance != _active_visual:
		instance.free()
