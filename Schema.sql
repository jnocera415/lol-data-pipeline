DROP TABLE IF EXISTS participant_items;
DROP TABLE IF EXISTS item_tags;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS match_participants;
DROP TABLE IF EXISTS champion_tags;
DROP TABLE IF EXISTS champions;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS players;


CREATE TABLE players (
  puuid varchar(78) PRIMARY KEY,
  gamename nvarchar(23),
  tagline nvarchar(5),
  track_history BIT,
  last_date_processed DATE
  );
  
CREATE TABLE matches (
  matchid varchar(14) PRIMARY KEY,
  match_time bigint, 
  duration float,
  gamemode varchar(32),
  gameversion varchar(30)
  );
  
CREATE TABLE champions (
  championid INT PRIMARY KEY,
  champion_name nvarchar(50),
  champion_title varchar(100)
  );
  
Create TABLE champion_tags (
  championid INT REFERENCES champions(championid),
  champion_tag varchar(20)
  );
  
Create TABLE match_participants (
  participantid varchar(92) PRIMARY KEY, --participantid is matchid and playerid concatenated 
  puuid varchar(78) REFERENCES players(puuid),
  matchid varchar(14) REFERENCES matches(matchid),
  championid INT REFERENCES champions(championid),
  lane varchar(10),
  gold_earned INT,
  damage_dealt_to_champions INT,
  total_healing INT,
  kills INT,
  Deaths INT,
  Assists INT,
  Win BIT
  );
 
CREATE TABLE items(
  itemid INT PRIMARY KEY,
  item_name varchar(150),
  gold_cost INT
  );

CREATE TABLE item_tags(
  itemid INT REFERENCES items(itemid),
  item_tag varchar(20)
  );
  
CREATE TABLE participant_items(
  participantid varchar(92) REFERENCES match_participants(participantid),
  itemid INT REFERENCES items(itemid),
  item_slot INT
  );
