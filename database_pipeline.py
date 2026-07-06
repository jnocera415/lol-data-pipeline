import pyodbc
import re
import time
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class database_pipeline:
    """Handles SQL Server connections and bulk upserts for pipeline data."""

    def __init__(self, driver, server, database, username, password):
        self.driver = driver
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.connected = False

    def handle_error(self, e):
        """Convert pyodbc errors into readable log messages and retry behavior."""
        error_code = e.args[0]
        error_explained = e.args[1] if len(e.args) > 1 else str(e)
        match error_code:
            case '08001':
                self.connected = False
                logging.error("Timeout Error Connecting to the database. Waiting 10 seconds and trying again after")
                time.sleep(10)
                return True
            case 'HY000' | '42000':
                self.connected = False
                logging.error(f"Database connection error. Retrying after 10 seconds.")
                time.sleep(10)
                return True 
            case _:      
                clean_message = re.sub(r"\[.*?\]", "", error_explained).strip()
                clean_message = re.sub(r"\s*\(\d+\)\s*\(SQLExec.*\)", "", clean_message).strip()
                logging.error(f"{error_code} {clean_message}" )
                return False

    def connect(self):
        """Connect to SQL Server with a few retry attempts for transient failures."""
        retries = 5
        attempt = 0
        connection_string = (
            f"Driver={self.driver};"
            f"Server={self.server},1433;"
            f"Database={self.database};"
            f"Uid={self.username};"
            f"Pwd={self.password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )
        while attempt < retries:
            try:
                self.conn = pyodbc.connect(connection_string, timeout=60)
                self.connected = True
                logging.info("Successfully connected to the database.")
                return
            except pyodbc.Error as e:
                self.connected = False
                if not self.handle_error(e):
                    break
            attempt += 1
            logging.info(f"Retrying connection... Attempt {attempt}/{retries}")
        logging.error("Failed to connect to the database after multiple attempts.")

    def disconnect(self):
        if self.connected:
            self.conn.close()
            self.connected = False
            logging.info("Database connection closed.")

    def upsert_items_table(self, item_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            # Create a temporary staging table for the incoming item data.
            insert_first_query = """
            DROP TABLE IF EXISTS #TempItems;

            CREATE TABLE #TempItems (
                itemid INT PRIMARY KEY,
                item_name NVARCHAR(200),
                gold_cost INT
            )
            """
            cursor.execute(insert_first_query)

            # Load the staged rows into the temporary table.
            insert_temp_query = "INSERT INTO #TempItems (itemid, item_name, gold_cost) VALUES (?, ?, ?)"
            cursor.executemany(insert_temp_query, item_tuples)

            # Insert only rows that are not already present in the target table.
            insert_final_query = """
            INSERT INTO ITEMS (itemid, item_name, gold_cost)
            SELECT t.itemid, t.item_name, t.gold_cost
            FROM #TempItems t
            LEFT JOIN ITEMS i ON t.itemid = i.itemid
            WHERE i.itemid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_item_tags_table(self, item_tag_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempItem_Tags;

            CREATE TABLE #TempItem_Tags (
                itemid INT,
                item_tag NVARCHAR(200)
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = "INSERT INTO #TempItem_Tags (itemid, item_tag) VALUES (?, ?)"
            cursor.executemany(insert_temp_query, item_tag_tuples)

            insert_final_query = """
            INSERT INTO ITEM_TAGS (itemid, item_tag)
            SELECT t.itemid, t.item_tag
            FROM #TempItem_Tags t
            LEFT JOIN ITEM_TAGS it ON t.itemid = it.itemid AND t.item_tag = it.item_tag
            WHERE it.itemid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_champions_table(self, champion_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempChampions;

            CREATE TABLE #TempChampions (
                championid INT PRIMARY KEY,
                champion_name NVARCHAR(200),
                champion_title NVARCHAR(200)
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = "INSERT INTO #TempChampions (championid, champion_name, champion_title) VALUES (?, ?, ?)"
            cursor.executemany(insert_temp_query, champion_tuples)

            insert_final_query = """
            INSERT INTO CHAMPIONS (championid, champion_name, champion_title)
            SELECT t.championid, t.champion_name, t.champion_title
            FROM #TempChampions t
            LEFT JOIN CHAMPIONS c ON t.championid = c.championid
            WHERE c.championid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_champion_tags_table(self, champion_tag_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempChampion_Tags;

            CREATE TABLE #TempChampion_Tags (
                championid INT,
                champion_tag NVARCHAR(200)
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = "INSERT INTO #TempChampion_Tags (championid, champion_tag) VALUES (?, ?)"
            cursor.executemany(insert_temp_query, champion_tag_tuples)

            insert_final_query = """
            INSERT INTO CHAMPION_TAGS (championid, champion_tag)
            SELECT t.championid, t.champion_tag
            FROM #TempChampion_Tags t
            LEFT JOIN CHAMPION_TAGS ct ON t.championid = ct.championid AND t.champion_tag = ct.champion_tag
            WHERE ct.championid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
    
    def upsert_queue_ids_table(self, queue_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempQueue_Ids;

            CREATE TABLE #TempQueue_Ids (
                queueid INT PRIMARY KEY,
                queue_name NVARCHAR(100),
                queue_description NVARCHAR(500)
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = "INSERT INTO #TempQueue_Ids (queueid, queue_name, queue_description) VALUES (?, ?, ?)"
            cursor.executemany(insert_temp_query, queue_tuples)

            insert_final_query = """
            INSERT INTO QUEUE_IDS (queueid, queue_name, queue_description)
            SELECT t.queueid, t.queue_name, t.queue_description
            FROM #TempQueue_Ids t
            LEFT JOIN QUEUE_IDS q ON t.queueid = q.queueid
            WHERE q.queueid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_players_table(self, player_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempPlayers;

            CREATE TABLE #TempPlayers (
                puuid VARCHAR(78) PRIMARY KEY,
                gamename NVARCHAR(23),
                tagline NVARCHAR(5),
                track_history BIT,
                last_date_processed DATE
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = "INSERT INTO #TempPlayers (puuid, gamename, tagline, track_history, last_date_processed) VALUES (?, ?, ?, ?, ?)"
            formatted_data = list({p[0]: p + (None,) for p in player_tuples}.values())
            cursor.executemany(insert_temp_query, formatted_data)

            insert_final_query = """
            MERGE PLAYERS AS target
            USING #TempPlayers AS source
            ON (target.puuid = source.puuid)

            WHEN MATCHED AND (target.gamename <> source.gamename OR target.tagline <> source.tagline) THEN
            UPDATE SET 
            target.gamename = source.gamename,
            target.tagline = source.tagline

            WHEN NOT MATCHED THEN
            INSERT (puuid, gamename, tagline, track_history, last_date_processed)
            VALUES (source.puuid, source.gamename, source.tagline, source.track_history, source.last_date_processed);
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_matches_table(self, match_tuples):
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempMatches;

            CREATE TABLE #TempMatches (
                matchid varchar(14) PRIMARY KEY,
                match_time BIGINT,
                duration float,
                queueid varchar(32),
                gameversion varchar(30)
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = """
            INSERT INTO #TempMatches (matchid, match_time, duration, queueid, gameversion)
            VALUES (?, ?, ?, ?, ?)
            """
            formatted_data = list(match_tuples)
            cursor.executemany(insert_temp_query, formatted_data)

            insert_final_query = """
            INSERT INTO MATCHES (matchid, match_time, duration, queueid, gameversion)
            SELECT t.matchid, t.match_time, t.duration, t.queueid, t.gameversion
            FROM #TempMatches t
            LEFT JOIN MATCHES m ON t.matchid = m.matchid
            WHERE m.matchid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
    def get_puuid(self):
        """Return one player whose history needs to be refreshed."""
        cursor = self.conn.cursor()
        current_date = datetime.now()
        try:
            query = """
            SELECT TOP 1 puuid FROM PLAYERS 
            WHERE last_date_processed IS NULL
            OR DATEDIFF(day, last_date_processed, ?) > 10
            """
            cursor.execute(query, (current_date,))
            row = cursor.fetchone()
            return row.puuid if row else None
        except pyodbc.Error as e:
            self.handle_error(e)
            return None
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def get_match_ids_by_puuid(self, puuid):
        """Fetch match IDs for a player and mark that player as recently processed."""
        cursor = self.conn.cursor()
        try:
            query = """
            SELECT DISTINCT m.matchid
            FROM MATCHES m
            JOIN MATCH_PARTICIPANTS mp ON m.matchid = mp.matchid
            WHERE mp.puuid = ?
            """
            cursor.execute(query, puuid)
            matchids =  [row.matchid for row in cursor.fetchall()]
            query = """
            UPDATE PLAYERS
            SET last_date_processed = ?
            WHERE PUUID = ?
            """
            current_date = datetime.now()
            cursor.execute(query, current_date, puuid)
            self.commit()
            return matchids
        except pyodbc.Error as e:
            self.handle_error(e)
            return []
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_match_participants_table(self, match_participant_tuples):
        """Bulk insert participant rows into the staging table and merge new ones."""
        if not match_participant_tuples:
            return
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            # Create a temporary table for match participant data before merging.
            insert_first_query = """
            DROP TABLE IF EXISTS #TempMatch_Participants;

            CREATE TABLE #TempMatch_Participants (
                participantid varchar(92) PRIMARY KEY,
                puuid varchar(78),
                matchid varchar(14),
                championid INT,
                participant_role varchar(10),
                gold_earned INT,
                damage_dealt_to_champions INT,
                total_healing INT,
                kills INT,
                Deaths INT,
                Assists INT,
                Vision_Score INT,
                Win BIT
            )
            """
            cursor.execute(insert_first_query)
            # Load the participant rows into the temporary staging table.
            insert_temp_query = """
            INSERT INTO #TempMatch_Participants (
                participantid, puuid, matchid, championid, participant_role, gold_earned,
                damage_dealt_to_champions, total_healing, kills, deaths, assists, vision_score, win
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            formatted_data = list({mp[0]: mp for mp in match_participant_tuples}.values())
            cursor.executemany(insert_temp_query, formatted_data)
            # Insert only participants that are not already in the final table.
            insert_final_query = """
            INSERT INTO MATCH_PARTICIPANTS (
                participantid, puuid, matchid, championid, participant_role, gold_earned,
                damage_dealt_to_champions, total_healing, kills, deaths, assists, vision_score, win
            )
            SELECT
                t.participantid, t.puuid, t.matchid, t.championid, t.participant_role, t.gold_earned,
                t.damage_dealt_to_champions, t.total_healing, t.kills, t.deaths, t.assists, t.vision_score, t.win
            FROM #TempMatch_Participants t
            LEFT JOIN MATCH_PARTICIPANTS mp ON t.participantid = mp.participantid
            WHERE mp.participantid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def upsert_participant_items_table(self, participant_item_tuples):
        if not participant_item_tuples:
            return
        cursor = self.conn.cursor()
        try:
            cursor.fast_executemany = True

            insert_first_query = """
            DROP TABLE IF EXISTS #TempParticipant_Items;

            CREATE TABLE #TempParticipant_Items (
                participantid varchar(92),
                itemid INT,
                item_slot INT
            )
            """
            cursor.execute(insert_first_query)

            insert_temp_query = """
            INSERT INTO #TempParticipant_Items (participantid, itemid, item_slot)
            VALUES (?, ?, ?)
            """
            formatted_data = list(participant_item_tuples)
            cursor.executemany(insert_temp_query, formatted_data)

            insert_final_query = """
            INSERT INTO PARTICIPANT_ITEMS (participantid, itemid, item_slot)
            SELECT t.participantid, t.itemid, t.item_slot
            FROM #TempParticipant_Items t
            LEFT JOIN PARTICIPANT_ITEMS pi ON t.participantid = pi.participantid AND t.item_slot = pi.item_slot
            WHERE pi.participantid IS NULL
            """
            cursor.execute(insert_final_query)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
    def update_player_as_tracked(self, puuid):
        cursor = self.conn.cursor()
        try:
            query = """
            UPDATE PLAYERS
            SET track_history = 1
            WHERE PUUID = ?
            """
            cursor.execute(query, puuid)
            self.commit()
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass
    def update_player_processed_date(self, puuid):
        cursor = self.conn.cursor()
        try:
            query = """
            UPDATE PLAYERS
            SET track_history = ?
            WHERE PUUID = ?
            """
            current_date = datetime.datenow()
            print(current_date)
            cursor.execute(query, current_date, puuid)
        except pyodbc.Error as e:
            self.handle_error(e)
        finally:
            try:
                cursor.close()
            except Exception:
                pass

    def commit(self):
        self.conn.commit()
