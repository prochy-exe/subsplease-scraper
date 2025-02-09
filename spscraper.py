import requests, copy, re, json, os, alfetcher
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

missing_ids = []
incorrect_ids = []

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
        item[title]['batches'], item[title]['episodes'], item[title]['specials'] = get_torrent_links(item[title]['id'])        
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
    specials = {}
    if response.status_code == 200:
        json_data = response.json()
        if json_data['batch']:
            batches.update(get_magnets(json_data['batch']))
        if json_data['episode']:
            episodes.update(get_magnets(json_data['episode']))
            new_episodes = copy.deepcopy(episodes)
            for episode in episodes:
                if not episode.isdigit():
                    specials[episode] = new_episodes.pop(episode)
            episodes = new_episodes
    return batches, episodes, specials
    
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

def process_anime(anime_id, anime_dict):
    global seasons_dict
    from alfetcher import get_anime_info, get_season_ranges
    def process_episodes(episode_torrents, working_season, working_id):
        if episode_torrents:
            skipped_eps = 0
            total_eps = int(anime_info['total_eps']) if anime_info['total_eps'] else 99999
            if int(list(episode_torrents.keys())[-1]) != total_eps:
                episode_adjustment = episode_adjustments[working_id] if working_id in episode_adjustments else 0
                seasons_dict[working_id]['episodes'] = {}
                for org_episode in episode_torrents:
                    while True:
                        episode = int(org_episode) - episode_adjustment
                        if episode <= int(season_ranges[working_season]['end']):
                            if working_id not in seasons_dict:
                                seasons_dict[working_id] = copy.deepcopy(anime_dict)
                                seasons_dict[working_id]['episodes'] = {}
                            seasons_dict[working_id]['episodes'][f"{(int(episode) - skipped_eps):02}"] = episode_torrents[f"{episode + episode_adjustment}"]
                            break
                        else:
                            skipped_eps += season_ranges[working_season]['total_eps']
                            working_season += 1
                            working_id = str(season_ranges[working_season]['id'])
                            episode_adjustment = episode_adjustments[working_id] if working_id in episode_adjustments else 0

    def process_batches(batch_torrents, working_season, working_id):
        if batch_torrents:
            total_eps = int(anime_info['total_eps']) if anime_info['total_eps'] else 99999
            if int(list(batch_torrents.keys())[-1].split('-')[1]) != total_eps:
                seasons_dict[working_id]['batches'] = {}
                for batch in batch_torrents:
                    while True:
                        if int(batch.split('-')[1]) <= int(season_ranges[working_season]['end']):
                            if working_id not in seasons_dict:
                                seasons_dict[working_id] = copy.deepcopy(anime_dict)
                                seasons_dict[working_id]['batches'] = {}
                            seasons_dict[working_id]['batches'][f"01-{season_ranges[working_season]['total_eps']:02}"] = batch_torrents[batch]
                            break
                        else:
                            working_season += 1
                            working_id = str(season_ranges[working_season]['id'])


    working_season = 1
    working_id = anime_id
    if anime_id == '21311':
        pass
    anime_info = get_anime_info(anime_id)[anime_id]
    season_ranges = get_season_ranges(anime_id)
    seasons_dict = {anime_id: copy.deepcopy(anime_dict)}
    episode_torrents = anime_dict['episodes']
    batch_torrents = anime_dict['batches']
    try:
        process_episodes(episode_torrents, working_season, working_id)
        process_batches(batch_torrents, working_season, working_id)
        ids_to_remove = []
        for season in seasons_dict:
            if not seasons_dict[season]['episodes'] and not seasons_dict[season]['batches']:
                ids_to_remove.append(season)
        [seasons_dict.pop(season_id) for season_id in ids_to_remove]
    except Exception as e:
        seasons_dict = {}
    return seasons_dict

def generate_seasons(subs_list):
    new_subs_list = copy.deepcopy(subs_list)
    for anime in subs_list:
        current_entry =  subs_list[anime]
        season_entries = process_anime(anime, current_entry)
        if season_entries:
            new_subs_list.pop(anime)
            new_subs_list.update(season_entries)
        else:
            incorrect_ids.append(anime)
    return new_subs_list
    
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
episode_adjustments = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'episode_adjustments.json')
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
    # anime_list = get_all_anime()
    # save_json('scraped_sb.json', anime_list)
    # converted_dict = subs_to_ani(anime_list)
    # save_json('converted_sb.json', converted_dict)
    converted_dict = read_json('converted_sb.json')
    subs_list = generate_seasons(converted_dict)
    save_cache(subs_list)
    save_json('incorrect_ids.json', {'incorrect_ids': incorrect_ids})
    save_json('missing_ids.json', {'missing_ids': missing_ids})
    pass