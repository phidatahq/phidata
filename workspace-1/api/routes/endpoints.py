from dataclasses import dataclass


@dataclass
class ApiEndpoints:
    PING: str = "/ping"
    HEALTH: str = "/health"
    ASSISTANTS: str = "/assistants"


endpoints = ApiEndpoints()
