class_name DamageReceiver
extends Node
## The sole HP damage gateway for a combatant.

signal damage_received(event: DamageEvent, resolved_amount: float)
signal damage_avoided(event: DamageEvent, reason: StringName)

var character: Node3D
var stats: StatsComponent
var health: HealthComponent
var statuses: StatusComponent
var animation_driver: HeroAnimationDriver
var vfx: HeroVFXController
var audio: HeroAudioEmitter


func initialize(
	owner_character: Node3D,
	owner_stats: StatsComponent,
	owner_health: HealthComponent,
	owner_statuses: StatusComponent,
	owner_animation: HeroAnimationDriver,
	owner_vfx: HeroVFXController,
	owner_audio: HeroAudioEmitter
) -> void:
	character = owner_character
	stats = owner_stats
	health = owner_health
	statuses = owner_statuses
	animation_driver = owner_animation
	vfx = owner_vfx
	audio = owner_audio


func is_targetable() -> bool:
	return health != null and not health.is_dead


func receive_damage(event: DamageEvent) -> bool:
	if event == null or not is_targetable():
		return false
	if statuses != null and statuses.is_damage_immune():
		damage_avoided.emit(event, &"phase_shift")
		if vfx != null:
			vfx.play_effect(&"evade", character.global_position + Vector3.UP)
		return false
	var resolved_amount := _resolve_damage(event)
	if resolved_amount <= 0.0:
		return false
	event.target = character
	event.metadata["resolved_amount"] = resolved_amount
	if not event.status_payload.is_empty() and statuses != null:
		var status_id := StringName(event.status_payload.get("id", ""))
		var duration := float(event.status_payload.get("duration", 0.0))
		var magnitude := float(event.status_payload.get("magnitude", 1.0))
		if not status_id.is_empty() and duration > 0.0:
			statuses.apply_status(status_id, duration, magnitude, event.source)
	if health.apply_damage(resolved_amount, event):
		damage_received.emit(event, resolved_amount)
		if animation_driver != null and not health.is_dead:
			animation_driver.play_hit(resolved_amount >= 120.0)
		if vfx != null:
			vfx.play_effect(&"hit", event.impact_position if event.impact_position != Vector3.ZERO else character.global_position + Vector3.UP)
		if audio != null:
			audio.play_event(&"damage_taken")
		return true
	return false


func _resolve_damage(event: DamageEvent) -> float:
	var raw := event.final_raw_amount()
	if event.damage_type == DamageEvent.DamageType.TRUE:
		return raw
	var resistance := 0.0
	if event.damage_type == DamageEvent.DamageType.PHYSICAL:
		resistance = stats.get_stat(&"defense") if stats != null else 0.0
	else:
		resistance = stats.get_stat(&"energy_resistance") if stats != null else 0.0
	resistance -= float(event.modifiers.get("penetration", 0.0))
	# A stable MOBA-style diminishing mitigation curve that remains expandable.
	return raw * (100.0 / (100.0 + maxf(-75.0, resistance)))
