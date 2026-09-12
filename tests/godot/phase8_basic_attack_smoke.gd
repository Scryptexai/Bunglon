extends SceneTree
## Real-engine Phase 8 basic-attack and projectile authority smoke coverage.
##
## Invoke after a Godot 4.3 project import:
##   godot --headless --path . --script res://tests/godot/phase8_basic_attack_smoke.gd
##
## The test uses the live HeroCharacter and TrainingDrone scenes. It proves that basic
## attack target validation, windup, imported-socket spawn placement, damage delivery,
## and target-loss cancellation stay in gameplay code rather than GLB semantic markers.

const HERO_SCENE := preload("res://heroes/hero_agile_hunter/scenes/hero_character.tscn")
const DRONE_SCENE := preload("res://heroes/hero_agile_hunter/scenes/training_drone.tscn")

var _failed := false


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var floor := _build_floor()
	var hero := await _spawn_hero()
	var friendly := await _spawn_drone("FriendlyDrone", Vector3(0.0, 0.0, -4.0), 1)
	var enemy := await _spawn_drone("EnemyDrone", Vector3(0.0, 0.0, -7.0), 2)
	var far_enemy := await _spawn_drone("FarEnemyDrone", Vector3(0.0, 0.0, -25.0), 2)
	if hero != null and friendly != null and enemy != null and far_enemy != null:
		await _test_targeting_and_basic_attack(hero, friendly, enemy, far_enemy)
		hero.queue_free()
		friendly.queue_free()
		enemy.queue_free()
		far_enemy.queue_free()
	if floor != null:
		floor.queue_free()
	await process_frame
	await process_frame
	print("PHASE8_BASIC_ATTACK_SMOKE result=%s" % ("FAIL" if _failed else "PASS"))
	quit(1 if _failed else 0)


func _build_floor() -> StaticBody3D:
	var floor := StaticBody3D.new()
	floor.name = "Phase8Floor"
	floor.position = Vector3(0.0, -0.15, 0.0)
	var collision := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(60.0, 0.3, 60.0)
	collision.shape = shape
	floor.add_child(collision)
	get_root().add_child(floor)
	return floor


func _spawn_hero() -> HeroCharacter:
	var hero := HERO_SCENE.instantiate() as HeroCharacter
	_expect(hero != null, "HeroCharacter scene instantiates for basic-attack test")
	if hero == null:
		return null
	hero.name = "Phase8AttackHero"
	hero.position = Vector3(0.0, 0.1, 0.0)
	hero.team_id = 1
	hero.set_control_mode(&"player")
	get_root().add_child(hero)
	await process_frame
	await process_frame
	await physics_frame
	_expect(hero.is_combat_ready(), "hero initializes combat components")
	_expect(hero.visual != null and hero.visual.is_import_ready(), "hero retains imported authored presentation")
	return hero


func _spawn_drone(drone_name: String, spawn_position: Vector3, team_id: int) -> TrainingDrone:
	var drone := DRONE_SCENE.instantiate() as TrainingDrone
	_expect(drone != null, "%s scene instantiates" % drone_name)
	if drone == null:
		return null
	drone.name = drone_name
	drone.position = spawn_position
	drone.team_id = team_id
	get_root().add_child(drone)
	await process_frame
	await physics_frame
	_expect(drone.damage_receiver != null and drone.damage_receiver.is_targetable(), "%s exposes a targetable damage receiver" % drone_name)
	return drone


func _test_targeting_and_basic_attack(hero: HeroCharacter, friendly: TrainingDrone, enemy: TrainingDrone, far_enemy: TrainingDrone) -> void:
	var attack := hero.basic_attack
	_expect(attack != null and hero.targeting != null, "basic attack and targeting components are available")
	if attack == null or hero.targeting == null:
		return
	hero.stats.set_flat_modifier(&"phase8_test", &"critical_chance", -1.0)
	var nearest := hero.targeting.acquire_nearest(hero.get_attack_range())
	_expect(nearest == enemy, "targeting selects the nearest hostile and excludes a nearer friendly")
	_expect(not attack.try_attack(friendly), "BasicAttack rejects a direct friendly target")
	_expect(not attack.try_attack(far_enemy), "BasicAttack rejects a direct out-of-range target")
	_expect(is_zero_approx(attack.get_cooldown_ratio()), "invalid direct targets do not consume basic-attack cooldown")

	var spawned_projectiles: Array[Dictionary] = []
	var fired_events: Array[DamageEvent] = []
	var landed_events: Array[DamageEvent] = []
	var presentation_releases: Array[Dictionary] = []
	var damage_events: Array[DamageEvent] = []
	attack.projectile_spawned.connect(
		func(projectile: EnergyProjectile, target: Node3D, event: DamageEvent) -> void:
			spawned_projectiles.append({
				"target": target,
				"event": event,
				"socket_error": projectile.global_position.distance_to(hero.get_projectile_origin_position()),
			})
			_expect(target == enemy and event.attack_source == &"basic_attack", "spawned projectile preserves basic-attack target and payload")
	)
	attack.attack_fired.connect(func(_target: Node3D, event: DamageEvent) -> void: fired_events.append(event))
	attack.attack_landed.connect(func(_target: Node3D, event: DamageEvent) -> void: landed_events.append(event))
	hero.visual.semantic_event.connect(
		func(event_id: StringName, clip_name: StringName, time_s: float, socket: Vector3) -> void:
			if event_id == &"projectile_release" and clip_name == &"basic_attack":
				presentation_releases.append({"time_s": time_s, "socket": socket})
	)
	enemy.damage_receiver.damage_received.connect(func(event: DamageEvent, _amount: float) -> void: damage_events.append(event))
	var health_before := enemy.damage_receiver.health.current_health
	_expect(attack.try_attack(enemy), "valid hostile target starts authoritative basic-attack windup")
	await create_timer(1.25).timeout
	_expect(spawned_projectiles.size() == 1, "one authoritative projectile spawns after the windup")
	_expect(fired_events.size() == 1 and fired_events[0].attack_source == &"basic_attack", "attack_fired reports exactly one gameplay payload")
	var spawn_socket_error := float(spawned_projectiles[0].get("socket_error", INF)) if spawned_projectiles.size() == 1 else INF
	_expect(spawn_socket_error < 0.001, "authoritative projectile begins at the live imported socket_projectile")
	_expect(presentation_releases.size() == 1, "imported basic_attack release marker emits one presentation event")
	_expect(landed_events.size() == 1 and damage_events.size() == 1, "projectile resolves one Hurtbox/DamageReceiver hit")
	_expect(enemy.damage_receiver.health.current_health < health_before, "damage receiver reduces target health through the gameplay pipeline")
	_expect(friendly.damage_receiver.health.current_health == friendly.damage_receiver.health.max_health, "friendly remains undamaged by the hostile-only projectile")
	_expect(attack.can_attack() and hero.animation_driver.current_action.is_empty(), "basic attack recovers independently after its gameplay/visual timelines")

	await create_timer(hero.stats.get_attack_interval() + 0.12).timeout
	var cancelled_events: Array[bool] = []
	attack.attack_cancelled.connect(func() -> void: cancelled_events.append(true))
	var cancellation_target := await _spawn_drone("CancelledWindupDrone", Vector3(2.0, 0.0, -6.0), 2)
	if cancellation_target == null:
		return
	_expect(attack.try_attack(cancellation_target), "second valid target starts a cancellable windup")
	cancellation_target.remove_from_group("targetable")
	await physics_frame
	await create_timer(0.75).timeout
	_expect(cancelled_events.size() == 1, "target loss during windup cancels the pending basic attack")
	_expect(spawned_projectiles.size() == 1 and fired_events.size() == 1, "cancelled windup cannot spawn or report a stale projectile")
	cancellation_target.queue_free()


func _expect(condition: bool, message: String) -> void:
	if condition:
		print("PHASE8_BASIC_ATTACK_SMOKE PASS %s" % message)
		return
	_failed = true
	push_error("PHASE8_BASIC_ATTACK_SMOKE FAIL %s" % message)
