from typing import List

from phi.tools import Toolkit
from phi.model.ollama import Ollama
from phi.agent import Agent
from phi.playground import Playground, serve_playground_app


class NavigationControls(Toolkit):
    def __init__(self):
        super().__init__(name="navigation_controls")

        self.register(self.set_destination)
        self.register(self.cancel_navigation)
        self.register(self.zoom_in)
        self.register(self.zoom_out)
        self.register(self.show_alternate_routes)
        self.register(self.set_route_preference)

    def set_destination(self, address: str) -> str:
        """
        Set the navigation destination.
        Args:
            address (str): The destination address or location.
        Returns:
            str: A confirmation message.
        """
        return f"I have set the destination to {address}."

    def cancel_navigation(self) -> str:
        """
        Cancel the current navigation.
        Returns:
            str: A confirmation message.
        """
        return "I have canceled the current navigation."

    def zoom_in(self) -> str:
        """
        Zoom in on the navigation map.
        Returns:
            str: A confirmation message.
        """
        return "I have zoomed in on the map."

    def zoom_out(self) -> str:
        """
        Zoom out on the navigation map.
        Returns:
            str: A confirmation message.
        """
        return "I have zoomed out on the map."

    def show_alternate_routes(self) -> str:
        """
        Display alternate route options to the current destination.
        Returns:
            str: A confirmation message.
        """
        return "I am displaying alternate route options."

    def set_route_preference(self, preference: str) -> str:
        """
        Set the route preference for navigation.
        Args:
            preference (str): The route preference (e.g., 'fastest', 'shortest', 'avoid highways').
        Returns:
            str: A confirmation message.
        """
        return f"I have set the route preference to {preference}."


class MediaControls(Toolkit):
    def __init__(self):
        super().__init__(name="media_controls")

        self.register(self.set_volume)
        self.register(self.change_station)
        self.register(self.next_track)
        self.register(self.previous_track)
        self.register(self.play)
        self.register(self.pause)
        self.register(self.select_source)

    def set_volume(self, level: int) -> str:
        """
        Set the audio system volume level.
        Args:
            level (int): The volume level to set (e.g., 0=muted, increasing levels from there).
        Returns:
            str: A confirmation message.
        """
        return f"I have set the volume to level {level}."

    def change_station(self, station: str) -> str:
        """
        Change the radio station.
        Args:
            station (str): The station identifier (e.g., a frequency like '101.5 FM').
        Returns:
            str: A confirmation message.
        """
        return f"I have changed the station to {station}."

    def next_track(self) -> str:
        """
        Move to the next track in the current playlist or media source.
        Returns:
            str: A confirmation message.
        """
        return "I have moved to the next track."

    def previous_track(self) -> str:
        """
        Move to the previous track in the current playlist or media source.
        Returns:
            str: A confirmation message.
        """
        return "I have moved to the previous track."

    def play(self) -> str:
        """
        Resume or start playback of the current media track.
        Returns:
            str: A confirmation message.
        """
        return "I have resumed playback."

    def pause(self) -> str:
        """
        Pause the current media playback.
        Returns:
            str: A confirmation message.
        """
        return "I have paused the playback."

    def select_source(self, source: str) -> str:
        """
        Change the audio input source.
        Args:
            source (str): The desired audio source (e.g., 'AM', 'FM', 'Bluetooth', 'USB').
        Returns:
            str: A confirmation message.
        """
        return f"I have changed the audio source to {source}."


class CabinControls(Toolkit):
    def __init__(self):
        super().__init__(name="cabin_controls")

        # Registering all the control functions
        self.register(self.set_temperature)
        self.register(self.set_seat_heating)
        self.register(self.open_sunroof)
        self.register(self.close_sunroof)
        self.register(self.tilt_sunroof)
        self.register(self.set_fan_speed)
        self.register(self.set_airflow_direction)
        self.register(self.turn_on_ac)
        self.register(self.turn_off_ac)
        self.register(self.set_interior_lighting)

        self.register(self.open_window)
        self.register(self.close_window)
        self.register(self.lock_doors)
        self.register(self.unlock_doors)
        self.register(self.adjust_side_mirror)

    def set_temperature(self, temperature: float) -> str:
        """Set the cabin temperature.
        Args:
            temperature (float): Desired cabin temperature in degrees Fahrenheit.
        Returns:
            str: Confirmation message.
        """
        return f"I have set the cabin temperature to {temperature}°F."

    def set_seat_heating(self, seat: str, level: int) -> str:
        """Set the seat heating level for a specific seat.
        Args:
            seat (str): The seat identifier (e.g. 'driver', 'passenger', 'rear_left').
            level (int): The heating level (0=off, 1=low, 2=medium, 3=high).
        Returns:
            str: Confirmation message.
        """
        return f"I have set {seat} seat heating to level {level}."

    def open_sunroof(self) -> str:
        """Open the sunroof.
        Returns:
            str: Confirmation message.
        """
        return "I have opened the sunroof."

    def close_sunroof(self) -> str:
        """Close the sunroof.
        Returns:
            str: Confirmation message.
        """
        return "I have closed the sunroof."

    def tilt_sunroof(self, angle: int) -> str:
        """Tilt the sunroof to a specified angle.
        Args:
            angle (int): The angle to tilt the sunroof (0-30 degrees).
        Returns:
            str: Confirmation message.
        """
        return f"I have tilted the sunroof to {angle} degrees."

    def set_fan_speed(self, speed: int) -> str:
        """Set the fan speed.
        Args:
            speed (int): Desired fan speed level (e.g. 0=off, 1=low, 2=medium, 3=high).
        Returns:
            str: Confirmation message.
        """
        return f"I have set the fan speed to level {speed}."

    def set_airflow_direction(self, direction: str) -> str:
        """Set the airflow direction.
        Args:
            direction (str): Desired airflow direction (e.g. 'feet', 'face', 'windshield').
        Returns:
            str: Confirmation message.
        """
        return f"I have set the airflow direction to {direction}."

    def turn_on_ac(self) -> str:
        """Turn on the air conditioning.
        Returns:
            str: Confirmation message.
        """
        return "I have turned on the air conditioning."

    def turn_off_ac(self) -> str:
        """Turn off the air conditioning.
        Returns:
            str: Confirmation message.
        """
        return "I have turned off the air conditioning."

    def set_interior_lighting(self, brightness_level: int) -> str:
        """Set the interior ambient lighting brightness level.
        Args:
            brightness_level (int): The brightness level (0=off, 1=dim, 2=medium, 3=bright).
        Returns:
            str: Confirmation message.
        """
        return f"I have set the interior lighting to brightness level {brightness_level}."

    def open_window(self, window: str) -> str:
        """
        Open a specified window.
        Args:
            window (str): The window identifier (e.g., 'driver', 'passenger', 'rear_left', 'rear_right').
        Returns:
            str: A confirmation message.
        """
        return f"I have opened the {window} window."

    def close_window(self, window: str) -> str:
        """
        Close a specified window.
        Args:
            window (str): The window identifier.
        Returns:
            str: A confirmation message.
        """
        return f"I have closed the {window} window."

    def lock_doors(self) -> str:
        """
        Lock all the doors.
        Returns:
            str: A confirmation message.
        """
        return "I have locked all the doors."

    def unlock_doors(self) -> str:
        """
        Unlock all the doors.
        Returns:
            str: A confirmation message.
        """
        return "I have unlocked all the doors."

    def adjust_side_mirror(self, mirror: str, angle: int) -> str:
        """
        Adjust a side mirror to a specified angle.
        Args:
            mirror (str): Which mirror to adjust (e.g., 'driver', 'passenger').
            angle (int): The angle to set the mirror to (in degrees).
        Returns:
            str: A confirmation message.
        """
        return f"I have adjusted the {mirror} side mirror to an angle of {angle} degrees."


instructions: List[str] = [
    "You have the ability to control various car features using predefined toolkits and their functions.",
    "There are three categories of controls available:",
    "1. CabinControls: Manage temperature, seat heating, sunroof (open/close/tilt), fan speed, airflow direction, AC (on/off), interior lighting, windows (open/close), door locks (lock/unlock), and side mirrors (adjust).",
    "2. MediaControls: Adjust volume, change stations, navigate tracks (next/previous), play/pause, and select audio sources.",
    "3. NavigationControls: Set a navigation destination, cancel navigation, zoom in/out on the map, show alternate routes, and set route preferences.",
    "When the user makes a request, carefully determine which toolkit and function to use.",
    "If the user's request is unclear or ambiguous, ask clarifying questions before proceeding.",
    "Some functions require no arguments (e.g., 'zoom_in' or 'play'), while others need specific values (e.g., temperature in degrees, fan speed level, station name, address).",
    "Always return a confirmation message after executing the function.",
]

agent = Agent(
    # model=Ollama(id="llama3.2:latest"),
    model=Ollama(id="qwen2.5:latest"),
    instructions=instructions,
    tools=[CabinControls(), MediaControls(), NavigationControls()],
    show_tool_calls=True,
    markdown=True,
)
# agent.cli_app()

app = Playground(agents=[agent]).get_app()

if __name__ == "__main__":
    serve_playground_app("qualcomm_ollama:app", reload=True)
