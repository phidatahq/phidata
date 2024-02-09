from assistant import get_world_builder  # type: ignore
from rich.pretty import pprint


world_builder = get_world_builder(model="openhermes", temperature=0.1, debug_mode=False)
world = world_builder.run("A highly advanced futuristic city on a distant planet with a population of over 1 trillion.")

pprint(world)
