from alfetcher import get_anime_info
import os, json

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

ani_list = read_json('ani_subs.json')
for key in ani_list:
    get_anime_info(key, True)