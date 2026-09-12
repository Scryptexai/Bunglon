extends SceneTree
## Real-engine Phase 6 smoke coverage.
##
## Invoke after a Godot 4.3 project import:
##   godot --headless --path . --script res://tests/godot/phase6_integration_smoke.gd
##
## This is intentionally a SceneTree script instead of a Python GLB parser. It exercises
## Godot's own PackedScene import, AnimationPlayer, AnimationTree, Skeleton3D helpers,
## LOD replacement, and the player/AI intent bridge.

const ADAPTER_SCRIPT := preload("res://heroes/hero_agile_hunter/scripts/presentation/hero_presentation_adapter.gd")
const HERO_SCENE := preload("res://heroes/hero_agile_hunter/scenes/hero_character.tscn")
const PREVIEW_SCENE := preload("res://heroes/hero_agile_hunter/scenes/lyra_presentation_preview.tscn")
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
const HELPERS := [
	&"socket_weapon",
	&"socket_projectile",
	&"socket_camera_body",
	&"socket_camera_chest",
	&"socket_camera_head",
	&"socket_aim",
]
const MATERIALS := [
	"M_Lyra_OpaqueAtlas",
	"M_Lyra_LumenEnergy",
	"M_Lyra_AuroraMantle",
]

var _failed := false
var _semantic_events: Array[Dictionary] = []
var _clip_starts: Array[StringName] = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var manifest := _load_manifest()
	await _test_isolated_preview_scene()
	await _test_adapter(manifest)
	await _test_player_and_ai_intent_bridge()
	print("PHASE6_INTEGRATION_SMOKE result=%s" % ("FAIL" if _failed else "PASS"))
	quit(1 if _failed else 0)


func _load_manifest() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	_expect(parsed is Dictionary, "animation manifest parses in Godot")
	if parsed is Dictionary:
		return parsed
	return {}


func _test_isolated_preview_scene() -> void:
	var preview := PREVIEW_SCENE.instantiate() as Node3D
	_expect(preview != null, "isolated Lyra presentation preview instantiates")
	if preview == null:
		return
	get_root().add_child(preview)
	await process_frame
	await process_frame
	var adapter := preview.get_node_or_null("Visual") as HeroPresentationAdapter
	_expect(adapter != null and adapter.is_import_ready(), "preview replaces the character with imported LOD0 visual")
	_expect(_nodes_of_type(preview, "MeshInstance3D").size() >= 4, "preview contains imported meshes plus review floor")
	preview.queue_free()
	await process_frame


func _test_adapter(manifest: Dictionary) -> void:
	var adapter := ADAPTER_SCRIPT.new() as HeroPresentationAdapter
	adapter.name = "Phase6AdapterUnderTest"
	adapter.lod_policy = "lod0"
	adapter.semantic_event.connect(_on_semantic_event)
	adapter.clip_started.connect(_on_clip_started)
	get_root().add_child(adapter)
	await process_frame
	adapter.initialize()
	await process_frame
	await process_frame

	_expect(adapter.is_import_ready(), "adapter owns one imported visual hierarchy")
	if not adapter.is_import_ready():
		return
	_expect(adapter.get_active_lod() == 0, "adapter starts on LOD0")
	_expect(adapter.is_lod1_contract_safe(), "LOD1 is enabled only after matching imported contract validation")
	_expect(adapter.get_skeleton() != null and adapter.get_skeleton().get_bone_count() == 54, "adapter resolves the imported 54-bone skeleton")
	_expect(adapter.get_animation_player() != null, "adapter resolves imported AnimationPlayer")
	_expect(adapter.get_animation_tree() != null and adapter.get_animation_tree().active, "adapter builds and activates AnimationTree")
	var playback := adapter.get_animation_tree().get("parameters/playback") as AnimationNodeStateMachinePlayback
	_expect(playback != null, "AnimationTree exposes a state-machine playback controller")

	var material_names := adapter.get_material_names()
	for material_name: String in MATERIALS:
		_expect(material_names.has(material_name), "adapter retains imported material %s" % material_name)
	var lod0_contract := adapter.get_import_contract(0)
	var lod1_contract := adapter.get_import_contract(1)
	_expect(int(lod0_contract.get("texture_count", 0)) >= 8, "LOD0 exposes eight embedded material textures")
	_expect(int(lod1_contract.get("texture_count", 0)) >= 8, "LOD1 exposes eight embedded material textures")

	var manifest_clips := _manifest_clips(manifest)
	var player := adapter.get_animation_player()
	for clip_name: StringName in CANONICAL_CLIPS:
		_expect(adapter.has_clip(clip_name), "adapter maps canonical clip %s" % clip_name)
		if not adapter.has_clip(clip_name):
			continue
		var imported_name := _find_imported_name(player, clip_name)
		var animation := player.get_animation(imported_name)
		var expected: Dictionary = manifest_clips.get(clip_name, {})
		_expect(animation != null, "Godot imported animation resource for %s exists" % clip_name)
		if animation == null:
			continue
		_expect(is_equal_approx(animation.length, float(expected.get("duration_s", -1.0))), "clip %s duration matches manifest" % clip_name)
		var expected_loop := Animation.LOOP_LINEAR if bool(expected.get("loop", false)) else Animation.LOOP_NONE
		_expect(animation.loop_mode == expected_loop, "adapter applies manifest loop policy to %s" % clip_name)
		var expected_tracks: Array = expected.get("direct_rotation_tracks", [])
		_expect(_matches_rotation_tracks(animation, adapter.get_skeleton(), expected_tracks), "clip %s preserves its imported skeleton rotation contract" % clip_name)

	# Exercise every canonical state through the adapter-owned AnimationTree, rather
	# than only proving that the imported AnimationPlayer resources exist.
	for clip_name: StringName in CANONICAL_CLIPS:
		_expect(adapter.play_clip(clip_name, true), "AnimationTree accepts canonical state %s" % clip_name)
		await process_frame
		_expect(playback == null or playback.get_current_node() == clip_name, "AnimationTree reaches canonical state %s" % clip_name)

	for helper_name: StringName in HELPERS:
		var helper := adapter.get_helper(helper_name)
		_expect(helper != null, "adapter resolves helper %s" % helper_name)
		if helper is BoneAttachment3D:
			_expect((helper as BoneAttachment3D).bone_name == String(helper_name), "helper %s follows its imported helper bone" % helper_name)
	var body_socket := adapter.get_camera_body_socket()
	var head_socket := adapter.get_camera_head_socket()
	var projectile_socket := adapter.get_projectile_origin()
	_expect(body_socket != null and head_socket != null and head_socket.global_position.y > body_socket.global_position.y, "axis conversion keeps head helper above body helper")
	_expect(projectile_socket != null and (projectile_socket.global_position - adapter.global_position).z < -0.05, "axis conversion places the bow projectile helper at Godot forward -Z")
	_expect(adapter.get_skeleton().global_transform.basis.determinant() > 0.0, "axis conversion preserves a proper non-mirrored skeleton basis")

	_semantic_events.clear()
	_clip_starts.clear()
	adapter.play_clip(&"basic_attack", true)
	await create_timer(0.12).timeout
	var early_projectile_socket := adapter.get_projectile_origin().global_position
	await create_timer(0.48).timeout
	var late_projectile_socket := adapter.get_projectile_origin().global_position
	_expect(adapter.get_active_clip() == &"basic_attack", "AnimationTree remains on requested basic_attack state")
	_expect(playback == null or playback.get_current_node() == &"basic_attack", "AnimationTree transitions to basic_attack")
	_expect(early_projectile_socket.distance_to(late_projectile_socket) > 0.0005, "projectile helper follows imported bow/hand animation")
	_expect(_count_semantic(&"projectile_release") == 1, "basic_attack presentation release emits once")

	var swap_time := adapter.get_active_clip_time()
	adapter.lod_policy = "lod1"
	_expect(adapter.set_lod_level(1), "matching LOD1 swaps during active animation")
	await process_frame
	await process_frame
	_expect(adapter.get_active_lod() == 1, "LOD1 becomes active")
	_expect(adapter.get_active_clip() == &"basic_attack", "LOD swap preserves current named action")
	_expect(absf(adapter.get_active_clip_time() - swap_time) < 0.12, "LOD swap preserves animation time where feasible")
	await create_timer(0.12).timeout
	_expect(_count_semantic(&"projectile_release") == 1, "LOD swap does not replay already-passed release marker")

	adapter.play_clip(&"basic_attack", true)
	await create_timer(0.60).timeout
	_expect(_count_semantic(&"projectile_release") == 2, "explicit action restart emits one new release marker")
	_expect(_clip_starts.count(&"basic_attack") >= 2, "restarts are explicit visual actions, not per-frame resets")

	adapter.queue_free()
	await process_frame


func _test_player_and_ai_intent_bridge() -> void:
	var player_hero := HERO_SCENE.instantiate() as HeroCharacter
	var ai_hero := HERO_SCENE.instantiate() as HeroCharacter
	_expect(player_hero != null and ai_hero != null, "player and AI HeroCharacter scenes instantiate")
	if player_hero == null or ai_hero == null:
		return
	player_hero.name = "PlayerIntentHero"
	player_hero.position = Vector3(0.0, 0.1, 0.0)
	player_hero.team_id = 1
	player_hero.set_control_mode(&"player")
	ai_hero.name = "AIIntentHero"
	ai_hero.position = Vector3(0.0, 0.1, 9.0)
	ai_hero.team_id = 2
	ai_hero.set_control_mode(&"ai")
	get_root().add_child(player_hero)
	get_root().add_child(ai_hero)
	await process_frame
	await process_frame
	await create_timer(0.08).timeout

	_expect(player_hero.visual is HeroPresentationAdapter and player_hero.visual.is_import_ready(), "player hero uses imported presentation adapter")
	_expect(ai_hero.visual is HeroPresentationAdapter and ai_hero.visual.is_import_ready(), "AI hero uses imported presentation adapter")
	if player_hero.visual != null:
		_expect(player_hero.get_projectile_origin_position().distance_to(player_hero.visual.get_projectile_origin().global_position) < 0.0001, "authoritative projectile origin reads imported socket_projectile")
	var player_input := player_hero.get_node_or_null("Control/CharacterController/PlayerInput") as PlayerInputSource
	var player_ability_requests: Array[Dictionary] = []
	player_hero.ability_controller.ability_requested.connect(
		func(slot_id: StringName, accepted: bool) -> void:
			player_ability_requests.append({"slot": slot_id, "accepted": accepted})
	)
	_expect(player_input != null, "player input bridge is present")
	if player_input != null:
		player_input.request_mobile_ability(&"skill_02")
	for _frame: int in 4:
		await physics_frame
	var phase_step := player_hero.ability_controller.get_ability(&"skill_02")
	var latest_player_request: Dictionary = player_ability_requests.back() if not player_ability_requests.is_empty() else {}
	_expect(StringName(latest_player_request.get("slot", "")) == &"skill_02" and bool(latest_player_request.get("accepted", false)), "player input reaches and activates HeroAbility skill_02")
	_expect(phase_step != null and phase_step.phase != HeroAbility.Phase.READY, "player skill_02 lifecycle remains active while its imported clip plays")
	_expect(player_hero.visual.get_active_clip() == &"skill_02", "player intent maps through HeroAbility and driver to imported skill_02")

	await create_timer(0.18).timeout
	_expect(not ai_hero.visual.get_active_clip().is_empty(), "AI intent reaches the same imported presentation adapter")
	_expect(ai_hero.visual.get_active_clip() in [&"basic_attack", &"skill_01", &"skill_03"], "AI requests a canonical imported combat clip")

	player_hero.queue_free()
	ai_hero.queue_free()
	await process_frame


func _manifest_clips(manifest: Dictionary) -> Dictionary:
	var result: Dictionary = {}
	var animation_contract: Dictionary = manifest.get("animation_contract", {})
	for raw_clip: Variant in animation_contract.get("clips", []):
		if raw_clip is Dictionary:
			var clip: Dictionary = raw_clip
			result[StringName(clip.get("name", ""))] = clip
	return result


func _matches_rotation_tracks(animation: Animation, skeleton: Skeleton3D, expected_tracks: Array) -> bool:
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
		if bone_name != "root" and skeleton.find_bone(bone_name) < 0:
			return false
		if expected_names.has(bone_name):
			found_expected_names[bone_name] = true
			if animation.track_get_key_count(track_index) > 1:
				dynamic_expected_track_count += 1
	return found_expected_names.size() == expected_names.size() and dynamic_expected_track_count > 0


func _find_imported_name(player: AnimationPlayer, clip_name: StringName) -> StringName:
	for candidate: StringName in player.get_animation_list():
		if candidate == clip_name or String(candidate).get_file() == String(clip_name):
			return candidate
	return &""


func _nodes_of_type(root_node: Node, type_name: String) -> Array:
	var results: Array = []
	if root_node.is_class(type_name):
		results.append(root_node)
	for descendant: Node in root_node.find_children("*", type_name, true, false):
		results.append(descendant)
	return results


func _on_semantic_event(event_id: StringName, clip_name: StringName, event_time_s: float, socket_position: Vector3) -> void:
	_semantic_events.append({
		"event_id": event_id,
		"clip_name": clip_name,
		"time_s": event_time_s,
		"socket_position": socket_position,
	})


func _on_clip_started(clip_name: StringName, _restart: bool) -> void:
	_clip_starts.append(clip_name)


func _count_semantic(event_id: StringName) -> int:
	var count := 0
	for event_data: Dictionary in _semantic_events:
		if event_data.get("event_id", &"") == event_id:
			count += 1
	return count


func _expect(condition: bool, message: String) -> void:
	if condition:
		print("PHASE6_INTEGRATION_SMOKE PASS %s" % message)
		return
	_failed = true
	push_error("PHASE6_INTEGRATION_SMOKE FAIL %s" % message)
