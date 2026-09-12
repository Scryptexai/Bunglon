extends SceneTree
## Phase 6 real-engine import probe.
##
## This intentionally talks to Godot's imported PackedScene resources rather than parsing
## the source GLB. Its structured output makes an importer conversion visible in CI logs.

const ASSETS := [
	"res://character_animated/lyra_vesper_animated.glb",
	"res://character_animated/lyra_vesper_animated_lod1.glb",
]
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

const HELPER_BONES := [
	&"socket_weapon",
	&"socket_projectile",
	&"socket_camera_body",
	&"socket_camera_chest",
	&"socket_camera_head",
	&"socket_aim",
]

var _failed: bool = false


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var manifest_clips := _load_manifest_clips()
	for asset_path: String in ASSETS:
		await _probe_asset(asset_path, manifest_clips)
	print("PHASE6_IMPORT_PROBE result=%s" % ("FAIL" if _failed else "PASS"))
	quit(1 if _failed else 0)


func _probe_asset(asset_path: String, manifest_clips: Dictionary) -> void:
	var packed := ResourceLoader.load(asset_path) as PackedScene
	_expect(packed != null, "%s resolves to a PackedScene" % asset_path)
	if packed == null:
		return
	var instance := packed.instantiate() as Node
	_expect(instance != null, "%s instantiates" % asset_path)
	if instance == null:
		return
	get_root().add_child(instance)
	await process_frame

	var players := _nodes_of_type(instance, "AnimationPlayer")
	var skeletons := _nodes_of_type(instance, "Skeleton3D")
	var meshes := _nodes_of_type(instance, "MeshInstance3D")
	_expect(players.size() == 1, "%s has exactly one imported AnimationPlayer (%d found)" % [asset_path, players.size()])
	_expect(skeletons.size() == 1, "%s has exactly one imported Skeleton3D (%d found)" % [asset_path, skeletons.size()])
	_expect(meshes.size() >= 3, "%s exposes the authored skinned mesh instances (%d found)" % [asset_path, meshes.size()])
	if players.is_empty() or skeletons.is_empty():
		instance.queue_free()
		await process_frame
		return

	var player := players[0] as AnimationPlayer
	var skeleton := skeletons[0] as Skeleton3D
	print("PHASE6_IMPORT_PROBE asset=%s root=%s player_path=%s skeleton_path=%s bones=%d animations=%s" % [
		asset_path,
		instance.get_class(),
		String(instance.get_path()),
		String(player.get_path()),
		skeleton.get_bone_count(),
		str(player.get_animation_list()),
	])
	_expect(skeleton.get_bone_count() >= 54, "%s preserves the 54-joint imported skeleton (%d bones)" % [asset_path, skeleton.get_bone_count()])

	for helper_name: StringName in HELPER_BONES:
		var helper_node := instance.find_child(String(helper_name), true, false) as Node3D
		var bone_index := skeleton.find_bone(helper_name)
		print("PHASE6_IMPORT_PROBE helper=%s node=%s bone_index=%d" % [helper_name, helper_node != null, bone_index])
		_expect(helper_node != null or bone_index >= 0, "%s preserves helper %s as a node or skeleton bone" % [asset_path, helper_name])

	var projectile_helper := instance.find_child("socket_projectile", true, false) as Node3D
	if projectile_helper == null:
		# Godot may represent a helper joint as a skeleton bone rather than preserving
		# a named attachment node. Resolve it through the engine Skeleton3D API.
		projectile_helper = BoneAttachment3D.new()
		projectile_helper.name = "ProbeProjectileSocket"
		projectile_helper.bone_name = "socket_projectile"
		skeleton.add_child(projectile_helper)
		await process_frame

	for clip_name: StringName in CANONICAL_CLIPS:
		var imported_name := _find_imported_clip(player, clip_name)
		_expect(not imported_name.is_empty(), "%s imports clip %s" % [asset_path, clip_name])
		if imported_name.is_empty():
			continue
		var animation := player.get_animation(imported_name)
		_expect(animation != null and animation.get_track_count() > 0, "%s clip %s has imported tracks" % [asset_path, clip_name])
		if animation != null:
			var expected: Dictionary = manifest_clips.get(clip_name, {})
			var expected_tracks: Array = expected.get("direct_rotation_tracks", [])
			print("PHASE6_IMPORT_PROBE clip=%s importer_name=%s length=%.4f loop=%d tracks=%d metadata=%s" % [
				clip_name,
				imported_name,
				animation.length,
				animation.loop_mode,
				animation.get_track_count(),
				str(animation.get_meta_list()),
			])
			_expect(is_equal_approx(animation.length, float(expected.get("duration_s", -1.0))), "%s clip %s duration matches manifest" % [asset_path, clip_name])
			_expect(_matches_rotation_tracks(animation, skeleton, expected_tracks), "%s clip %s preserves imported bone rotation tracks" % [asset_path, clip_name])
			player.play(imported_name)
			await create_timer(0.02).timeout
			_expect(player.current_animation == imported_name, "%s AnimationPlayer plays %s" % [asset_path, clip_name])
	player.stop()
	var basic_attack_name := _find_imported_clip(player, &"basic_attack")
	var initial_projectile_position := projectile_helper.global_position
	player.play(basic_attack_name)
	await create_timer(0.14).timeout
	var drawn_projectile_position := projectile_helper.global_position
	await create_timer(0.42).timeout
	var released_projectile_position := projectile_helper.global_position
	_expect(initial_projectile_position.distance_to(drawn_projectile_position) > 0.0005 or drawn_projectile_position.distance_to(released_projectile_position) > 0.0005, "%s socket_projectile follows imported basic_attack bone motion" % asset_path)
	player.stop()

	var material_names: Array[String] = []
	for mesh_node: Node in meshes:
		var mesh_instance := mesh_node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		for surface_index: int in mesh_instance.mesh.get_surface_count():
			var material := mesh_instance.get_active_material(surface_index)
			if material != null and not material.resource_name.is_empty() and material.resource_name not in material_names:
				material_names.append(material.resource_name)
	var texture_count := _material_texture_count(meshes)
	print("PHASE6_IMPORT_PROBE asset=%s material_names=%s mesh_count=%d texture_count=%d" % [asset_path, str(material_names), meshes.size(), texture_count])
	_expect(texture_count >= 8, "%s imports eight authored material texture references" % asset_path)
	_expect(material_names.has("M_Lyra_OpaqueAtlas"), "%s preserves M_Lyra_OpaqueAtlas" % asset_path)
	_expect(material_names.has("M_Lyra_LumenEnergy"), "%s preserves M_Lyra_LumenEnergy" % asset_path)
	_expect(material_names.has("M_Lyra_AuroraMantle"), "%s preserves M_Lyra_AuroraMantle" % asset_path)

	instance.queue_free()
	await process_frame


func _load_manifest_clips() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	_expect(parsed is Dictionary, "animation manifest parses through Godot JSON")
	if not (parsed is Dictionary):
		return {}
	var manifest: Dictionary = parsed
	var animation_contract: Dictionary = manifest.get("animation_contract", {})
	var clips: Dictionary = {}
	for raw_clip: Variant in animation_contract.get("clips", []):
		if raw_clip is Dictionary:
			var clip: Dictionary = raw_clip
			clips[StringName(clip.get("name", ""))] = clip
	return clips


func _matches_rotation_tracks(animation: Animation, skeleton: Skeleton3D, expected_tracks: Array) -> bool:
	# Godot 4.3 adds one-key rest-pose tracks and collapses source identity-only
	# channels. Every authored target must survive, every imported target must remain
	# a rotation target, and each clip must retain at least one multi-key source motion.
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


func _material_texture_count(meshes: Array[Node]) -> int:
	var texture_ids: Dictionary = {}
	for mesh_node: Node in meshes:
		var mesh_instance := mesh_node as MeshInstance3D
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


func _nodes_of_type(root_node: Node, type_name: String) -> Array[Node]:
	var results: Array[Node] = []
	if root_node.is_class(type_name):
		results.append(root_node)
	for descendant: Node in root_node.find_children("*", type_name, true, false):
		results.append(descendant)
	return results


func _find_imported_clip(player: AnimationPlayer, canonical_name: StringName) -> StringName:
	for candidate: StringName in player.get_animation_list():
		var candidate_text := String(candidate)
		if candidate == canonical_name or candidate_text.get_file() == String(canonical_name):
			return candidate
	return &""


func _expect(condition: bool, message: String) -> void:
	if condition:
		print("PHASE6_IMPORT_PROBE PASS %s" % message)
		return
	_failed = true
	push_error("PHASE6_IMPORT_PROBE FAIL %s" % message)
