import re, time, requests
from pynyaasi.nyaasi import NyaaSiClient
from spscraper import load_cache

missing_entries = []

def verify_torrent(anime, torrents_local):
  def append_prefix(epNumber):
    if epNumber < 10:
      return '0' + str(epNumber)
    else:
      return str(epNumber)
  global missing_entries
  client = NyaaSiClient()
  exceptions = {
    '[-KS-] My Hero Academia (Boku no Hero Academia) S5 - 01 [1080p] [Dual Audio] [CC] [FUNimation] [D822D670]': 89
  }
  init_resource = client.get_resource(int(torrents_local[0][len('https://nyaa.si/view/'):])).title
  try:
    init_ep = int(re.search(r"- (\d\d\d\d|\d\d\d|\d\d)", init_resource).group(1))
  except Exception as e:
    return # Skip when an anime has a first episode unconventional (SP, OVA...) or if its a movie, we dont need to check those
  if init_resource in exceptions:
    init_ep = exceptions[init_resource]
  expected_ep = init_ep + 1
  for x in range(1, len(torrents_local)):
    torrent = torrents_local[x]
    resource = client.get_resource(int(torrent[len('https://nyaa.si/view/'):])).title
    if not ('- ' + append_prefix(expected_ep)) in resource:
      missing_entries.append(f'missing ep: {expected_ep}, {anime}')
    expected_ep += 1

def verify_torrents():
    # Load cache
    cache = load_cache()

    # List of IDs to skip
    skip_list_ids = [
        '132096',
        '135939',
        '122148'
    ]
    for anime in cache:
      if anime not in skip_list_ids:
        anime_links = cache[anime]['nyasii_links']
        verify_torrent(anime, anime_links)
                
verify_torrents()
if missing_entries:
  for entry in missing_entries:
    print(entry+'\n')
  exit(1)
