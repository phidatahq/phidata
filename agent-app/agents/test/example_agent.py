from agents.example import get_example_agent

example_agent = get_example_agent(debug_mode=True)

example_agent.print_response("What is simulation theory", stream=True)
