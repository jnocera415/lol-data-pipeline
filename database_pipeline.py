import pyodbc 
import re

class database_pipeline:
    
    def __init__(self, driver, server, database, username, password):
        self.driver = driver
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.connected = False
        self.conn = None

    def _is_connection_error(self, e):
        if not e or not getattr(e, "args", None):
            return False

        error_code = str(e.args[0])
        return error_code in {"08S01", "08001", "08003", "08004", "HYT00", "HY010"}

    def handle_error(self, e):
        
        error_code = e.args[0]
        error_explained = e.args[1] if len(e.args) > 1 else str(e)
        clean_message = re.sub(r"\[.*?\]", "", error_explained).strip()
        clean_message = re.sub(r"\s*\(\d+\)\s*\(SQLExec.*\)", "", clean_message).strip()

        if self._is_connection_error(e):
            print("Connection lost or reset by the server. The next operation will try to reconnect.")
            self.disconnect()
            return

        print(f"Error code {error_code}")
        print(clean_message)
        print("")

    def connect(self):

        connection_string = (
            f"Driver={self.driver};"
            f"Server={self.server},1433;"
            f"Database={self.database};"
            f"Uid={self.username};"
            f"Pwd={self.password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
        )

        try:
            self.conn = pyodbc.connect(connection_string)
            self.connected = True
            print("Successfully connected to the database.")

        except pyodbc.Error as e:
            self.connected = False
            self.conn = None
            self.handle_error(e)

    def disconnect(self):

        if self.connected and self.conn is not None:
            try:
                self.conn.close()
            except pyodbc.Error:
                pass

            self.connected = False
            self.conn = None
            print("Database connection closed.")

        else:
            self.connected = False
            self.conn = None
            print("No active database connection to close.")

    def ensure_connection(self):

        if self.connected and self.conn is not None:
            try:
                with self.conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            except pyodbc.Error:
                self.disconnect()

        if not self.connected:
            print("Not connected to the database. Trying to connect...")
            self.connect()

        return self.connected

    def run_with_retry(self, operation_name, operation):

        for attempt in range(3):
            if not self.ensure_connection():
                print(f"Failed to connect to the database for {operation_name}.")
                return False

            try:
                operation()
                return True

            except pyodbc.Error as e:
                if not self._is_connection_error(e):
                    self.handle_error(e)
                    return False

                print(f"{operation_name} failed because the connection was dropped. Retry {attempt + 1}/3.")
                self.disconnect()

        return False

    def chunk_data(self, rows, batch_size=100):
        for index in range(0, len(rows), batch_size):
            yield rows[index:index + batch_size]

    def upsert_items_table(self, item_tuples):

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True
                
                insert_query = "INSERT INTO ITEMS (itemid, item_name, gold_cost) "
                insert_query += "SELECT ?, ?, ? "
                insert_query += "WHERE NOT EXISTS ( "
                insert_query += "   SELECT 1 FROM ITEMS WHERE itemid = ? "
                insert_query += ")"

                for batch in self.chunk_data(item_tuples, 100):
                    formatted_data = [
                        (item_id, item_name, gold_cost, item_id) for item_id, item_name, gold_cost in batch
                    ]
                    cursor.executemany(insert_query, formatted_data)

        self.run_with_retry("upserting items", run)
    
    def upsert_item_tags_table(self, item_tag_tuples):  

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True
                
                insert_query = "INSERT INTO ITEM_TAGS (itemid, item_tag) "
                insert_query += "SELECT ?, ? "
                insert_query += "WHERE NOT EXISTS ( "
                insert_query += "   SELECT 1 FROM ITEM_TAGS WHERE itemid = ? AND item_tag = ? "
                insert_query += ")"

                for batch in self.chunk_data(item_tag_tuples, 100):
                    formatted_data = [
                        (item_id, item_tag, item_id, item_tag) for item_id, item_tag in batch
                    ]
                    cursor.executemany(insert_query, formatted_data)

        self.run_with_retry("upserting item tags", run)
    
    def upsert_champions_table(self, champion_tuples):

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True
                
                insert_query = "INSERT INTO CHAMPIONS (championid, champion_name, champion_title) "
                insert_query += "SELECT ?, ?, ? "
                insert_query += "WHERE NOT EXISTS ( "
                insert_query += "   SELECT 1 FROM CHAMPIONS WHERE championid = ? "
                insert_query += ")"
                
                for batch in self.chunk_data(champion_tuples, 100):
                    formatted_data = [
                        (champion_id, champion_name, champion_title, champion_id) for champion_id, champion_name, champion_title in batch
                    ]
                    cursor.executemany(insert_query, formatted_data)

        self.run_with_retry("upserting champions", run)

    def upsert_champion_tags_table(self, champion_tag_tuples):

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True
                
                insert_query = "INSERT INTO CHAMPION_TAGS (championid, champion_tag) "
                insert_query += "SELECT ?, ? "
                insert_query += "WHERE NOT EXISTS ( "
                insert_query += "   SELECT 1 FROM CHAMPION_TAGS WHERE championid = ? AND champion_tag = ? "
                insert_query += ")"

                for batch in self.chunk_data(champion_tag_tuples, 100):
                    formatted_data = [
                        (champion_id, champion_tag, champion_id, champion_tag) for champion_id, champion_tag in batch
                    ]
                    cursor.executemany(insert_query, formatted_data)

        self.run_with_retry("upserting champion tags", run)

    def upsert_players_table(self, player_tuples):

        if not player_tuples:
            return

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True
                
                insert_first_query = """
                DROP TABLE IF EXISTS #TempPlayers;

                CREATE TABLE #TempPlayers (
                    puuid VARCHAR(78) PRIMARY KEY,
                    gamename NVARCHAR(16),
                    tagline NVARCHAR(5),
                    track_history BIT
                )
                """

                cursor.execute(insert_first_query)

                insert_temp_query = "INSERT INTO #TempPlayers (puuid, gamename, tagline, track_history) VALUES (?, ?, ?, ?)"
                
                formatted_data = list({p[0]: p for p in player_tuples}.values())

                cursor.executemany(insert_temp_query, formatted_data)

                insert_final_query = """
                INSERT INTO PLAYERS (puuid, gamename, tagline, track_history)
                SELECT t.puuid, t.gamename, t.tagline, t.track_history
                FROM #TempPlayers t
                LEFT JOIN PLAYERS p ON t.puuid = p.puuid
                WHERE p.puuid IS NULL
                """
                cursor.execute(insert_final_query)

        self.run_with_retry("upserting player tuples", run)

    def upsert_matches_table(self, match_tuples):

        if not match_tuples:
            return

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True

                insert_first_query = """
                DROP TABLE IF EXISTS #TempMatches;
                
                CREATE TABLE #TempMatches (
                    matchid varchar(14) PRIMARY KEY,
                    match_time BIGINT,
                    duration float,
                    gamemode varchar(20),
                    gameversion varchar(30)
                )
                """
                cursor.execute(insert_first_query)

                insert_temp_query = """
                INSERT INTO #TempMatches (matchid, match_time, duration, gamemode, gameversion) 
                VALUES (?, ?, ?, ?, ?)
                """
                formatted_data = match_tuples

                cursor.executemany(insert_temp_query, formatted_data)

                insert_final_query = """
                INSERT INTO MATCHES (matchid, match_time, duration, gamemode, gameversion)
                SELECT t.matchid, t.match_time, t.duration, t.gamemode, t.gameversion
                FROM #TempMatches t
                LEFT JOIN MATCHES m 
                    ON t.matchid = m.matchid 
                WHERE m.matchid IS NULL
                """

                cursor.execute(insert_final_query)

        self.run_with_retry("upserting matches", run)
    
    def upsert_match_participants_table(self, match_participant_tuples):

        if not match_participant_tuples:
            return

        def run():
            with self.conn.cursor() as cursor:
                cursor.fast_executemany = True

                insert_first_query = """
                DROP TABLE IF EXISTS #TempMatch_Participants

                Create TABLE #TempMatch_Participants (
                    participantid varchar(92) PRIMARY KEY,
                    puuid varchar(78),
                    matchid varchar(14),
                    championid INT,
                    lane varchar(10),
                    gold_earned INT,
                    damage_dealt_to_champions INT,
                    total_healing INT,
                    kills INT,
                    Deaths INT,
                    Assists INT,
                    Win BIT
                    )
                """
                cursor.execute(insert_first_query)

                insert_temp_query = """
                INSERT INTO #TempMatch_Participants (
                    participantid, puuid, matchid, championid, lane, gold_earned, 
                    damage_dealt_to_champions, total_healing, kills, deaths, assists, win
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """

                formatted_data = list({mp[0]: mp for mp in match_participant_tuples}.values())
                cursor.executemany(insert_temp_query, formatted_data)

                insert_final_query = """
                INSERT INTO MATCH_PARTICIPANTS (
                    participantid, puuid, matchid, championid, lane, gold_earned, 
                    damage_dealt_to_champions, total_healing, kills, deaths, assists, win
                )
                SELECT 
                    t.participantid, t.puuid, t.matchid, t.championid, t.lane, t.gold_earned, 
                    t.damage_dealt_to_champions, t.total_healing, t.kills, t.deaths, t.assists, t.win
                FROM #TempMatch_Participants t
                LEFT JOIN MATCH_PARTICIPANTS mp ON t.participantid = mp.participantid
                WHERE mp.participantid IS NULL
                """
                cursor.execute(insert_final_query)

        self.run_with_retry("upserting match participants", run)
    
    def upsert_participant_items_table(self, participant_item_tuples):

        if not participant_item_tuples:
            return

        def run():
            with self.conn.cursor() as cursor:
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
                formatted_data = participant_item_tuples

                cursor.executemany(insert_temp_query, formatted_data)

                insert_final_query = """
                INSERT INTO PARTICIPANT_ITEMS (participantid, itemid, item_slot)
                SELECT t.participantid, t.itemid, t.item_slot
                FROM #TempParticipant_Items t
                LEFT JOIN PARTICIPANT_ITEMS pi 
                    ON t.participantid = pi.participantid 
                    AND t.item_slot = pi.item_slot
                WHERE pi.participantid IS NULL
                """
                cursor.execute(insert_final_query)

        self.run_with_retry("upserting participant item data", run)

    def get_all_existing_matches(self):

        if not self.ensure_connection():
            print("Failed to connect to the database.")
            return

        try:

            with self.conn.cursor() as cursor:

                query = "SELECT matchid FROM MATCHES"
                cursor.execute(query)

                return set(row[0] for row in cursor.fetchall())

        except pyodbc.Error as e:
            
            print("Error has occured while getting all existing matches")
            self.handle_error(e)


    def commit(self):

        if not self.connected:
            print("No active database connection to commit.")
            return

        def run():
            self.conn.commit()

        self.run_with_retry("committing changes", run)