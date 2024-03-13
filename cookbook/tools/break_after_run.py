"""
This example demonstrates how to stop execution after a function call.

This is useful when you want to run a tool but don't want to send the response back to OpenAI.
For example when you want to run a tool that prints a message to the console and then stops execution.
"""

import httpx

from phi.assistant import Assistant
from phi.tools import Function


def print_a_dog_fact() -> str:
    """Get a random dog fact.

    Returns:
        str: A random dog fact.
    """

    try:
        dog_facts = httpx.get("https://dog-api.kinduff.com/api/facts").json()
        print(dog_facts.get("facts")[0])
        return dog_facts.get("facts")[0]
    except Exception:
        return "No dog facts found, try again later."


# This run with print 3 dog facts and then stop execution.
# NOTE: it will not print the final message from OpenAI because the function call result was not sent back to OpenAI.
print("*************************************")
a1 = Assistant(tools=[Function.build(print_a_dog_fact, break_after_run=True)])
a1_response = a1.run("Share 3 dog facts.", stream=False)
# The response is empty because the function call result was not sent back to OpenAI.
# So there is no response from the assistant.
print(a1_response)

# Stream the response to see the function call result.
a1_response_generator = a1.run("Share 3 dog facts.")
# This will also not print the final message from OpenAI because the function call result was not sent back to OpenAI.
for message in a1_response_generator:
    print(message)
print("*************************************")

# Now try the same thing but with the function call sent back to OpenAI.
print("*************************************")
a2 = Assistant(tools=[print_a_dog_fact])
a2_response = a2.run("Share 3 dog facts.", stream=False)
# The response is the final message from OpenAI because the function call result was sent back to OpenAI.
print(a2_response)
print("*************************************")
