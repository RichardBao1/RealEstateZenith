from math import sqrt, tanh, cos
import googlemaps
import os

class GeoTools:

    def __init__(self, api_key):
        self.gmaps = googlemaps.Client(key=api_key)

    def get_suburb_and_coords(self, address):
        print(f'ADDRESS: {address}')
        geo = self.gmaps.geocode(address)
        # print(geo)
        components = list(filter(lambda a: 'address_components' in a.keys(), geo))[0]['address_components']
        # print(components)

        try:
            suburb = list(filter(lambda e: 'neighborhood' in e['types'], components))[0]['long_name']
            lat = list(filter(lambda a: 'geometry' in a.keys(), geo))[0]['geometry']['location']['lat']
            lng = list(filter(lambda a: 'geometry' in a.keys(), geo))[0]['geometry']['location']['lng']
            
            rad = sqrt(lat**2 + lng**2)
            angle = tanh(lng / lat)
            
            print(f'{suburb}, {lat}, {lng}, {rad}, {angle}')
            return suburb.lower(), lat, lng, rad, angle
        except IndexError:
            print(f'NA {address}')
            return "NA", -1, -1, -1, -1

def get_airdna_city_id(city: str):
    return 60

def get_polar_centroid(lat_lng_box: list):
    """
        box: [lngMin, latMin, lngMax, latMax]
    """
    lat_avg = (lat_lng_box[1] + lat_lng_box[3]) / 2
    lng_avg = (lat_lng_box[0] + lat_lng_box[2]) / 2

    rad = sqrt(lat_avg**2 + lng_avg**2)
    angle = tanh(lng_avg / lat_avg)
    return rad, angle

def polar_from_centroid(centroid, coord):
    angle = coord[1] - centroid[1]
    d = sqrt((coord[0]**2 + centroid[0]**2) - ((2*coord[0]*centroid[0])*cos(angle)))

    return d, angle
