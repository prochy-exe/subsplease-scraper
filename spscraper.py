import requests, copy, re, json, os, alfetcher
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

missing_ids = []
yanked_entries = []

def get_all_anime():

    # URL of the webpage
    url = "https://subsplease.org/shows"
    base = "https://subsplease.org"
    # Send a GET request to the URL
    response = requests.get(url)
    items_dict = {}


    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content
        html_content = response.text
        
        # Create a BeautifulSoup object
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all elements with class 'all-shows-link' and get their 'title' attribute
        all_shows_links = soup.find_all(class_='all-shows-link')

        for link in all_shows_links:
            anime_title = link.a['title']
            listing_url = base + link.a['href']
            if anime_title not in skip_list: 
                anime_info = get_data(listing_url)
                if not anime_info:
                    continue
                # Set the proper dictionary entry
                try:
                    dict_entry = anime_info[anime_title]
                except:
                    for entry in anime_info:
                        anime_title = entry
                        dict_entry = anime_info[anime_title]
                items_dict[anime_title] = dict_entry
    else:
        print("Failed to retrieve webpage. Status code:", response.status_code)
    return items_dict

def get_data(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content
        html_content = response.text
        
        # Create a BeautifulSoup object
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all elements with class 'all-shows-link' and get their 'title' attribute
        table_element  = soup.find('table', id='show-release-table')
        sid_value = table_element.get('sid')
        title = soup.find('h1', class_='entry-title').text
        title = re.sub('–', '-', title)
        title = re.sub('’', "'", title)

        item = {}
        item[title] = {}
        item[title]['url'] = url
        item[title]['id'] = sid_value
        torrent_links = get_torrent_links(item[title]['id'])
        item[title]['batches'] = torrent_links[0]
        item[title]['episodes'] = torrent_links[1]
        
        return item
    else:
        print("Failed to retrieve webpage. Status code:", response.status_code)

def get_torrent_links(sub_id):

    def get_magnets(torrent_dict):
        def get_hq_int(downloads):
            for x in range(len(downloads)):
                sd = None
                hd = None
                fhd = None
                if downloads[x]['res'] == '480':
                    sd = x
                elif downloads[x]['res'] == '720':
                    hd = x
                elif downloads[x]['res'] == '1080':
                    fhd = x
            if fhd:
                return fhd
            elif hd:
                return hd
            else:
                return sd
        cleaned_dict = {}
        for key in torrent_dict:
            try: #try to match the episode number
                adjusted_key = re.search(r".* - (\d\d.*)", key).group(1)
            except: #if not found let's use whatever we have
                adjusted_key = re.search(r".* - (.*)", key).group(1)
            if re.search(r"\d{2,}\.\d+", adjusted_key): #skip recap episodes
                continue
            if re.search(r"v\d+", adjusted_key): #remove version numbers from the number of the ep
                adjusted_key = re.sub(r"v\d+", "", adjusted_key)
            cleaned_dict.update({adjusted_key: torrent_dict[key]['downloads'][get_hq_int(torrent_dict[key]['downloads'])]['magnet']})
        return {k: cleaned_dict[k] for k in sorted(cleaned_dict, key=lambda x: list(cleaned_dict.keys()).index(x), reverse=True)}
    
    url = f'https://subsplease.org/api/?f=show&tz=Europe/Prague&sid={sub_id}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    batches = {}
    episodes = {}
    if response.status_code == 200:
        json_data = response.json()
        if json_data['batch']:
            batches.update(get_magnets(json_data['batch']))
        if json_data['episode']:
            episodes.update(get_magnets(json_data['episode']))
    return batches, episodes
    
#Utils

def read_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        if data == {}:
            return None
        else:
            return data
    else:
        return None

def save_json(file_path, data, overwrite = True):
    def update_json():
        json_copy = read_json(file_path)
        if json_copy is None:
            json_copy = {}
            json_copy.update(data)
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(json_copy, file, indent=4, ensure_ascii=False)

    json_file = read_json(file_path)
    if json_file != None:
        if overwrite:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
        else:
            update_json()
    else:
        update_json()     

def save_cache(data):
    save_json(cache_path, data, True)

def load_cache():
    cache = read_json(cache_path)
    return cache

def find_key(data, key_type):
    key_type = key_type.lower()
    if isinstance(data, dict):
        if key_type in data:
            return data[key_type]
        else:
            for value in data.values():
                result = find_key(value, key_type)
                if result is not None:
                    return result
    elif isinstance(data, list):
        for item in data:
            result = find_key(item, key_type)
            if result is not None:
                return result
    return None

def get_input(prompt, lower = True, data_type = str):
    while True:
        if lower:
          user_input = input(prompt).lower()
        else:
          user_input = input(prompt)
        try:
            converted_input = data_type(user_input)
            return converted_input
        except ValueError:
            print("Invalid input. Please enter a valid", data_type.__name__)

def subs_to_ani(anime_list):
    al_list = {}
    for anime in anime_list:
        if anime in manual_adjustments:
            al_list.update({manual_adjustments[anime]: anime_list[anime]})
        else:
            search_string = re.sub(r"S(\d+)$", r"Season \1", anime)
            al_id = alfetcher.get_id(search_string)
            if al_id is None:
                al_id = search_google_for_anilist_id(search_string)
                if al_id is None:
                    missing_ids.append(anime)
                    continue
            al_list.update({al_id: anime_list[anime]})
            save_json('manual_adjustments.json', {anime: al_id}, False)
    return al_list

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def generate_seasons(subs_list):
    subs_copy = copy.deepcopy(subs_list)
    from alfetcher import get_anime_info, get_season_ranges
    for ani_id in subs_list:
        working_entry = copy.deepcopy(subs_copy[ani_id]['episodes'])
        subs_copy[ani_id]['specials'] = {}
        anime_data = get_anime_info(ani_id)[ani_id]
        episode_count = anime_data['total_eps'] 
        if not episode_count:
            episode_count = 9999
        if ani_id == '146065':
            episode_count = 12
        start_ep_num = 1
        seasons_info = get_season_ranges(ani_id)
        season_ranges = seasons_info[0]
        season_ids = seasons_info[1]
        for ep in working_entry:
            try:
                if not int(ep) < 2:
                    start_ep_num = int(ep)
            except:
                pass
            if ep == '00' and int(ani_id) != 146065:
                subs_copy[ani_id]['specials'].update({ep: working_entry[ep]})
                working_entry.pop(ep)
            break
        modif_entries = copy.deepcopy(working_entry)
        for ep in working_entry:
            try:
                int(ep)
            except:
                if not subs_copy[ani_id]['batch'] and episode_count > 1:
                    subs_copy[ani_id]['specials'].update({ep: working_entry[ep]})
                    modif_entries.pop(ep)
        #remove empty dicts with no episodes
        if not subs_copy[ani_id]['episodes'] and not subs_copy[ani_id]['specials']:
            subs_copy.pop(ani_id)
            continue
        working_entry = modif_entries
        subs_copy[ani_id]['episodes'] = working_entry
        if not subs_copy[ani_id]['specials']:
            subs_copy[ani_id].pop('specials')
        elif not subs_copy[ani_id]['episodes']:
            subs_copy[ani_id]['episodes'] = subs_copy[ani_id]['specials']
            subs_copy[ani_id].pop('specials')
        if start_ep_num != 1:
            for season in season_ranges:
                if season_ranges[season]['start'] <= start_ep_num and start_ep_num <= season_ranges[season]['end']:
                    if season != ani_id:
                        subs_copy[season] = subs_copy[ani_id]
                        subs_copy.pop(ani_id)
                        ani_id = season
                        subs_copy[ani_id]['episodes'] = {}
                        e = 1
                        for ep in working_entry:
                            if e <= season_ranges[season]['total_eps'] :
                                en = str(e) if e > 9 else '0' + str(e)
                                subs_copy[ani_id]['episodes'].update({en: working_entry[ep]})
                                e += 1
        if season_ids:
            try:
                range_start = season_ids.index(ani_id) + 1 if start_ep_num > 1 else 0
            except:
                range_start = 0
            last_matched_ep = 0
            y = 0
            x = 0
            for x in range(range_start, len(season_ids)):
                following_id = season_ids[x]
                if not subs_copy[ani_id]['batch']:
                    subs_eps = len(working_entry)
                    if subs_eps > episode_count:
                        following_entry = {}
                        following_entry.update(subs_copy[ani_id])
                        following_entry['episodes'] = {}
                        if start_ep_num != 1:
                            for y in range(season_ranges[following_id]['start'], season_ranges[following_id]['end'] + 1):
                                if y - start_ep_num >= subs_eps:
                                    break
                                ep_num = str(y) if y > 9 else '0' + str(y)
                                real_num = str(y - season_ranges[season_ids[x - 1]]['end'] ) if y - season_ranges[season_ids[x - 1]]['end'] > 9 else '0' + str(y - season_ranges[season_ids[x - 1]]['end'] )
                                following_entry['episodes'].update({real_num: working_entry[ep_num]})
                        else:
                            for y in range(episode_count + last_matched_ep + 1, subs_eps):
                                ep_num = str(y) if y > 9 else '0' + str(y)
                                real_num = str(y - episode_count) if y - episode_count > 9 else '0' + str(y - episode_count)
                                following_entry['episodes'].update({real_num: working_entry[ep_num]})
                                subs_copy[ani_id]['episodes'].pop(ep_num)
                            last_matched_ep = y
                        subs_copy[following_id] = following_entry
                else:   
                    if len(subs_copy[ani_id]['episodes']) > 1:
                        index_key = get_key_by_index(working_entry, x + 1)
                        subs_eps = index_key.split('-')[1]
                        if int(subs_eps) > episode_count:
                            following_entry = {}
                            following_entry.update(subs_copy[ani_id])
                            following_entry['episodes'] = {index_key: working_entry[index_key]}
                            subs_copy[following_id] = following_entry
                            subs_copy[ani_id]['episodes'].pop(index_key)
                        else: 
                            subs_copy[ani_id]['episodes'] = {index_key: working_entry[index_key]}
    return subs_copy
def get_key_by_index(dict, index):
    x = 0
    for key, value in dict.items():
        if x == index:
            return key
        x += 1
    pass
    
def search_google_for_anilist_id(subs_name):
    search_string = subs_name.replace(' ', '+') + '+anilist'
    headers = {
        'User-agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
    }
    titles = {}
    similar_vals = []
    data = requests.get(f"https://www.google.com/search?q={search_string}", headers=headers).text
    ani_ids = re.findall(r"https://anilist.co/anime/(\d+)/", data)
    ani_ids = [i for n, i in enumerate(ani_ids) if i not in ani_ids[:n]]
    try:
        return ani_ids[0]
    except:
        return None
    #Made some code to sort the results, but lets trust google
    for ani_id in ani_ids:
        match_pattern = re.compile(rf"url=https://anilist.co/anime/{ani_id}/.*?h3.*?>(.*?)</h3")
        title = re.search(match_pattern, data).group(1)
        titles.update({ani_id: title})
    for al_id in titles:
        similar_val = similar(subs_name, titles[al_id])
        similar_vals.append(similar_val)
    max_similar = max(similar_vals)
    similar_index = similar_vals.index(max_similar)
    return ani_ids[similar_index]

cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ani_subs.json')
manual_adjustments = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_adjustments.json')
skip_list = []
# skip_list = ["Lee's Detective Agency", 
#             'Fruits Basket (2019)', 
#             'Fruits Basket (2019) S2', 
#             'Rail Romanesque S2', 
#             'Youjo Senki',     test = {}
#             'Mahouka Koukou no Rettousei',
#             'Tsugumomo S2 OVA',
#             'Edens Zero',
#             'Boruto - Naruto Next Generations',
#             'One Piece']

if __name__ == "__main__":
    #anime_list = get_all_anime()
    #subs_list = subs_to_ani(anime_list)
    #save_json(cache_path, subs_list)
    test_dict = read_json('scraped_sb.json')
    converted_dict = subs_to_ani(test_dict)
    save_json('converted_sb.json', converted_dict)
    subs_list = generate_seasons(converted_dict)
    save_cache(subs_list)
    pass