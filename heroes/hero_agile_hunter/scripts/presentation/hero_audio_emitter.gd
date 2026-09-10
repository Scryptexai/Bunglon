class_name HeroAudioEmitter
extends Node3D
## Audio routing facade. Gameplay sends semantic events, never references audio assets directly.

signal audio_event_requested(event_id: StringName)

const STREAMS := {
	&"weapon_draw": "res://heroes/hero_agile_hunter/audio/weapon_draw.wav",
	&"weapon_release": "res://heroes/hero_agile_hunter/audio/weapon_release.wav",
	&"projectile": "res://heroes/hero_agile_hunter/audio/projectile.wav",
	&"hit": "res://heroes/hero_agile_hunter/audio/hit.wav",
	&"skill_cast": "res://heroes/hero_agile_hunter/audio/skill_cast.wav",
	&"ultimate": "res://heroes/hero_agile_hunter/audio/ultimate.wav",
	&"damage_taken": "res://heroes/hero_agile_hunter/audio/damage_taken.wav",
	&"death": "res://heroes/hero_agile_hunter/audio/death.wav",
	&"movement": "res://heroes/hero_agile_hunter/audio/footstep.wav",
	&"voice": "res://heroes/hero_agile_hunter/audio/voice_callout.wav",
}

var _players: Dictionary = {}


func initialize() -> void:
	_players = {
		&"Voice": get_node_or_null("Voice") as AudioStreamPlayer3D,
		&"Attack": get_node_or_null("Attack") as AudioStreamPlayer3D,
		&"Skill": get_node_or_null("Skill") as AudioStreamPlayer3D,
		&"Movement": get_node_or_null("Movement") as AudioStreamPlayer3D,
	}


func play_event(event_id: StringName) -> void:
	var stream_path := String(STREAMS.get(event_id, ""))
	if stream_path.is_empty():
		return
	var player := _players.get(_channel_for(event_id)) as AudioStreamPlayer3D
	if player == null:
		return
	var stream := load(stream_path) as AudioStream
	if stream != null:
		player.stream = stream
		player.play()
	audio_event_requested.emit(event_id)


func _channel_for(event_id: StringName) -> StringName:
	match event_id:
		&"ultimate", &"skill_cast":
			return &"Skill"
		&"movement":
			return &"Movement"
		&"voice", &"death", &"damage_taken":
			return &"Voice"
		_:
			return &"Attack"
