# main.py

from flask import Flask, jsonify, request
from flask_cors import CORS  # Add this import
from datetime import datetime, timedelta
from dummyDB import DummyDB
from route_finder import RouteFinder
from llm_service import LLMService

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
llm_service = LLMService()

db = DummyDB()
route_finder = RouteFinder()

@app.route("/trains", methods=["GET"])
def trains():
    """Handle train search requests with various input combinations"""
    try:
        source = request.args.get("source")
        destination = request.args.get("destination")
        travel_date = request.args.get("travel_date")
        include_alternative_routes = request.args.get("alternative_routes", "false").lower() == "true"
        max_transfers = int(request.args.get("max_transfers", "2"))
        max_wait_time = int(request.args.get("max_wait_time", "120"))
        include_overnight = request.args.get("include_overnight", "true").lower() == "true"
        check_nearby = request.args.get("check_nearby", "false").lower() == "true"
        priority = request.args.get("priority", "Speed")

        if not source:
            return jsonify({
                "status": "error",
                "message": "Source station is required"
            }), 400

        # Parse travel date if provided
        if travel_date:
            try:
                travel_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": "Invalid date format. Use YYYY-MM-DD"
                }), 400

        # Handle only source provided case
        if not destination:
            trains = db.get_trains(source)
            destinations = {}
            for train in trains:
                if train["destination"] not in destinations:
                    destinations[train["destination"]] = []
                destinations[train["destination"]].append(train)
            return jsonify({
                "status": "success",
                "data": destinations
            })

        # Search with source and destination
        all_trains = db.get_all_trains()
        routes = route_finder.find_routes(
            all_trains,
            source,
            destination,
            max_transfers=max_transfers,
            max_wait_time=max_wait_time,
            include_overnight=include_overnight,
            travel_date=travel_date
        )

        # Check nearby stations if requested
        nearby_routes = []
        if check_nearby and (not routes or len(routes.get("direct_routes", [])) == 0):
            nearby_stations = db.get_nearby_stations(source)
            for station in nearby_stations:
                station_routes = route_finder.find_routes(
                    all_trains,
                    station["name"],
                    destination,
                    max_transfers=max_transfers,
                    max_wait_time=max_wait_time,
                    include_overnight=include_overnight,
                    travel_date=travel_date
                )
                if station_routes:
                    for route in station_routes.get("direct_routes", []) + station_routes.get("alternative_routes", []):
                        route["from_nearby"] = True
                        route["distance_to_source"] = station["distance"]
                        nearby_routes.append(route)

        # Sort routes based on priority
        all_routes = routes.get("direct_routes", []) + routes.get("alternative_routes", []) + nearby_routes
        if priority == "Speed":
            all_routes.sort(key=lambda x: x["total_duration_minutes"])
        elif priority == "Cost":
            all_routes.sort(key=lambda x: sum(leg["cost"] for leg in x["legs"]))
        elif priority == "Comfort":
            all_routes.sort(key=lambda x: (-sum(leg["seats_available"] for leg in x["legs"]) / len(x["legs"])))

        result = {
            "status": "success",
            "data": {
                "direct_routes": [r for r in all_routes if r.get("number_of_transfers", 0) == 0 and not r.get("from_nearby", False)],
                "alternative_routes": [r for r in all_routes if r.get("number_of_transfers", 0) > 0 and not r.get("from_nearby", False)],
                "nearby_station_routes": [r for r in all_routes if r.get("from_nearby", False)]
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/availability", methods=["GET"])
def check_availability():
    """Check seat availability for specific trains"""
    try:
        train_id = request.args.get("train_id")
        travel_date = request.args.get("travel_date")

        if not (train_id and travel_date):
            return jsonify({
                "status": "error",
                "message": "Train ID and travel date are required"
            }), 400

        try:
            travel_date = datetime.strptime(travel_date, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({
                "status": "error",
                "message": "Invalid date format. Use YYYY-MM-DD"
            }), 400

        availability = db.check_seat_availability(train_id, travel_date)
        return jsonify({
            "status": "success",
            "data": availability
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/recommend", methods=["POST"])
def get_recommendation():
    """Get LLM recommendations for travel routes"""
    try:
        data = request.json
        if not data or not data.get("query") or not data.get("context"):
            return jsonify({
                "status": "error",
                "message": "Query and context are required"
            }), 400

        recommendation = llm_service.get_recommendation(
            data["query"],
            data["context"]
        )

        return jsonify({
            "status": "success",
            "data": {
                "recommendation": recommendation
            }
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Update your existing /search route to use the LLM service
@app.route("/search", methods=["POST"])
def search_trains():
    """Process both natural language and form-based queries"""
    try:
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        input_type = data.get("input_type")
        
        if input_type == "natural_language":
            query = data.get("query")
            if not query:
                return jsonify({
                    "status": "error",
                    "message": "Query is required for natural language search"
                }), 400
                
            parsed_details = llm_service.process_natural_language(query)
            if "error" in parsed_details:
                return jsonify({
                    "status": "error",
                    "message": parsed_details["error"]
                }), 400
                
            return jsonify({
                "status": "success",
                "data": parsed_details
            })
        else:
            # Rest of the form handling code remains the same
            pass

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/nearby-stations", methods=["GET"])
def get_nearby_stations():
    """Get nearby stations for a given station"""
    try:
        station = request.args.get("station")
        if not station:
            return jsonify({
                "status": "error",
                "message": "Station name is required"
            }), 400
            
        nearby = db.get_nearby_stations(station)
        return jsonify({
            "status": "success",
            "data": nearby
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

if __name__ == "__main__":
    app.run(port=5000, debug=True)