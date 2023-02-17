from datetime import datetime
from json import JSONDecodeError, dumps, dump
import json
import re
from time import sleep
from typing import Dict, List
from logger import Logger
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType

from zumper_mapper import zumper_building_mapper, zumper_apt_mapper
from geotools import GeoTools
from dotenv import load_dotenv
import os
import time

load_dotenv()

API_KEY = os.getenv("MAPS_API_KEY")
z_logger = Logger('ZUMPER_LOG')

class Zumper_Links:
    USER_AGENT_LIST = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    ]
     
    def __init__(self):
        self.base_url = "https://www.zumper.com" 
        self.s = requests.Session()
        self.apts = []
        self.headers = {
            'Connection': 'keep-alive',
            'sec-ch-ua': '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
            'X-CSRFToken': 'AIlkht9j5VbVkzwipewsNdJHdWuwx53JlQuLeFo7QwxIaxE3Soqv1JASdMgjXvyx38LpeDmrK8AaA0iA',
            'X-Zumper-XZ-Token': None,
            'sec-ch-ua-mobile': '?0',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
            'sec-ch-ua-platform': '"macOS"',
            'Accept': '*/*',
            'Origin': 'https://www.zumper.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.zumper.com/',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

        self.neighborhoods = []
        
        options = Options()
        options.headless = True
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        self.agent_idx = 0
        
    def rotate_agent(self):
        if self.agent_idx == len(Zumper_Links.USER_AGENT_LIST) - 1:
            self.agent_idx = 0
        else:
            self.agent_idx += 1
        
        self.headers['User-Agent'] = Zumper_Links.USER_AGENT_LIST[self.agent_idx]

          
    def close(self) -> None:
        """[summary]
        """
        self.driver.quit()

    def get_neighborhoods(self, min_lng, min_lat, max_lng, max_lat):
        
        # print(max_lat)
        neighborhood_res = self.s.get(f'{self.base_url}/api/t/1/hoods/?hoodType=1&maxLat={max_lat}&maxLng={max_lng}&minLat={min_lat}&minLng={min_lng}', headers=self.headers)
        # print(neighborhood_res.json())
        
        self.neighborhoods = [n["name"] for n in neighborhood_res.json()]
        
        return self.neighborhoods

    def get_listables(self, box, nearby=15, page=1, long_term=True, monthly=False, vacation=False):
        data = {"external":True, "longTerm": long_term, "maxLat":box[3], "maxLng":box[2], "minLat":box[1], "minLng":box[0], "minPrice":0, "monthly": monthly, "transits":{}, "vacation": vacation, "limit":24, "matching":True, "nearby": nearby, "notFeatures":[], "descriptionLength":580, "page" : page}
        time.sleep(1)
        res = self.s.post('https://www.zumper.com/api/t/1/pages/listables', data=dumps(data), headers=self.headers)
        try: 
            return res.json()['listables'], res.json()['matching']
        except JSONDecodeError as e:
            z_logger.log_f(f'status: {res.status_code} || text: {res.content} || enc: {res.encoding}', level='ERROR')
            if res.status_code == 429:
                z_logger.log_f('RATE LIMIT...RESTING')
                time.sleep(60)
            return None, None

    def scrape(self, city : str, state : str) -> pd.DataFrame:
        """[summary]

        Args:
            city (str): [description]
            state (str): [description]
        """
        self._update_xz_token(city, state)
        box = self._get_lat_long_box(city , state)
    
        page_num = 1
        count = None
        fetched_properties = 0
        p_df = pd.read_csv(f"../rental_properties_{city.lower()}.csv")
        while True:
            print(f'LOG: neighborhoods -- PAGE: {page_num}, COUNT: {count}')
            
            #Get first page of apartments
            # data = {"external":True, "longTerm":True, "maxLat":box[3], "maxLng":box[2], "minLat":box[1], "minLng":box[0], "minPrice":0, "monthly":False, "transits":{}, "vacation":False, "limit":100, "matching":True, "nearby":15, "notFeatures":[], "descriptionLength":580, "page" : page_num}
            # res = self.s.post('https://www.zumper.com/api/t/1/pages/listables', data=dumps(data), headers=self.headers)
            entity_list, matching = self.get_listables(box, 5, page_num, True, False, False)
            if entity_list is None:
                self.s = requests.Session()
                time.sleep(7)
                self.rotate_agent()
                self._update_xz_token(city, state)
                box = self._get_lat_long_box(city , state)
                entity_list, matching = self.get_listables(box, 5, page_num, True, False, False)
            z_logger.log_f(f'GETTING LISTABLES: REMAINING={matching}, FETCHED FROM PAGE: {len(entity_list)}, PAGE: {page_num}, PAGE_COUNT: {count}')
            
            # Format for csv usage
            for entity in entity_list:
                link = self.base_url + entity.get("url")
                found = link in set(p_df['link'])
                if found:
                    z_logger.log_f(f"Skipping {link}. Already Scraped.")
                    continue
                
                if 'apartment-building' in link:
                    time.sleep(0.5)
                    details = self._get_building_details(link)
                    units = zumper_building_mapper(link, entity, details)
                    u_c = 1
                    for unit in units:

                        unit['address'] = f'{unit["address"]}, {city}, {state}'
                        self.apts.append(unit)
                        z_logger.log_f(f'Address: {unit["address"]} -- {u_c} | PAGE_NUM: {page_num}/{count} | FETCHED PROPERTIES: {fetched_properties}', 'ZUMPER')
                        u_c += 1
                        fetched_properties += 1
                        
                elif 'apartments-for-rent' in link:
                    # time.sleep(0.5)
                    details = self._get_apartment_details(link)
                    new_entity = zumper_apt_mapper(link, entity, details)
                    new_entity['address'] = f'{new_entity["address"]}, {city}, {state}'
                    self.apts.append(new_entity)
                    z_logger.log_f(f'Address: {new_entity["address"]} | PAGE_NUM: {page_num}/{count} | FETCHED PROPERTIES: {fetched_properties}', 'ZUMPER')
                    fetched_properties += 1

                    
            # Get num pages
            if count == None:
                try:
                    count = matching // 24
                except:
                    pass
            
            page_num += 1
            
            if page_num > count:
                break 
            
        self.close()
        
        g = GeoTools(API_KEY)
        df = pd.DataFrame(self.apts)
        
        df[['neighborhood', 'lat', 'lng', 'rad', 'angle']] = df.apply(lambda r: g.get_suburb_and_coords(r['address']), axis=1, result_type='expand')

        pd.concat([df, p_df]).drop_duplicates(subset=['price','address','name','beds','bathrooms','area']).reset_index(drop=True)

        df.to_csv(f"../rental_properties_{city.lower()}.csv", index=False)
        return df     
    
    def _get_building_details(self, link) -> List[Dict]:    
        """[summary]

        Args:
            link ([type]): [description]

        Returns:
            List[Dict]: [description]
        """
        self.driver.get(link)
        self.driver.execute_script("window.scrollTo(0, 1300)")
        sleep(1)
        content = self.driver.page_source
        soup = BeautifulSoup(content, features="lxml")
        raw_bed_options = soup.find_all('div', attrs = {'class' : 'css-1mxhdum'})
        raw_num_floorplans = soup.find_all('div', attrs = {'class' : 'css-1s09v6y'})
        
        total_options = []
        x = 0
        for nb, np in zip(raw_bed_options, raw_num_floorplans):
            try:
                num = int(nb.text.split()[0])
            except:
                num = 0
                
            try:
                x += int(np.text.split()[0])
            except:
                pass

            total_options.append((num , x))
        # print(f'Total Options: {total_options}')
            
        
        raw_baths = soup.find_all('div', attrs = {'class' : 'css-1ukfvem'})
        raw_sqf = soup.find_all('div', attrs = {'class' : 'css-13koqug'})
        raw_price = soup.find_all('div', attrs = {'class' : 'css-11mm0h3'})

        building_details = []
        apartment_num = 1
        for bath, area, cost in zip(raw_baths, raw_sqf, raw_price):
            num_beds = "-1"
            for key, value in total_options:
                if apartment_num <= value:
                    num_beds = f"{key} Beds"
                    break
            building_details.append({
                    'beds': num_beds,
                    'baths': bath.text.replace("Bath Icon", ""),
                    'sqf': area.text.replace("Sqft Icon", ""),
                    'price': cost.text
            })
            apartment_num += 1
        z_logger.log_f(f'BUILDING LINK: {link}')
        return building_details

    
    def _get_apartment_details(self, link) -> Dict:
        """[summary]

        Args:
            link ([type]): [description]

        Returns:
            Dict: [description]
        """
        self.driver.get(link)
        content = self.driver.page_source
        soup = BeautifulSoup(content, features="lxml")
        raw = soup.find_all('div', attrs={'class': re.compile(r'SummaryIcon_summaryText')})

    
        details = {
            'sqf' : [x.text for x in raw if 'ft' in x.text],
            'listed' : [x.text for x in raw if 'Hours' in x.text or 'Days' in x.text or 'Ago' in x.text]
        }

        z_logger.log_f(f'SQFT: {details["sqf"]}| Summary Items: {raw}')

        # print(f'LOG: APT Details -- {details}')
        
        for key, value in details.items():
            if value == []:
                details.update({key:"N/A"})
            else:
                details.update({key:value[0]})
        
        # print(f'LOG: APT Details -- {details}')


        return details
        

    def _update_xz_token(self, city: str, state: str):
        """[summary]

        Raises:
            ValueError: [description]
        """
        res = self.s.get(f'https://www.zumper.com/api/t/1/pages/cities/{city.lower()}-{state.lower()}', headers=self.headers)
        if res.status_code != 200:
            try:
                print(f'RES {res.status_code} - {res.content}')
                new_token = res.json()['xz_token']
                self.headers.update({'X-Zumper-XZ-Token': new_token})
                print('Successfully set new xz_token.')
            except:
                raise ValueError
            
    
    def _get_lat_long_box(self, city : str, state : str):
        """[summary]

        Args:
            city (str): [description]
            state (str): [description]

        Returns:
            [type]: [description]
        """
        res = self.s.get(f'https://www.zumper.com/api/t/1/pages/cities/{city.lower()}-{state.lower()}', headers=self.headers)
        print(res.json())
        print(res.headers)
        with open(f'../{city.lower()}-coords.json', "w+") as FILE:
            dump(res.json()['box'], FILE)
        # print(res.json()['box'])
        return res.json()['box']
    

if __name__ == "__main__":
    print("start")
    a = Zumper_Links()
    print(a.scrape("vancouver", "bc"))
    print("finish")