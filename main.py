from riot_api import *
import database_pipeline    
import time

from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("RIOT_API_KEY")

driver = os.getenv("DB_DRIVER")
server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")

def update_static_data():
    
    # Fetch Static Data and Upsert to Database

    raw_champion_data = fetch_raw_champion_data()
    champion_tuples, champion_tag_tuples = parse_champion_tuples(raw_champion_data)
    raw_item_data = fetch_item_data()
    item_tuples, item_tag_tuples = parse_item_tuples(raw_item_data)

    my_pipeline.upsert_items_table(item_tuples)
    my_pipeline.upsert_item_tags_table(item_tag_tuples)
    my_pipeline.upsert_champions_table(champion_tuples)
    my_pipeline.upsert_champion_tags_table(champion_tag_tuples)

def update_selected_player_history(list_of_players):
    
    #Grabs and throws players entire history and store into the database
    
    for player in list_of_players:

        gamename, tagline = player
        puuid = fetch_puuid(api_key, gamename, tagline)
        matchids = fetch_matchids(api_key, puuid, True)

        all_existing_matches = my_pipeline.get_all_existing_matches()

        batch_match_tuples = []
        batch_player_tuples = []
        batch_match_participant_tuples = []
        batch_participant_item_tuples = []

        print(f"Updating Player {gamename}'s games.")
        start_time = time.perf_counter()

        for matchid in matchids:

            if matchid in all_existing_matches:
                continue
                
            match_data = fetch_match_data(matchid, api_key)

            if not match_data:
                continue

            match_tuple, player_tuples, match_participant_tuples, participant_item_tuples = parse_match_tuples(match_data)

            batch_match_tuples.append(match_tuple)
            batch_player_tuples.extend(player_tuples)
            batch_match_participant_tuples.extend(match_participant_tuples)
            batch_participant_item_tuples.extend(participant_item_tuples)

        my_pipeline.upsert_players_table(batch_player_tuples)
        my_pipeline.upsert_matches_table(batch_match_tuples)
        my_pipeline.upsert_match_participants_table(batch_match_participant_tuples)
        my_pipeline.upsert_participant_items_table(batch_participant_item_tuples)

        my_pipeline.commit()

        end_time = time.perf_counter()
        time_delta = end_time - start_time

        print(f"Finish Updating Player {gamename}'s games.")
        print(f"It took {time_delta} seconds to process {player}'s data.")
        print()

def send_match_info(puuid):

    matchids = fetch_matchids(api_key, puuid, False)

    all_existing_matches = my_pipeline.get_all_existing_matches()
    
    batch_match_tuples = []
    batch_player_tuples = []
    batch_match_participant_tuples = []
    batch_participant_item_tuples = []

    for matchid in matchids:

        if matchid in all_existing_matches:
            continue
            
        match_data = fetch_match_data(matchid, api_key)

        if not match_data:
            continue

        print(f"Adding match id {matchid} to table")

        match_tuple, player_tuples, match_participant_tuples, participant_item_tuples = parse_match_tuples(match_data)

        batch_match_tuples.append(match_tuple)
        batch_player_tuples.extend(player_tuples)
        batch_match_participant_tuples.extend(match_participant_tuples)
        batch_participant_item_tuples.extend(participant_item_tuples)

    my_pipeline.upsert_players_table(batch_player_tuples)
    my_pipeline.upsert_matches_table(batch_match_tuples)
    my_pipeline.upsert_match_participants_table(batch_match_participant_tuples)
    my_pipeline.upsert_participant_items_table(batch_participant_item_tuples)

    my_pipeline.commit()

my_pipeline = database_pipeline.database_pipeline(driver, server, database, username, password)
my_pipeline.connect()

puuid = '--h2hfGe90W_M3uc2TqaGSzQfDTyVeXB650aPQ9H8NN730H2RdX12Ktrdt7AAzEDqVZys9L_2GnEKA'

list_of_players = [('Ferdalicious', 'NA1')]

'''
list_of_players = [('Papa Jonathan', '1337'),
                   ('Bloo', 'LoyUM'),
                   ('BOYNEXTDOOR', 'BND'),
                   ('cherrybee27', 'NA1'),
                   ('Densanzon', 'NA1'),
                   ('Ferdalicious', 'NA1'),
                   ('Flowz', 'NA10'),
                   ('Jaycourt', 'NA1'),
                   ('Kyoshii', '1133'),
                   ('MizterCoffee', 'NA1'),
                   ('Optimusbrown', '7674')]
'''

start_time = time.perf_counter()
#update_static_data()
update_selected_player_history(list_of_players)
end_time = time.perf_counter()
time_delta = end_time - start_time

print(f"It took {time_delta} seconds to run everthing")



