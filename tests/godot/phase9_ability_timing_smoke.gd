extends SceneTree
## Real-engine Phase 9 ability lifecycle and authored-timing smoke coverage.
##
## Invoke after a Godot 4.3 project import:
##   godot --headless --path . --script res://tests/godot/phase9_ability_timing_smoke.gd
##
## This executes actual HeroAbility components against imported Lyra presentation. It
## confirms that gameplay owns independent timers while those timers read the validated
## manifest contract once at cast start; no presentation signal authorizes damage/dashes.

const HERO_SCENE := preload("res://heroes/hero_agile_hunter/scenes/hero_character.tscn")
const DRONE_SCENE := preload("res://heroes/hero_agile_hunter/scenes/training_drone.tscn")
const TIME_TOLERANCE := 0.13

var _failed := false


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var floor := _build_floor()
	var hero := await _spawn_hero("Phase9AbilityHero", Vector3.ZERO)
	var primary: TrainingDrone
	var radial: TrainingDrone
	var distant: TrainingDrone
	if hero != null:
		await _test_target_requirement_guard(hero)
		primary = await _spawn_drone("Phase9Primary", Vector3(0.0, 0.0, -5.0), 2)
		radial = await _spawn_drone("Phase9Radial", Vector3(2.1, 0.0, -5.0), 2)
		distant = await _spawn_drone("Phase9Distant", Vector3(0.0, 0.0, -80.0), 2)
		if primary != null and radial != null and distant != null:
			await _test_phase_step_timing(hero, distant)
			_reset_hero_position(hero)
			await _test_prism_volley_timing(hero, primary)
			await _test_tether_timing_and_root(hero, primary)
			await _test_ultimate_timing_and_radial(hero, primary, radial)
		hero.queue_free()
	if primary != null:
		primary.queue_free()
	if radial != null:
		radial.queue_free()
	if distant != null:
		distant.queue_free()
	await process_frame
	var cancellation_hero := await _spawn_hero("Phase9CancellationHero", Vector3(10.0, 0.0, 0.0))
	var cancellation_target := await _spawn_drone("Phase9CancellationTarget", Vector3(10.0, 0.0, -5.0), 2)
	if cancellation_hero != null and cancellation_target != null:
		await _test_target_loss_cancellation(cancellation_hero, cancellation_target)
	if cancellation_hero != null:
		cancellation_hero.queue_free()
	if cancellation_target != null:
		cancellation_target.queue_free()
	if floor != null:
		floor.queue_free()
	await process_frame
	await process_frame
	print("PHASE9_ABILITY_TIMING_SMOKE result=%s" % ("FAIL" if _failed else "PASS"))
	quit(1 if _failed else 0)


func _build_floor() -> StaticBody3D:
	var floor := StaticBody3D.new()
	floor.name = "Phase9Floor"
	floor.position = Vector3(0.0, -0.15, 0.0)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(180.0, 0.3, 180.0)
	collision.shape = shape
	floor.add_child(collision)
	get_root().add_child(floor)
	return floor


func _spawn_hero(hero_name: String, spawn_position: Vector3) -> HeroCharacter:
	var hero := HERO_SCENE.instantiate() as HeroCharacter
	_expect(hero != null, "%s HeroCharacter instantiates" % hero_name)
	if hero == null:
		return null
	hero.name = hero_name
	hero.position = spawn_position + Vector3.UP * 0.1
	hero.team_id = 1
	hero.set_control_mode(&"player")
	get_root().add_child(hero)
	await process_frame
	await process_frame
	await physics_frame
	_expect(hero.is_combat_ready() and hero.visual.is_import_ready(), "%s initializes gameplay and imported presentation" % hero_name)
	return hero


func _spawn_drone(drone_name: String, spawn_position: Vector3, team_id: int) -> TrainingDrone:
	var drone := DRONE_SCENE.instantiate() as TrainingDrone
	_expect(drone != null, "%s TrainingDrone instantiates" % drone_name)
	if drone == null:
		return null
	drone.name = drone_name
	drone.position = spawn_position
	drone.team_id = team_id
	get_root().add_child(drone)
	await process_frame
	await physics_frame
	_expect(drone.damage_receiver != null and drone.damage_receiver.is_targetable(), "%s is a valid combat target" % drone_name)
	return drone


func _test_target_requirement_guard(hero: HeroCharacter) -> void:
	var prism := hero.ability_controller.get_ability(&"skill_01")
	_expect(prism != null, "Prism Volley ability is registered")
	if prism == null:
		return
	var energy_before := hero.energy.current_energy
	_expect(not hero.ability_controller.try_activate(&"skill_01", null, Vector3.FORWARD), "targeted Prism Volley rejects an absent target")
	_expect(is_equal_approx(hero.energy.current_energy, energy_before) and prism.cooldown_remaining <= 0.0, "rejected targeted cast spends no energy or cooldown")


func _test_phase_step_timing(hero: HeroCharacter, distant_target: TrainingDrone) -> void:
	var phase_step := hero.ability_controller.get_ability(&"skill_02")
	_expect(phase_step != null, "Phase Step ability is registered")
	if phase_step == null:
		return
	var dash_clip_times: Array[float] = []
	hero.movement.dash_started.connect(func(_direction: Vector3) -> void: dash_clip_times.append(hero.visual.get_active_clip_time()))
	var energy_before := hero.energy.current_energy
	_expect(hero.ability_controller.try_activate(&"skill_02", distant_target, Vector3.RIGHT), "non-targeted Phase Step accepts an optional distant target")
	_expect(is_equal_approx(hero.energy.current_energy, energy_before - phase_step.energy_cost), "Phase Step commits its energy at accepted cast")
	_expect(hero.visual.get_active_clip() == &"skill_02", "Phase Step requests the imported skill_02 clip")
	await create_timer(0.22).timeout
	_expect(dash_clip_times.size() == 1, "Phase Step starts one authoritative dash")
	var dash_time := dash_clip_times[0] if dash_clip_times.size() == 1 else -1.0
	_expect(absf(dash_time - 0.1344) < TIME_TOLERANCE, "Phase Step dash begins at authored dash_start timing")
	_expect(hero.get_statuses().has_status(&"phase_shift"), "Phase Step immunity opens with the authoritative dash")
	await create_timer(0.38).timeout
	_expect(not hero.movement.is_dashing() and not hero.get_statuses().has_status(&"phase_shift"), "Phase Step dash and immunity close after authored window")
	_expect(phase_step.phase == HeroAbility.Phase.READY, "Phase Step lifecycle recovers at authored clip end")


func _test_prism_volley_timing(hero: HeroCharacter, target: TrainingDrone) -> void:
	var prism := hero.ability_controller.get_ability(&"skill_01")
	_expect(prism != null, "Prism Volley remains available after Phase Step")
	if prism == null:
		return
	var projectile_records: Array[Dictionary] = []
	var presentation_releases: Array[StringName] = []
	var lifecycle: Array[StringName] = []
	hero.projectile_spawned.connect(
		func(_projectile: EnergyProjectile, _target: Node3D, event: DamageEvent) -> void:
			if event.attack_source == &"prism_volley":
				projectile_records.append({"clip_time": hero.visual.get_active_clip_time(), "event": event})
	)
	hero.visual.semantic_event.connect(
		func(event_id: StringName, clip_name: StringName, _time_s: float, _socket: Vector3) -> void:
			if clip_name == &"skill_01" and String(event_id).begins_with("volley_release_"):
				presentation_releases.append(event_id)
	)
	prism.cast_started.connect(func(_ability: HeroAbility, _target: Node3D) -> void: lifecycle.append(&"cast"))
	prism.activated.connect(func(_ability: HeroAbility, _target: Node3D) -> void: lifecycle.append(&"action"))
	prism.recovery_started.connect(func(_ability: HeroAbility) -> void: lifecycle.append(&"recovery"))
	prism.finished.connect(func(_ability: HeroAbility) -> void: lifecycle.append(&"finished"))
	var energy_before := hero.energy.current_energy
	_expect(hero.ability_controller.try_activate(&"skill_01", target, Vector3.FORWARD), "Prism Volley accepts an in-range hostile")
	_expect(is_equal_approx(hero.energy.current_energy, energy_before - prism.energy_cost), "Prism Volley commits its configured energy")
	await create_timer(1.15).timeout
	_expect(projectile_records.size() == 3, "Prism Volley emits exactly three authoritative arrows")
	_expect(presentation_releases.size() == 3, "Prism Volley retains three cosmetic authored release markers")
	var expected_times := [0.4600, 0.5612, 0.6624]
	for index: int in mini(projectile_records.size(), expected_times.size()):
		var actual_time := float(projectile_records[index].get("clip_time", -1.0))
		_expect(absf(actual_time - expected_times[index]) < TIME_TOLERANCE, "Prism arrow %d follows its authored release timing" % (index + 1))
	_expect(lifecycle.has(&"cast") and lifecycle.has(&"action") and lifecycle.has(&"recovery") and lifecycle.has(&"finished"), "Prism Volley completes cast/action/recovery lifecycle")
	_expect(prism.phase == HeroAbility.Phase.READY, "Prism Volley returns to ready after imported clip timing")


func _test_tether_timing_and_root(hero: HeroCharacter, target: TrainingDrone) -> void:
	var tether := hero.ability_controller.get_ability(&"skill_03")
	_expect(tether != null, "Tether Snare ability is registered")
	if tether == null:
		return
	var projectile_times: Array[float] = []
	var tether_damage: Array[DamageEvent] = []
	hero.projectile_spawned.connect(
		func(_projectile: EnergyProjectile, _target: Node3D, event: DamageEvent) -> void:
			if event.attack_source == &"tether_snare":
				projectile_times.append(hero.visual.get_active_clip_time())
	)
	target.damage_receiver.damage_received.connect(
		func(event: DamageEvent, _amount: float) -> void:
			if event.attack_source == &"tether_snare":
				tether_damage.append(event)
	)
	var energy_before := hero.energy.current_energy
	_expect(hero.ability_controller.try_activate(&"skill_03", target, Vector3.FORWARD), "Tether Snare accepts its hostile target")
	_expect(is_equal_approx(hero.energy.current_energy, energy_before - tether.energy_cost), "Tether Snare commits its configured energy")
	await create_timer(1.16).timeout
	_expect(projectile_times.size() == 1, "Tether Snare emits one authoritative projectile")
	var tether_time := projectile_times[0] if projectile_times.size() == 1 else -1.0
	_expect(absf(tether_time - 0.7280) < TIME_TOLERANCE, "Tether projectile begins at authored release timing")
	_expect(tether_damage.size() == 1 and target.statuses.has_status(&"root"), "Tether projectile deals damage and applies root through DamageReceiver")
	_expect(tether.phase == HeroAbility.Phase.READY, "Tether Snare returns to ready after authored recovery")
	await create_timer(1.10).timeout
	_expect(not target.statuses.has_status(&"root"), "Tether root expires through StatusComponent")


func _test_ultimate_timing_and_radial(hero: HeroCharacter, target: TrainingDrone, radial_target: TrainingDrone) -> void:
	var ultimate := hero.ability_controller.get_ability(&"ultimate")
	_expect(ultimate != null, "Apex Constellation ability is registered")
	if ultimate == null:
		return
	var projectile_records: Array[Dictionary] = []
	var ultimate_markers: Array[StringName] = []
	var radial_damage: Array[DamageEvent] = []
	hero.projectile_spawned.connect(
		func(_projectile: EnergyProjectile, _target: Node3D, event: DamageEvent) -> void:
			if event.attack_source == &"apex_constellation":
				projectile_records.append({"clip_time": hero.visual.get_active_clip_time(), "event": event})
	)
	hero.visual.semantic_event.connect(
		func(event_id: StringName, clip_name: StringName, _time_s: float, _socket: Vector3) -> void:
			if clip_name == &"ultimate" and event_id in [&"ultimate_release", &"ultimate_impact_window"]:
				ultimate_markers.append(event_id)
	)
	radial_target.damage_receiver.damage_received.connect(
		func(event: DamageEvent, _amount: float) -> void:
			if event.attack_source == &"apex_constellation":
				radial_damage.append(event)
	)
	var energy_before := hero.energy.current_energy
	_expect(hero.ability_controller.try_activate(&"ultimate", target, Vector3.FORWARD), "Apex Constellation accepts an in-range hostile")
	_expect(is_equal_approx(hero.energy.current_energy, energy_before - ultimate.energy_cost), "Apex Constellation commits its configured energy")
	_expect(hero.movement.is_action_locked() and not hero.is_basic_attack_allowed(), "ultimate owns movement and basic-attack locks during cast")
	_expect(not hero.basic_attack.try_attack(target), "basic attack cannot bypass the active ultimate lock")
	await create_timer(2.05).timeout
	_expect(projectile_records.size() == 3, "Apex Constellation emits exactly three authoritative arrows")
	_expect(ultimate_markers.size() == 2, "ultimate retains authored release and final-impact presentation markers")
	var expected_times := [1.2376, 1.3650, 1.4924]
	for index: int in mini(projectile_records.size(), expected_times.size()):
		var actual_time := float(projectile_records[index].get("clip_time", -1.0))
		_expect(absf(actual_time - expected_times[index]) < TIME_TOLERANCE, "ultimate arrow %d follows authored release/impact timing" % (index + 1))
	var finisher_count := 0
	for record: Dictionary in projectile_records:
		var event := record.get("event") as DamageEvent
		if event != null and bool(event.metadata.get("finisher", false)):
			finisher_count += 1
	_expect(finisher_count == 1, "only the third ultimate projectile carries finisher payload")
	_expect(radial_damage.size() == 1 and radial_target.statuses.has_status(&"slow"), "ultimate finisher applies one radial slow/damage event to nearby hostile")
	_expect(ultimate.phase == HeroAbility.Phase.READY and not hero.movement.is_action_locked() and hero.is_basic_attack_allowed(), "ultimate releases gameplay locks after authored recovery")


func _test_target_loss_cancellation(hero: HeroCharacter, target: TrainingDrone) -> void:
	var prism := hero.ability_controller.get_ability(&"skill_01")
	_expect(prism != null, "cancellation hero has Prism Volley")
	if prism == null:
		return
	var spawned: Array[DamageEvent] = []
	var failures: Array[StringName] = []
	hero.projectile_spawned.connect(
		func(_projectile: EnergyProjectile, _target: Node3D, event: DamageEvent) -> void:
			if event.attack_source == &"prism_volley":
				spawned.append(event)
	)
	prism.failed.connect(func(_ability: HeroAbility, reason: StringName) -> void: failures.append(reason))
	_expect(hero.ability_controller.try_activate(&"skill_01", target, Vector3.FORWARD), "targeted cast begins before target-loss check")
	target.remove_from_group("targetable")
	await create_timer(0.72).timeout
	_expect(prism.phase == HeroAbility.Phase.READY and failures.has(&"target_lost"), "target loss during cast cancels the ability lifecycle")
	_expect(spawned.is_empty(), "cancelled targeted cast cannot emit a stale projectile")


func _reset_hero_position(hero: HeroCharacter) -> void:
	hero.movement.force_stop()
	hero.global_position = Vector3(0.0, 0.1, 0.0)


func _expect(condition: bool, message: String) -> void:
	if condition:
		print("PHASE9_ABILITY_TIMING_SMOKE PASS %s" % message)
		return
	_failed = true
	push_error("PHASE9_ABILITY_TIMING_SMOKE FAIL %s" % message)
