from datetime import datetime, timedelta

# Expanded dummy train data with more interconnected routes and additional fields
trains = [
    # [Previous train data remains the same]
    # Additional fields for each train:
    {
        "train_id": "DEL-MUM-01",
        "train_name": "Delhi Mumbai Express",
        "source": "Delhi",
        "destination": "Mumbai",
        "departure_time": "08:00",
        "arrival_time": "20:00",
        "days_available": ["Mon", "Wed", "Fri"],
        "seats_available": 50,
        "popularity": 0.8,
        "cost": 1200,
        "class_types": ["1A", "2A", "3A"],
        "platform": "1",
        "duration_minutes": 720
    },
    # Add similar fields for all other trains...
]

NEARBY_STATIONS = {
    "Mumbai": [
        {"name": "Thane", "distance": 21, "connectivity_score": 0.9},
        {"name": "Kalyan", "distance": 54, "connectivity_score": 0.8}
    ],
    "Delhi": [
        {"name": "Ghaziabad", "distance": 28, "connectivity_score": 0.85},
        {"name": "Noida", "distance": 25, "connectivity_score": 0.75}
    ],
    # Add similar details for other cities...
}

class DummyDB:
    @staticmethod
    def get_trains(source, destination=None, travel_date=None):
        """Fetch trains by source and optional destination with date filtering"""
        filtered_trains = []
        
        for train in trains:
            if train["source"] == source:
                if destination is None or train["destination"] == destination:
                    if travel_date:
                        day_of_week = travel_date.strftime("%a")
                        if day_of_week in train["days_available"]:
                            filtered_trains.append(train)
                    else:
                        filtered_trains.append(train)
        
        return filtered_trains

    @staticmethod
    def get_all_trains():
        """Fetch all trains"""
        return trains

    @staticmethod
    def get_nearby_stations(station):
        """Get nearby stations with detailed information"""
        return NEARBY_STATIONS.get(station, [])

    @staticmethod
    def check_seat_availability(train_id, travel_date):
        """Check seat availability for a specific train and date"""
        for train in trains:
            if train["train_id"] == train_id:
                # Simulate varying availability based on travel date
                base_seats = train["seats_available"]
                date_diff = (travel_date - datetime.now().date()).days
                
                # Reduce availability for dates closer to departure
                adjusted_seats = max(0, base_seats - (30 - min(date_diff, 30)))
                
                return {
                    "train_id": train_id,
                    "available_seats": adjusted_seats,
                    "class_types": train["class_types"]
                }
        
        return None  # Train not found