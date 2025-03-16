from math import radians, sin, cos, sqrt, atan2, degrees, acos
import requests
import polyline
import pandas as pd
import folium
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="geoapi")

def get_coordinates(address):
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": address,
        "key": "aedbf6e3ec284f75a00c1adaf622b1cf",
        "limit": 1
    }
    
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data["results"]:
            location = data["results"][0]["geometry"]
            return location["lat"], location["lng"]
    
    return None

def distance(coord1, coord2):
    R = 6371.0  
    lat1, lon1 = map(radians, coord1)
    lat2, lon2 = map(radians, coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def get_bearing(coord1, coord2):
    lat1, lon1 = radians(coord1[0]), radians(coord1[1])
    lat2, lon2 = radians(coord2[0]), radians(coord2[1])
    
    d_lon = lon2 - lon1
    x = sin(d_lon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(d_lon)
    
    return (atan2(x, y) * 180 / 3.141592653589793 + 360) % 360

def gcfa(address):
    location = geolocator.geocode(address)
    if location:
        return list((location.latitude, location.longitude))
    return None

def detect_painful_u_turns(coordinates):
    pain_points = []
    traveled_distances = [0]

    with open("debug_log.txt", "w") as log_file:
        log_file.write("U-Turn Detection Debug Log\n")
        log_file.write("=" * 50 + "\n")

        for i in range(1, len(coordinates)):
            traveled_distances.append(traveled_distances[-1] + distance(coordinates[i - 1], coordinates[i]))

        for i in range(len(coordinates) - 1):
            for j in range(i + 10, min(i + 100, len(coordinates))):  # Look ahead (skip small distances)
                travel_distance = traveled_distances[j] - traveled_distances[i]
                straight_distance = distance(coordinates[i], coordinates[j])

                log_entry = (f"Checking {i} -> {j}: Travel = {travel_distance:.2f}m, "
                             f"Straight = {straight_distance:.2f}m\n")
                log_file.write(log_entry)

                if travel_distance >= 4*straight_distance and straight_distance < 0.1 and travel_distance >= 1.25:
                    new_pain_point = {
                        'start_index': i,
                        'end_index': j,
                        'start_location': coordinates[i],
                        'end_location': coordinates[j],
                        'travel_distance': travel_distance,
                        'straight_distance': straight_distance
                    }

                    if pain_points and distance(pain_points[-1]['end_location'], new_pain_point['start_location']) < 0.5:
                        log_file.write(f"Merging pain points {pain_points[-1]['end_index']} -> {new_pain_point['start_index']}\n")
                        pain_points[-1]['end_index'] = new_pain_point['end_index']
                        pain_points[-1]['end_location'] = new_pain_point['end_location']
                    else:
                        pain_points.append(new_pain_point)

                    log_file.write(f"PAIN POINT DETECTED at {i} -> {j}\n")
                    log_file.write(f"Start: {coordinates[i]}, End: {coordinates[j]}\n")
                    log_file.write(f"Travel Distance: {travel_distance:.2f}m, Straight Distance: {straight_distance:.2f}m\n")
                    log_file.write("=" * 50 + "\n")

    print(pain_points)
    return pain_points



def getDifferences(coordinates):
    if not coordinates or len(coordinates) < 2:
        print("Insufficient coordinates provided.")
        return
    
    with open('polyline.txt', 'a') as file:
        print("Number of coordinates:", len(coordinates))
        totalDis = distance(coordinates[0], coordinates[-1])
        print("Distance:", totalDis)
        
        for i in range(1, len(coordinates)):
            rd = 0  # Reset relative distance for each starting point
            end = min(i + 100, len(coordinates))  # Ensure index does not go out of range
            
            for j in range(i, end):
                if i != j:
                    d = distance(coordinates[i], coordinates[j])
                    rd += distance(coordinates[j - 1], coordinates[j])
                    
                    if rd < d and d >= 0.3 * totalDis:
                        s = f"Points: {i}, {j}; rd: {rd}; d: {d}\n"
                        file.write(s)


def get_intermediate_junctions(source_address, dest_address):
    route_map = None
    total_distance = None
    pain_points = []


    source_coords = get_coordinates(source_address)
    dest_coords = get_coordinates(dest_address)

    if source_coords and dest_coords:
            start = f"{source_coords[1]},{source_coords[0]}"
            end = f"{dest_coords[1]},{dest_coords[0]}"
            
            url = f'http://router.project-osrm.org/route/v1/driving/{start};{end}?alternatives=false&overview=full'
            r = requests.get(url)

            if r.status_code == 200:
                routejson = r.json()
                total_distance = routejson['routes'][0]['distance'] / 1000 
                
                geometry = routejson['routes'][0]['geometry']
                coordinates = polyline.decode(geometry)

                pain_points = detect_painful_u_turns(coordinates) 

                max_pain_point = None
                if pain_points:
                    max_pain_point = max(pain_points, key=lambda x: x['travel_distance'] - x['straight_distance'])   

    if max_pain_point:
        return max_pain_point
    else:
        return None


if __name__ == "__main__" :
    print(main(source_address="Kengeri Upanagara Bus Stand, Bangalore", dest_address="Kengeri Bus Terminal"))