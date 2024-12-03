from phi.agent import Agent
from phi.tools.apicaller import ApiCaller

# Use any OpenAPI spec file
OPENAPI_SPEC = 'https://petstore3.swagger.io/api/v3/openapi.json'
# Generate swagger client and copy the client package to the current directory
CLIENT_PACKAGE = 'swagger_client'
agent = Agent(tools=[ApiCaller(CLIENT_PACKAGE, OPENAPI_SPEC,
                               generate_swagger=True,
                               configuration={'host': 'https://petstore3.swagger.io/api/v3'})], show_tool_calls=True)
agent.print_response("Get pet id 1", markdown=True)

# # Use any OpenAPI spec file
# OPENAPI_SPEC = 'https://raw.githubusercontent.com/sonallux/spotify-web-api/refs/heads/main/official-spotify-open-api.yml'
# # Generate swagger client and copy the client package to the current directory
# CLIENT_PACKAGE = 'swagger_client'
#
# agent = Agent(tools=[ApiCaller(CLIENT_PACKAGE, OPENAPI_SPEC, path='spotify_swagger')], show_tool_calls=True, debug_mode=True)
# agent.print_response("make me a playlist with the first song from kind of blue. call it machine blues.", markdown=True)
