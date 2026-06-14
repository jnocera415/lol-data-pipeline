import requests 
import time

def api_request(url):
    
    while True:
        resp = requests.get(url)
        
        if resp.status_code == 200:
            return resp.json()
            
        elif resp.status_code == 429:
            
            print('')
            print('Attempt to request ' + str(url) + '\nand got an Error Code 429 (too many request).')
            cooldown = int(resp.headers.get("Retry-After", 10))
            print('Cooling Down for ' + str(cooldown) + ' seconds.')
            
            
            
            time.sleep(cooldown)
            
            print('Done cooldown!')
            print('')
            continue 
            
        else:
            print('Failed request. Error: '+ str(resp.status_code))
            return None
        
def fetch_raw_champion_data():
    
    game_version = api_request("https://ddragon.leagueoflegends.com/api/versions.json")[0]
    champion_url = "https://ddragon.leagueoflegends.com/cdn/" + str(game_version) + "/data/en_US/champion.json"
    champion_data = api_request(champion_url)['data']
    
    return champion_data

def parse_champion_tuples(raw_champion_data):
    
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

def fetch_item_data():
    
    game_version = api_request("https://ddragon.leagueoflegends.com/api/versions.json")[0]
    item_url = "https://ddragon.leagueoflegends.com/cdn/" + str(game_version) + "/data/en_US/item.json"
    item_data = api_request(item_url)['data']

    return item_data

def parse_item_tuples(raw_item_data):
    
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
    
    puuid_url = f'https://americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/' + gamename.replace(' ', '%20') + '/' + tagline.replace('#', '') + '?api_key=' + api_key
    user_puuid = api_request(puuid_url)['puuid']
    
    return user_puuid

def fetch_matchids(api_key, puuid, entire = False):
    
    matchids = []
    start = 0

    if entire:

        count = 100
    
    else: 

        count = 20
    
    while True:
        
        matchid_url = 'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/' + puuid + '/ids?start=' + str(start) + '&count=' + str(count) + '&api_key=' + api_key
        current_matchids = api_request(matchid_url)

        if current_matchids:

            matchids = matchids + list(current_matchids)
            start += count
        
        if not current_matchids or not entire:
            break
            
    return matchids

def fetch_match_data(matchid, api_key):
    
    match_stats_url = 'https://americas.api.riotgames.com/lol/match/v5/matches/' + matchid + '?api_key=' + api_key
    match_data = api_request(match_stats_url)['info']
    return match_data

def parse_match_tuples(match_data):
    
    #This Block of Code grabs the 'match' data
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    raw_game_id = match_data['gameId']       
    platform_id = match_data['platformId']    

    match_id = str(platform_id) + '_' + str(raw_game_id)

    match_tuple = (
        match_id,
        match_data['gameCreation'],
        match_data['gameDuration'],
        match_data['gameMode'],
        match_data['gameVersion']
    )

    
    player_tuples =[]
    participants_tuples = []
    item_tuples = []
    
    for i in range(len(match_data['participants'])):
        
        participant_data = match_data['participants'][i]

    #This Block of Code grabs the 'player' data
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
              
        cleaned_player_tuple = (
            participant_data['puuid'],
            participant_data['riotIdGameName'],
            participant_data['riotIdTagline'],
            0
        )
        
        player_tuples.append(cleaned_player_tuple)

        if match_data.get('gameMode') == 'STRAWBERRY':
            
            continue
    
        
    #This Block of Code grabs the 'match_participants' data
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        participantid = str(participant_data['puuid']) + str(match_id)
        
        cleaned_participant_tuple = (
            participantid, #This is the primary key for match_participants table
            participant_data['puuid'],
            match_id,
            participant_data['championId'],
            participant_data['lane'],
            participant_data['goldEarned'],
            participant_data['totalDamageDealtToChampions'],
            participant_data['totalHeal'],
            participant_data['kills'],
            participant_data['deaths'],
            participant_data['assists'],
            1 if participant_data['win'] == True else 0
        )
        
        participants_tuples.append(cleaned_participant_tuple)
        
        #This Block of Code grabs the 'participant_items' data
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        for j in range(7):
            
            if participant_data['item' + str(j)] != 0:
                
                item_tuples.append((participantid, participant_data['item' + str(j)], j))   
    
    return match_tuple, player_tuples, participants_tuples, item_tuples