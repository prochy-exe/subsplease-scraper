import requests, copy, re, json, os
from bs4 import BeautifulSoup

missing_ids = []
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
            matched_url = False
            if anime_title not in skip_list:
                if anime_title == 'Boku no Hero Academia':#the fandom isn't the only thing that requires special attention ig
                    anime_info = subspleaseinfo_bh(anime_title)
                else:    
                    anime_info = get_data(listing_url)
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

def subs_to_ani(subs_entry, reverse = False):
    from alfetcher import get_id, get_anime_info
    
    def check_manual_adjust(anime_key, manually_adjusted_strings):
        if not manually_adjusted_strings:
            manually_adjusted_strings = {}
        if manually_adjusted_strings and anime_key in manually_adjusted_strings:
            checked_id = manually_adjusted_strings[anime_key]
        else:
            missing_ids.append(anime_key)
            return None
            checked_id = get_input(f'Type in AniList ID of the anime(SubsPlease match: {anime_key}): ', False, str)
            checked_id = checked_id if checked_id else None
            manually_adjusted_strings[anime_key] = checked_id if checked_id else None
        if manually_adjusted_strings:
            save_json(manual_adjustments_path, manually_adjusted_strings, True)
        return checked_id

    manually_adjusted_strings = read_json(manual_adjustments_path)
    new_list = {}
    for key in subs_entry:
        pattern = re.compile(r's(\d)', re.I)
        title = re.sub(pattern, f'Season \\1', key)
        anime_id = get_id(title)
        if not anime_id:
            anime_id = check_manual_adjust(key, manually_adjusted_strings)
            if not anime_id: continue
        else:
            anime_id = str(anime_id)
            info = get_anime_info(anime_id)[anime_id]
            anime_state = find_key(info, 'status')
            if anime_state == 'NOT_YET_RELEASED':
                anime_id = check_manual_adjust(key, manually_adjusted_strings)
        # Add the value with the new key
        new_list[anime_id] = key
    if reverse:
        return {subs_value:anilist_key for anilist_key, subs_value in new_list.items()} #Returns Subsplease title: AniList ID
    else:
        return new_list #Returns AniList ID: Subsplease title

def get_ani_id_from_subs_title(subs_entry, title, reverse = False):
    manually_adjusted_strings = read_json(manual_adjustments_path)
    if manually_adjusted_strings and title in manually_adjusted_strings:
        anime_dict =  manually_adjusted_strings
    else:
        anime_dict = subs_to_ani(subs_entry, True)
    try:
        anime_id = anime_dict[title]
    except:
        return None
    if anime_id:
      save_json(conv_dict_path, {anime_id: title}, False)
    return anime_id

def create_season_keys(subs_entry):
    from alfetcher import get_anime_info
    current_cache = load_cache()
    subs_list_new = copy.deepcopy(subs_entry)
    test_int = None
    for key in subs_entry:
        try:
            test_int = int(key)
            ani_key = key
        except ValueError:
            ani_key = get_ani_id_from_subs_title({key: subs_entry[key]}, key)
            if not ani_key: return None
        subs_list_new[ani_key] = subs_entry[key]
        if not test_int:
            del subs_list_new[key]
        hasSeason = True
        checked_episodes = 0
        skipped_episodes = 0
        cleared_ids = []
        while hasSeason:
            anime_id = ani_key
            anime_info = get_anime_info(anime_id)[anime_id]
            anime_relations = find_key(anime_info, 'related')
            previous_episodes = 0
            hasSeason = False
            if not anime_relations:
                break
            for relation in anime_relations:
                if relation not in cleared_ids:
                    if anime_relations[relation]['status'] != 'NOT_YET_RELEASED' and anime_relations[relation]['type'] == 'SEQUEL':
                        anime_relation = relation
                        hasSeason = True
                        break
                    elif anime_relations[relation]['type'] == 'PREQUEL' and relation in current_cache:
                        previous_episodes = len(current_cache[relation]['nyaasi_links'])
                        break                        
            if anime_relations:
                try:
                    season_id = str(anime_relation)
                except:
                    season_id = None
                if season_id is not None and season_id in subs_list_new and checked_episodes == 0:
                    break     
                sub_id = subs_entry[key]['id']
                url = f'https://subsplease.org/api/?f=show&tz=Europe/Prague&sid={sub_id}'
                headers = {'Content-Type': 'application/json'}
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    json_response = response.json()['episode']
                    json_data = {}
                    if not json_response:
                        break
                    # Iterate over the reversed items and populate the new dictionary
                    for reverse_key, value in reversed(json_response.items()):
                        json_data[reverse_key] = value
                first_key = next(iter(json_data.keys()))
                episode_string = json_data[first_key]['episode']
                try:
                    starting_episode = int(episode_string)
                except:
                    if (re.search(r"movie", episode_string, re.I) or
                        re.search(r"v\d", episode_string, re.I) or #i really dont know what to do about this, just save me
                        re.search(r"movie", json_data[first_key]['show'], re.I)):
                        starting_episode = 1                        
                    else:
                        break
                links = subs_entry[key]['nyaasi_links']
                link_amount = len(subs_entry[key]['nyaasi_links'])
                episode_amount = find_key(anime_info, 'total_eps')
                if not episode_amount:
                    sorted_magnets = []
                    if link_amount - previous_episodes < 1: previous_episodes = 0
                    for x in range(previous_episodes, link_amount):
                        try:
                            sorted_magnets.append(links[x])
                            x += 1
                        except:
                            break
                    subs_list_new[ani_key]['nyaasi_links'] = sorted_magnets
                    break
                if link_amount > episode_amount:
                    checked_episodes += previous_episodes
                if starting_episode > episode_amount + skipped_episodes:
                    skipped_episodes += episode_amount
                    if ani_key not in cleared_ids:
                        try:
                            del subs_list_new[ani_key]
                            cleared_ids.append(ani_key)
                        except:
                           cleared_ids.append(ani_key) 
                    ani_key = season_id
                    save_json(conv_dict_path, {ani_key: key}, False)
                    continue
                sorted_magnets = []
                for x in range(0, episode_amount):
                    try:
                        sorted_magnets.append(links[x + checked_episodes])
                        x += 1
                    except:
                        break
                if starting_episode == 0:
                    x = x + 1
                checked_episodes += x
                leftover_episodes = link_amount - checked_episodes
                if leftover_episodes  > 0 and episode_amount > 1:
                    subs_list_new[season_id] = copy.deepcopy(subs_entry[key])
                    leftover_magnets = []
                    for y in range(checked_episodes, link_amount):
                        leftover_magnets.append(links[y])
                elif leftover_episodes  > 0:
                    subs_list_new[season_id] = copy.deepcopy(subs_entry[key])
                    leftover_magnets = []
                    leftover_magnets.append(links[checked_episodes])
                try:
                    subs_list_new[ani_key]['nyaasi_links'] = sorted_magnets
                except:
                    subs_list_new[ani_key] = copy.deepcopy(subs_entry[key])
                    subs_list_new[ani_key]['nyaasi_links'] = sorted_magnets
                cleared_ids.append(ani_key)
                if season_id is not None:
                    try:
                        subs_list_new[season_id]['nyaasi_links'] = leftover_magnets
                    except:
                        hasSeason = False
                else:
                    break
            ani_key = season_id
            save_json(conv_dict_path, {ani_key: key}, False)
    return subs_list_new
                
    
def update_list(subs_list):
    # URL of the webpage
    url = "https://subsplease.org/shows"
    base = "https://subsplease.org"
    # Send a GET request to the URL
    response = requests.get(url)
    list_urls = [entry['url'] for entry in subs_list.values()]
    not_found = []
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
            item_url = base + link.a['href']
            if anime_title not in skip_list and item_url not in list_urls:
                data = get_data(item_url)
                if data:
                    anilist_data = create_season_keys(data)
                    if anilist_data: subs_list.update(anilist_data)
    else:
        print("Failed to retrieve webpage. Status code:", response.status_code)
    return subs_list

def gen_cache():
    cleaned_list = load_cache()
    final_cache = create_season_keys(cleaned_list)
    save_cache(final_cache)

def subspleaseinfo_bh(search_string):
    url = "https://subsplease.org/shows"
    url_request = f'https://subsplease.org/api/?f=search&tz=Europe/Prague&s={search_string}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url_request, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
    items_dict = {}
    items_dict[search_string] = {}
    items_dict[search_string]['url'] = url + '/' + json_data[next(iter(json_data.keys()))]['page']
    items_dict[search_string]['id'] = get_subsplease_id(items_dict[search_string]['url'])
    torrent_link = get_torrent_link_bh(items_dict[search_string]['id'])[0]
    skip_list = get_torrent_link_bh(items_dict[search_string]['id'])[1]
    items_dict[search_string]['nyaasi_links'] = torrent_link
    
    for skip in skip_list:
        items_dict[skip] = {}
        items_dict[skip]['url'] = url + '/' + json_data[next(iter(json_data.keys()))]['page']
        items_dict[skip]['id'] = get_subsplease_id(items_dict[search_string]['url'])
        torrent_link = skip_list[skip]
        items_dict[skip]['nyaasi_links'] = torrent_link

    return items_dict
    #save_cache(items_dict) 

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
        torrent_link = get_torrent_link(item[title]['id'])
        item[title]['nyaasi_links'] = torrent_link

        if not torrent_link:
            return None
        else:
            return item
    else:
        print("Failed to retrieve webpage. Status code:", response.status_code)

def get_torrent_link(sub_id):
    url = f'https://subsplease.org/api/?f=show&tz=Europe/Prague&sid={sub_id}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        json_data = response.json()
        torrent_links = []
        if json_data['episode']:
            for episode in json_data['episode']:
                if '.5' not in episode:
                    for download in json_data['episode'][episode]['downloads']:
                        if download['res'] == '1080':
                            raw_url = download['torrent']
                            if raw_url.endswith("/torrent"):
                                raw_url = raw_url[:-len("/torrent")]
                            torrent_links.insert(0, raw_url)  
        elif json_data['batch']:
            for batch in json_data['batch']:
                for download in json_data['batch'][batch]['downloads']:
                    if download['res'] == '1080':
                        raw_url = download['torrent']
                        if raw_url.endswith("/torrent"):
                            raw_url = raw_url[:-len("/torrent")]
                        torrent_links.insert(0, raw_url)
        else:
            torrent_links = None
        return torrent_links

def get_torrent_link_bh(sub_id):
    url = f'https://subsplease.org/api/?f=show&tz=Europe/Prague&sid={sub_id}'
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers)
    skipped_eps = {}
    ona = []
    if response.status_code == 200:
        json_data = response.json()
        torrent_links = []
        try:
            for episode in json_data['episode']:
                for download in json_data['episode'][episode]['downloads']:
                    if download['res'] == '1080':
                        raw_url = download['torrent']
                        if raw_url.endswith("/torrent"):
                            raw_url = raw_url[:-len("/torrent")]
                        if not re.search(r"\d", episode, re.I):
                            if episode == 'Boku no Hero Academia - UA Heroes Battle':
                                skipped_eps[episode] = raw_url
                                break
                            else:
                                ona.insert(0, raw_url)
                                if episode == 'Boku no Hero Academia - Hero League Baseball':
                                    skipped_eps[episode] = ona
                                break
                        else:
                            torrent_links.insert(0, raw_url)
                        break
        except KeyError:
            for batch in json_data['batch']:
                for download in json_data['batch'][batch]['downloads']:
                    if download['res'] == '1080':
                        raw_url = download['torrent']
                        if raw_url.endswith("/torrent"):
                            raw_url = raw_url[:-len("/torrent")]
                        torrent_links.insert(0, raw_url)
        return torrent_links, skipped_eps

def get_subsplease_id(url):
    # URL of the webpage

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
        return sid_value
    else:
        print("Failed to retrieve webpage. Status code:", response.status_code)
 
def update_entries(subs_entry):
    from alfetcher import get_anime_info
    
    def filter_404_links(links):
        for link in links:
            response = requests.head(link)
            if response.status_code == 404:
                return 'reset'
    
    copied_entries = copy.deepcopy(subs_entry)
    checked_keys = []
    missing_keys = []
    for key in subs_entry:
        anime_status = find_key(get_anime_info(key), 'status')
        try:
            remote_key = read_json(conv_dict_path)[key]
        except:
            missing_keys.append(key)
            continue
        if anime_status == 'RELEASING' and remote_key not in checked_keys:
            entry_url = subs_entry[key]['url']
            remote_entry = get_data(entry_url)
            modified_entry = create_season_keys({key: remote_entry[remote_key]})
            try:
                last_url = modified_entry[key]['nyaasi_links'][-1]
            except:
                print("DEBUG: Error occurred while accessing 'nyaasi_links'")
                print(modified_entry[key])
                continue
            current_urls = copied_entries[key]['nyaasi_links']
            try:
                if last_url not in current_urls:
                    current_urls.append(last_url)
            except:
                current_urls = [last_url]
            filtered_urls = filter_404_links(current_urls)
            if filtered_urls == 'reset':
                filtered_urls = modified_entry[key]['nyaasi_links']
            else:
                filtered_urls = current_urls
            copied_entries[key]['nyaasi_links'] = filtered_urls
    return copied_entries
    
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
    
def yank_anime_entry(name):
    ani_list = load_cache()
    return {name: ani_list[name]}

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

def check_cache():
    from alfetcher import get_anime_info
    attention = []
    cache = load_cache()
    for entry in cache:
        anime_data = get_anime_info(entry)
        anime_amount = find_key(anime_data, 'total_eps')
        anime_status = find_key(anime_data, 'status')
        links_amount = len(cache[entry]['nyaasi_links'])
        if links_amount != anime_amount and anime_status != 'RELEASING':
            attention.append([entry, 'https://anilist.co/anime/' + entry, str(links_amount)+'/'+str(anime_amount)])
    for anime_id in attention:
        print(anime_id)

def generate_conv_keys():
    cache = load_cache()
    
    def get_title(url):
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
            title = soup.find('h1', class_='entry-title').text
            title = re.sub('–', '-', title)
            title = re.sub('’', "'", title)
            
            return title
        else:
            print("Failed to retrieve webpage. Status code:", response.status_code)

    for key in cache:
        save_json(conv_dict_path, {key: get_title(cache[key]['url'])}, False)

conv_dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conv_dict.json')
cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ani_subs.json')
manual_adjustments_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_adjustments.json')
skip_list = ["Lee's Detective Agency", 
            'Fruits Basket (2019)', 
            'Fruits Basket (2019) S2', 
            'Rail Romanesque S2', 
            'Youjo Senki', 
            'Mahouka Koukou no Rettousei',
            'Tsugumomo S2 OVA',
            'Edens Zero',
            'Boruto - Naruto Next Generations',
            'One Piece']

if __name__ == "__main__":
  cache = load_cache()
  updated_list = update_list(cache)
  updated_entries = update_entries(updated_list)
  save_cache(updated_entries)
  for missing_entry in missing_ids:
    print(missing_entry)