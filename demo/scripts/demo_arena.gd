class_name HeroDemoArena
extends Node3D
## Smoke-test arena: a player hero, one AI-controlled mirror, and static target dummies.

const HERO_SCENE := preload("res://heroes/hero_agile_hunter/scenes/hero_character.tscn")
const DRONE_SCENE := preload("res://heroes/hero_agile_hunter/scenes/training_drone.tscn")

var player_hero: HeroCharacter
var ai_hero: HeroCharacter


func _ready() -> void:
	_spawn_player()
	_spawn_ai_mirror()
	_spawn_training_drones()
	_build_arena_accents()


func _spawn_player() -> void:
	player_hero = HERO_SCENE.instantiate() as HeroCharacter
	player_hero.name = "LyraVesper_Player"
	player_hero.global_position = Vector3(0.0, 0.02, 4.0)
	player_hero.team_id = 1
	player_hero.set_control_mode(&"player")
	add_child(player_hero)
	var camera := get_node_or_null("FollowCamera") as DemoFollowCamera
	camera.set_target(player_hero.get_node_or_null("CameraTarget") as HeroCameraTarget)
	var hud := get_node_or_null("HUD") as HeroDemoHUD
	hud.set_hero(player_hero)


func _spawn_ai_mirror() -> void:
	ai_hero = HERO_SCENE.instantiate() as HeroCharacter
	ai_hero.name = "LyraVesper_AI"
	ai_hero.global_position = Vector3(0.0, 0.02, -7.0)
	ai_hero.team_id = 2
	ai_hero.set_control_mode(&"ai")
	ai_hero.set_meta("target_priority", 1.0)
	add_child(ai_hero)


func _spawn_training_drones() -> void:
	for position: Vector3 in [
		Vector3(-6.0, 0.0, -4.0),
		Vector3(6.0, 0.0, -4.0),
		Vector3(-8.5, 0.0, -11.0),
		Vector3(8.5, 0.0, -11.0),
	]:
		var drone := DRONE_SCENE.instantiate() as TrainingDrone
		drone.global_position = position
		drone.team_id = 2
		add_child(drone)


func _build_arena_accents() -> void:
	for position: Vector3 in [Vector3(-11, 0.1, 2), Vector3(11, 0.1, 2), Vector3(-11, 0.1, -13), Vector3(11, 0.1, -13)]:
		var pillar := MeshInstance3D.new()
		var mesh := CylinderMesh.new()
		mesh.top_radius = 0.28
		mesh.bottom_radius = 0.45
		mesh.height = 3.4
		pillar.mesh = mesh
		pillar.position = position + Vector3.UP * 1.7
		var material := StandardMaterial3D.new()
		material.albedo_color = Color("273057")
		material.metallic = 0.55
		material.roughness = 0.26
		pillar.material_override = material
		add_child(pillar)
