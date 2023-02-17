import json
from typing import Dict
from datetime import datetime
import re

def zumper_apt_mapper(link, entity, details):
    if entity['amenity_tags'] != None and entity['building_amenity_tags'] != None:
        amenity_tags = set(entity['building_amenity_tags'] + entity['amenity_tags'])
    elif entity['amenity_tags'] != None:
        amenity_tags = entity['amenity_tags']
    elif entity['building_amenity_tags'] != None:
        amenity_tags = entity['building_amenity_tags']
    else:
        amenity_tags = None
    
    if amenity_tags != None:   
        num_tags = len(amenity_tags)
        amenity_tag_str = ", ".join(amenity_tags)
    else:
        amenity_tag_str = None
        num_tags = None

    area = details.get("sqf")
    area = area.replace(",", "")
    if area == "N/A":
        area = -1
    else:
        area = int(area.split()[0])
    new_entity = {
        'price' : int(entity['max_price']),
        'address': entity['address'],
        'name' : entity['address'],
        'beds' : int(entity['max_bedrooms']),
        'bathrooms' : int(entity['max_bathrooms']),
        'area' : area,
        'number_of_amenities': num_tags,
        'amenities': amenity_tag_str,
        'listed' : str(datetime.fromtimestamp(entity['listed_on'])),
        'min_lease': entity['max_lease_days'],
        'link': link,
        'townhouse': 1 if entity['property_type'] == 2 else 0,
        'house':  1 if entity['property_type'] == 13 else 0
    }
    # print(f'LOG: APT Entity -- {entity}')
    return new_entity

def zumper_building_mapper(link, entity, details) -> Dict:
    # print(f'LOG: Building Entity -- {entity}')
    if entity['amenity_tags'] != None and entity['building_amenity_tags'] != None:
        amenity_tags = set(entity['building_amenity_tags'] + entity['amenity_tags'])
    elif entity['building_amenity_tags'] != None:
        amenity_tags = entity['building_amenity_tags']
    elif entity['amenity_tags'] != None:
        amenity_tags = entity['amenity_tags']
    else:
        amenity_tags = None
        
    if amenity_tags != None:
        num_tags = len(amenity_tags)
        amenity_tag_str = ", ".join(amenity_tags)
    else:
        amenity_tag_str = None
        num_tags = None
    
    final = []
    u_c = 0
    for unit in details:
        # Formatting for use by Model
        price = unit.get("price")
        price = price.replace("$", "")
        price = price.replace(",", "")
        if "—" in price:
            range = price.split("—")
            price = (int(range[0]) + int(range[1])) // 2 
        price = int(price)
        
        beds = unit.get("beds")
        beds = int(beds.split()[0])
        
        bathrooms = unit.get("baths")
        if "–" in bathrooms:
            bathrooms = 0
        else:
            if "Half" in bathrooms:
                bathrooms = int(bathrooms.split()[0]) + 0.5
            else:
                bathrooms = int(bathrooms.split()[0])
            
        area = unit.get("sqf")
        if "—" in area:
            area = -1
        else:
            area = area.replace(",", "")
            area = int(area.split()[0])
    
        new_entity = {
            'price' : price,
            'address': entity["address"],
            'name' : f'{entity["building_name"]} | #{u_c}',
            'beds' : beds,
            'bathrooms' : bathrooms,
            'area' : area,
            'number_of_amenities': num_tags,
            'amenities': amenity_tag_str,
            'listed' : str(datetime.fromtimestamp(entity['listed_on'])),
            'min_lease': entity['max_lease_days'],
            'link': link,
            'townhouse': 1 if entity['property_type'] == 2 else 0,
            'house': 0
        }
        u_c += 1
        final.append(new_entity)
    
    return final
        
    