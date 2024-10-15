from assistant import get_world_builder, get_world_explorer, World  # type: ignore
from rich.pretty import pprint

model = "openhermes"
temperature = 0.1

world_builder = get_world_builder(model=model, temperature=temperature)
world: World = world_builder.run(  # type: ignore
    "A highly advanced futuristic city on a distant planet with a population of over 1 trillion."
)

pprint("============== World ==============")
pprint(world)
pprint("============== World ==============")

world_explorer = get_world_explorer(model=model, temperature=temperature, world=world, debug_mode=False)
world_explorer.cli_app(markdown=True)
