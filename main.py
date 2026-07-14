from riot_api import *
from dotenv import load_dotenv
import database_pipeline    
import time
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s\n%(message)s",
    force=True
)


def update_static_data():
    """Fetch the latest static League data and store it in the database."""
    # Fetch item and champion information, including tags, from Riot and upsert it into the database.
    # Although labeled as static, champions and item stats can change between patches.
    raw_champion_data = fetch_raw_champion_data()
    champion_tuples, champion_tag_tuples = parse_champion_tuples(raw_champion_data)
    raw_item_data = fetch_item_data()
    item_tuples, item_tag_tuples = parse_item_tuples(raw_item_data)
    raw_queue_data = fetch_queue_ids()
    queue_tuples = parse_queue_tuples(raw_queue_data)

    my_pipeline.upsert_items_table(item_tuples)
    my_pipeline.upsert_item_tags_table(item_tag_tuples)
    my_pipeline.upsert_champions_table(champion_tuples)
    my_pipeline.upsert_champion_tags_table(champion_tag_tuples)
    my_pipeline.upsert_queue_ids_table(queue_tuples)
    my_pipeline.commit()

def send_match_info(puuid, entire = False):
    """Fetch and store a player's recent matches in batches."""
    game_count_position = 0
    number_of_games_per_batch = 100 if entire else 20
    logging.info(f"Fetching match data\nPUUID: {puuid}")
    matchids_in_database = my_pipeline.get_match_ids_by_puuid(puuid)
    while True:
        matchids = fetch_matchids(api_key, puuid, game_count_position, number_of_games_per_batch)
        matchids = [matchid for matchid in matchids if matchid not in matchids_in_database]
        if not matchids:
            break
        # Prepare empty batch lists before collecting the current round of data.
        batch_match_tuples = []
        batch_player_tuples = []
        batch_match_participant_tuples = []
        batch_participant_item_tuples = []
        for matchid in matchids:
            match_data = fetch_match_data(matchid, api_key)
            if not match_data:
                continue
            match_tuple, player_tuples, match_participant_tuples, participant_item_tuples = parse_match_tuples(match_data)

            batch_match_tuples.append(match_tuple)
            batch_player_tuples.extend(player_tuples)
            batch_match_participant_tuples.extend(match_participant_tuples)
            batch_participant_item_tuples.extend(participant_item_tuples)

        logging.info(f"Atempting to send current batch of {len(batch_match_tuples)} matches to the database." )
        logging.info(f"Upserting players table")
        my_pipeline.upsert_players_table(batch_player_tuples)
        logging.info(f"Upserting matches table")
        my_pipeline.upsert_matches_table(batch_match_tuples)
        logging.info(f"Upserting match participants table")
        my_pipeline.upsert_match_participants_table(batch_match_participant_tuples)
        logging.info(f"Upserting participant items")
        my_pipeline.upsert_participant_items_table(batch_participant_item_tuples)
        logging.info(f"Committing batch to database")
        my_pipeline.commit()
        logging.info('Batch sent!')
        game_count_position += number_of_games_per_batch
        if not entire:
            break

def send_entire_history(list_of_players):
    """Process the full match history for each player in the provided list."""
    for player in list_of_players:
        puuid = fetch_puuid(api_key, player[0], player[1])
        logging.info(f"Getting {player[0]}'s entire match history")
        send_match_info(puuid, True)
        my_pipeline.update_player_as_tracked(puuid)

load_dotenv()
api_key = os.getenv("RIOT_API_KEY")
driver = os.getenv("DB_DRIVER")
server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")

my_pipeline = database_pipeline.database_pipeline(driver, server, database, username, password)
my_pipeline.connect()

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
                   ('Optimusbrown', '7674'),
                   ('GreyAr3a', '4697'),
                   ('tailedbeastsky', 'b3wbs'),
                   ('Phoon', 'Boo'),
                   ('roelaid','NA1'),
                   ('cloud', '9927')]

update_static_data()
send_entire_history(list_of_players)
logging.info("All selected players match histories have been processed and stored in the database")

for i in range(50):
    puuid = my_pipeline.get_puuid()
    send_match_info(puuid)

my_pipeline.disconnect()