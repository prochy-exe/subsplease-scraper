import os, json
from alfetcher import get_anime_info

cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ani_subs.json')

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

def load_cache():
    cache = read_json(cache_path)
    return cache

subs_list = load_cache()

attention_please = {}

for anime in subs_list:
    if not subs_list[anime]['batch']:
        anime_info = get_anime_info(anime)[anime]
        eps = anime_info['total_eps']
        if eps and int(eps) != len(subs_list[anime]['episodes']) and anime_info['status'] != 'RELEASING':
            problem_dict = subs_list[anime]
            attention_please.update({anime: eps})

print("-------------------")
for attention in attention_please:
    print(f"{attention} has an incorrect number of episodes")
    print(f"expected: {attention_please[attention]} , got {len(subs_list[attention]['episodes'])}")
    print(subs_list[attention]['url'])
    print(f"https://www.anilist.co/anime/{attention}")
    print("-------------------")
