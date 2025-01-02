"""
Tool for searching business information using Google Maps API.
This required API key to be set in the environment variable `GOOGLE_MAPS_API_KEY`

You can get the API key here: https://console.cloud.google.com/projectselector2/google/maps-apis/credentials
"""
from os import getenv
from phi.tools import Toolkit
import googlemaps

_google_map_client = googlemaps.Client(key=getenv('GOOGLE_MAPS_API_KEY'))

class GoogleMapTools(Toolkit):
    def __init__(self):
        super().__init__(name="google_map")
        self.register(self.search_google_maps)

    def search_google_maps(self, query: str) -> str:
        """
        Search for businesses using Google Maps Places API.
        This tool takes a search query and returns detailed business information.
        
        Args:
            query (str): The query string to search for using Google Maps Search API. (e.g., "dental clinics in Noida")
            
        Returns:
            Stringified list of dictionaries containing business information like name, address, phone, website, rating, and reviews etc.
        """
        try:
            # Perform places search
            places_result = _google_map_client.places(query)
            
            if not places_result or 'results' not in places_result:
                return []
            
            businesses = []
            for place in places_result['results']:
                business = {
                    'name': place.get('name', ''),
                    'address': place.get('formatted_address', ''),
                    'rating': place.get('rating', 0.0),
                    'reviews': place.get('user_ratings_total', 0),
                    'place_id': place.get('place_id', ''),
                }
                
                # Get place details for additional information
                if place.get('place_id'):
                    details = _google_map_client.place(place['place_id'])
                    if details and 'result' in details:
                        result = details['result']
                        business.update({
                            'phone': result.get('formatted_phone_number', ''),
                            'website': result.get('website', ''),
                            'hours': result.get('opening_hours', {}).get('weekday_text', [])
                        })
                
                businesses.append(business)
            
            return str(businesses)
            
        except Exception as e:
            print(f"Error searching Google Maps: {str(e)}")
            return str([])
