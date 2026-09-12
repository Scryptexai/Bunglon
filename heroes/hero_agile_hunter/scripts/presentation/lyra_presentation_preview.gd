extends Node3D
## Isolated authored-visual review scene for Phase 6.
## This scene intentionally contains no HeroCharacter gameplay or legacy primitive model.

@onready var visual: HeroPresentationAdapter = $Visual
@onready var review_camera: Camera3D = $ReviewCamera

var _clip_index := 0
var _clip_elapsed := 0.0


func _ready() -> void:
	visual.lod_policy = "automatic"
	visual.lod_reference_path = visual.get_path_to(review_camera)
	visual.initialize()
	if review_camera != null:
		review_camera.look_at(visual.global_position + Vector3(0.0, 1.15, 0.0), Vector3.UP, true)
	visual.play_clip(&"idle", true)


func _process(delta: float) -> void:
	if not visual.is_import_ready():
		return
	_clip_elapsed += delta
	var current_clip := visual.get_active_clip()
	var review_duration := maxf(1.2, visual.get_clip_duration(current_clip) + 0.3)
	if _clip_elapsed < review_duration:
		return
	_clip_elapsed = 0.0
	_clip_index = (_clip_index + 1) % HeroPresentationAdapter.CANONICAL_CLIPS.size()
	visual.play_clip(HeroPresentationAdapter.CANONICAL_CLIPS[_clip_index], true)
