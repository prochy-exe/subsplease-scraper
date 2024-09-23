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
    current_entry = subs_list[anime]
    anime_info = get_anime_info(anime)[anime]
    eps = anime_info['total_eps']
    if current_entry['batch']:
        for ep in current_entry['episodes']:
            ep_split = ep.split('-')
            break
        try:
            start = int(ep_split[0])
        except ValueError as e:
            error = e.args[0] 
            if error == "invalid literal for int() with base 10: 'Complete'":
                pass
                continue
            else:
                attention_please.update({anime: "problem"})
                continue
        end = int(ep_split[1])
        ep_count = len(current_entry['episodes'])
        batch_coverage = (end - start) + 1
        if ep_count != 1 or (eps != batch_coverage and start > 1):
            attention_please.update({anime: f"{eps} batch"})
    else:

        if eps and int(eps) != len(current_entry['episodes']) and anime_info['status'] != 'RELEASING':
            attention_please.update({anime: eps})

print("-------------------")
for attention in attention_please:
    print(f"{attention} has an incorrect number of episodes")
    print(f"expected: {attention_please[attention]} , got {len(subs_list[attention]['episodes'])}")
    print(subs_list[attention]['url'])
    print(f"https://www.anilist.co/anime/{attention}")
    print("-------------------")
pass