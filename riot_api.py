import requests 
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def api_request(url):
    """Send a request to the Riot API and handle common rate-limit and auth responses."""
    while True:
        resp = requests.get(url)
        
        if resp.status_code == 200:
            return resp.json()
        
        elif resp.status_code == 401:
            logging.warning('Error 401: Unauthroized Request')
            return None
        elif resp.status_code == 429:
            logging.warning('Error 429: API Recieved Too Many Requests')
            cooldown = int(resp.headers.get("Retry-After", 10))
            logging.info('Cooling Down for ' + str(cooldown) + ' seconds.')
            
            time.sleep(cooldown)
            
            logging.info('Done cooldown!')
            continue 
        
        elif resp.status_code == 503:
                 logging.warning('')

        else:
            logging.error('Failed request. Error: '+ str(resp.status_code))
            return None
        
def fetch_raw_champion_data():
    """Fetch the current champion data from Data Dragon."""
    game_version = api_request("https://ddragon.leagueoflegends.com/api/versions.json")[0]
    champion_url = "https://ddragon.leagueoflegends.com/cdn/" + str(game_version) + "/data/en_US/champion.json"
    champion_data = api_request(champion_url)['data']
    
    return champion_data

def parse_champion_tuples(raw_champion_data):
    """Convert champion JSON into database-friendly tuples for champions and tags."""
    cleaned_champion_data = []
    cleaned_champion_tags = []
    
    for champion in raw_champion_data:
        
        championid = raw_champion_data[champion]['key']
        champion_name = raw_champion_data[champion]['name']
        champion_title = raw_champion_data[champion]['title']
        champion_tags = raw_champion_data[champion]['tags']
        
        cleaned_champion_data.append((championid, champion_name, champion_title))
        
        for tag in champion_tags:
            
            cleaned_champion_tags.append((championid, tag))
    
    return cleaned_champion_data, cleaned_champion_tags

def fetch_queue_ids():
    """Fetch the current queue IDs and names from Riot's API."""
    queue_url = "https://static.developer.riotgames.com/docs/lol/queues.json"
    queue_data = api_request(queue_url)
    
    return queue_data

def parse_queue_tuples(raw_queue_data):
    """Convert queue JSON into database-friendly tuples for queue IDs and names."""
    cleaned_queue_data = []
    
    for queue in raw_queue_data:
        queueid = queue['queueId']
        map_name = queue['map']
        queue_name = queue['description']
        
        cleaned_queue_data.append((queueid, map_name, queue_name))
    
    cleaned_queue_data.append((1750, 'Rings of Wrath', 'Arena'))
    return cleaned_queue_data

def fetch_item_data():
    """Fetch the current item data from Data Dragon."""
    game_version = api_request("https://ddragon.leagueoflegends.com/api/versions.json")[0]
    item_url = "https://ddragon.leagueoflegends.com/cdn/" + str(game_version) + "/data/en_US/item.json"
    item_data = api_request(item_url)['data']

    return item_data

def parse_item_tuples(raw_item_data):
    """Convert item JSON into database-friendly tuples for items and tags."""
    cleaned_item_data = []
    cleaned_item_tags = []
    
    for item in raw_item_data:
    
        itemid = item
        item_name = raw_item_data[item]['name']
        gold_cost = raw_item_data[item]['gold']['total']
        item_tags = raw_item_data[item]['tags']
        
        cleaned_item_data.append((itemid, item_name, gold_cost))
        
        for tag in item_tags:
            
            cleaned_item_tags.append((itemid, tag))

    return cleaned_item_data, cleaned_item_tags

def fetch_puuid(api_key, gamename, tagline):
    """Look up a player's Riot PUUID by their in-game name and tagline."""
    puuid_url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/' + gamename.replace(' ', '%20') + '/' + tagline.replace('#', '') + '?api_key=' + api_key
    user_puuid = api_request(puuid_url)['puuid']
    
    return user_puuid

def fetch_matchids(api_key, puuid, start = 0, count = 20):
    """Fetch a list of recent match IDs for a player."""
    matchid_url = 'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/' + puuid + '/ids?start=' + str(start) + '&count=' + str(count) + '&api_key=' + api_key
    matchids = api_request(matchid_url)

    return matchids

def fetch_match_data(matchid, api_key):
    """Retrieve the detailed info for a single match."""
    match_stats_url = 'https://americas.api.riotgames.com/lol/match/v5/matches/' + matchid + '?api_key=' + api_key
    match_data = api_request(match_stats_url)['info']
    return match_data

def parse_match_tuples(match_data):
    """Transform match JSON into tuples for matches, players, participants, and items."""
    # This block builds the base match record.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    raw_game_id = match_data['gameId']       
    platform_id = match_data['platformId']    

    match_id = str(platform_id) + '_' + str(raw_game_id)

    match_tuple = (
        match_id,
        match_data['gameCreation'],
        match_data['gameDuration'],
        match_data['queueId'],
        match_data['gameVersion']
    )

    player_tuples =[]
    participants_tuples = []
    item_tuples = []
    
    for i in range(len(match_data['participants'])):
        
        participant_data = match_data['participants'][i]

    # This block builds player rows for each participant.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
              
        cleaned_player_tuple = (
            participant_data['puuid'],
            participant_data['riotIdGameName'],
            participant_data['riotIdTagline'],
            0
        )
        
        player_tuples.append(cleaned_player_tuple)
    
    # This block builds the participant rows for the database.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        participantid = str(participant_data['puuid']) + str(match_id)
        
        cleaned_participant_tuple = (
            participantid, #This is the primary key for match_participants table
            participant_data['puuid'],
            match_id,
            participant_data['championId'],
            participant_data['teamPosition'],
            participant_data['goldEarned'],
            participant_data['totalDamageDealtToChampions'],
            participant_data['totalHeal'],
            participant_data['kills'],
            participant_data['deaths'],
            participant_data['assists'],
            participant_data['visionScore'],
            1 if participant_data['win'] == True else 0
        )
        if match_data['gameMode'] == 'STRAWBERRY':  
            cleaned_participant_tuple = (
            participantid,
            participant_data['puuid'],
            match_id,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            1 if participant_data['win'] == True else 0
        )
        participants_tuples.append(cleaned_participant_tuple)
        
        # This block gathers any items owned by the participant.
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if match_data['gameMode'] == 'STRAWBERRY':
            continue
        for j in range(7):
            if participant_data['item' + str(j)] != 0:
                item_tuples.append(
                    (participantid,
                    participant_data['item' + str(j)],
                    j)
                )
    
    return match_tuple, player_tuples, participants_tuples, item_tuples