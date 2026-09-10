class_name InputSource
extends Node
## Contract for player, AI, replay, and network command producers.


func get_command(_character: HeroCharacter) -> CharacterCommand:
	return CharacterCommand.new()
