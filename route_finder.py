from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Route:
    legs: List[Dict]
    total_duration: int
    total_wait_time: int
    transfers: int
    total_cost: float
    average_popularity: float

class RouteFinder:
    def __init__(self):
        self.max_search_depth = 5

    def calculate_duration(self, departure: str, arrival: str) -> int:
        """Calculate duration in minutes between departure and arrival times"""
        dep = datetime.strptime(departure, "%H:%M")
        arr = datetime.strptime(arrival, "%H:%M")
        duration = arr - dep
        if duration.days < 0:
            duration += timedelta(days=1)
        return int(duration.total_seconds() / 60)

    def calculate_wait_time(self, arrival: str, next_departure: str) -> int:
        """Calculate waiting time in minutes between arrival and next departure"""
        arr = datetime.strptime(arrival, "%H:%M")
        dep = datetime.strptime(next_departure, "%H:%M")
        wait = dep - arr
        if wait.days < 0:
            wait += timedelta(days=1)
        return int(wait.total_seconds() / 60)

    def is_valid_transfer(self, arrival_time: str, departure_time: str, max_wait_time: int, include_overnight: bool) -> bool:
        """Check if a transfer is valid based on wait time and overnight settings"""
        wait_time = self.calculate_wait_time(arrival_time, departure_time)
        if not include_overnight and wait_time > 720:  # 12 hours
            return False
        return wait_time >= 30 and wait_time <= max_wait_time

    def find_routes(self, trains: List[Dict], source: str, destination: str, 
                   max_transfers: int = 2, max_wait_time: int = 120,
                   include_overnight: bool = True, travel_date: Optional[datetime] = None) -> Dict:
        """Find all possible routes between source and destination with given constraints"""
        direct_routes = []
        alternative_routes = []

        # Find direct routes
        direct_trains = [
            train for train in trains 
            if train["source"] == source and train["destination"] == destination
        ]
        
        for train in direct_trains:
            if travel_date and travel_date.strftime("%a") not in train["days_available"]:
                continue
                
            duration = self.calculate_duration(train["departure_time"], train["arrival_time"])
            route = Route(
                legs=[train],
                total_duration=duration,
                total_wait_time=0,
                transfers=0,
                total_cost=train["cost"],
                average_popularity=train["popularity"]
            )
            direct_routes.append(self.format_route_details(route))

        def find_connecting_routes(current_station: str, target: str, visited: set, 
                                current_route: List[Dict], transfers: int,
                                current_time: str, total_wait_time: int):
            """Recursive function to find connecting routes"""
            if transfers > max_transfers or len(visited) > self.max_search_depth:
                return

            possible_next_legs = [
                train for train in trains 
                if train["source"] == current_station 
                and train["source"] not in visited
                and (not travel_date or travel_date.strftime("%a") in train["days_available"])
            ]

            for next_leg in possible_next_legs:
                if len(current_route) > 0:
                    if not self.is_valid_transfer(
                        current_route[-1]["arrival_time"],
                        next_leg["departure_time"],
                        max_wait_time,
                        include_overnight
                    ):
                        continue

                    wait_time = self.calculate_wait_time(
                        current_route[-1]["arrival_time"],
                        next_leg["departure_time"]
                    )
                else:
                    wait_time = 0

                if next_leg["destination"] == target:
                    total_duration = sum(
                        self.calculate_duration(leg["departure_time"], leg["arrival_time"])
                        for leg in current_route + [next_leg]
                    ) + total_wait_time + wait_time

                    total_cost = sum(leg["cost"] for leg in current_route + [next_leg])
                    avg_popularity = sum(leg["popularity"] for leg in current_route + [next_leg]) / (len(current_route) + 1)

                    route = Route(
                        legs=current_route + [next_leg],
                        total_duration=total_duration,
                        total_wait_time=total_wait_time + wait_time,
                        transfers=len(current_route),
                        total_cost=total_cost,
                        average_popularity=avg_popularity
                    )
                    alternative_routes.append(self.format_route_details(route))
                else:
                    new_visited = visited | {next_leg["source"]}
                    find_connecting_routes(
                        next_leg["destination"],
                        target,
                        new_visited,
                        current_route + [next_leg],
                        transfers + 1,
                        next_leg["arrival_time"],
                        total_wait_time + wait_time
                    )

        # Find alternative routes if needed
        if len(direct_routes) == 0 or max_transfers > 0:
            find_connecting_routes(source, destination, {source}, [], 0, "", 0)

        return {
            "direct_routes": direct_routes,
            "alternative_routes": alternative_routes
        }

    def format_route_details(self, route: Route) -> Dict:
        """Format route details for API response"""
        legs = []
        for i, leg in enumerate(route.legs):
            leg_info = {
                "train_id": leg["train_id"],
                "train_name": leg["train_name"],
                "source": leg["source"],
                "destination": leg["destination"],
                "departure_time": leg["departure_time"],
                "arrival_time": leg["arrival_time"],
                "seats_available": leg["seats_available"],
                "cost": leg["cost"],
                "popularity": leg["popularity"],
                "platform": leg.get("platform", "TBD")
            }

            if i > 0:
                wait_time = self.calculate_wait_time(
                    route.legs[i-1]["arrival_time"],
                    leg["departure_time"]
                )
                leg_info["wait_time_at_source"] = wait_time
                leg_info["transfer_instructions"] = self.generate_transfer_instructions(
                    route.legs[i-1],
                    leg
                )

            legs.append(leg_info)

        return {
            "legs": legs,
            "total_duration_minutes": route.total_duration,
            "total_wait_time_minutes": route.total_wait_time,
            "number_of_transfers": route.transfers,
            "total_cost": route.total_cost,
            "average_popularity": route.average_popularity
        }

    def generate_transfer_instructions(self, prev_leg: Dict, next_leg: Dict) -> str:
        """Generate transfer instructions between two legs"""
        return (
            f"Exit at platform {prev_leg.get('platform', 'TBD')} of {prev_leg['destination']}. "
            f"Transfer to platform {next_leg.get('platform', 'TBD')} for {next_leg['train_name']}."
        )

    def parse_natural_language(self, query: str) -> Dict:
        """Parse natural language query to extract travel details"""
        # This is a placeholder for NLP implementation
        # In a real implementation, you would use an NLP model or service
        parsed = {
            "source": None,
            "destination": None,
            "travel_date": None,
            "preferences": {
                "priority": "Speed",
                "max_transfers": 2,
                "include_overnight": True
            }
        }
        
        # Add actual NLP logic here
        return parsed

def format_duration(minutes: int) -> str:
    """Format duration from minutes to hours and minutes"""
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"