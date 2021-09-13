import json
from airtable import Airtable


class Game:
    def __init__(
        self,
        game_date,
        map_name,
        team_info,
        team1_rounds,
        team2_rounds,
        agents,
        assists,
        acss,
        kds,
    ):
        self.game_date = game_date
        self.map_name = map_name
        self.team_info = team_info
        self.team1_rounds = team1_rounds
        self.team2_rounds = team2_rounds

        self.agents = agents
        self.assists = assists
        self.acss = acss
        self.kds = kds

    def __str__(self):
        return f"{self.team_info['team1']} vs. {self.team_info['team2']} on {self.map_name}"

    def to_vector(self):
        out = [
            self.game_date,
            self.map_name,
            self.team_info["team1"],
            self.team_info["team2"],
            self.team_info["team1_abbrev"],
            self.team_info["team2_abbrev"],
            self.team1_rounds,
            self.team2_rounds,
        ]

        team1_players = self.team_info["team1_players"]
        team2_players = self.team_info["team2_players"]
        all_players = team1_players + team2_players
        out += all_players

        out += [self.assists[player] for player in all_players]
        out += [self.acss[player] for player in all_players]

        kds_vec = []
        for player1 in team1_players:
            for player2 in team2_players:
                kds_vec.append(self.kds[player1][player2]["kills"])
                kds_vec.append(self.kds[player1][player2]["deaths"])
        out += kds_vec

        return out

    def get_or_insert_players(self, players_table):
        player_at_id_map = {}

        team1_at_ids = []
        for player in self.team_info["team1_players"]:
            entry = players_table.match("Name", player)
            if not entry:
                entry = players_table.insert({"Name": player})
            at_id = entry["id"]
            team1_at_ids.append(at_id)
            player_at_id_map[player] = at_id

        team2_at_ids = []
        for player in self.team_info["team2_players"]:
            entry = players_table.match("Name", player)
            if not entry:
                entry = players_table.insert({"Name": player})
            at_id = entry["id"]
            team2_at_ids.append(at_id)
            player_at_id_map[player] = at_id

        return team1_at_ids, team2_at_ids, player_at_id_map

    def find_existing_game(self, games_table):
        date_str = self.game_date.split()[0]
        day_entries = games_table.search("Date Str", date_str)
        existing_entry = [
            x
            for x in day_entries
            if x["fields"]["Team 1"] == self.team_info["team1"]
            and x["fields"]["Team 2"] == self.team_info["team2"]
            and x["fields"]["Map"] == self.map_name
        ]

        return len(existing_entry) > 0

    def insert_game(self, games_table, team1_at_ids, team2_at_ids):
        date_str = self.game_date.split()[0]
        entry = {
            "Team 1": self.team_info["team1"],
            "Team 2": self.team_info["team2"],
            "Map": self.map_name,
            "Date": date_str,
            "Date Str": date_str,
            "Team 1 Abbrev": self.team_info["team1_abbrev"],
            "Team 2 Abbrev": self.team_info["team2_abbrev"],
            "Team 1 Rounds": self.team1_rounds,
            "Team 2 Rounds": self.team2_rounds,
            "Team 1 Players": team1_at_ids,
            "Team 2 Players": team2_at_ids,
        }

        print(entry)
        inserted_entry = games_table.insert(entry)
        return inserted_entry["id"]

    def insert_player_map_info(self, map_info_table, game_at_id, player_at_id_map):
        to_insert = []
        for player in self.team_info["team1_players"]:
            entry = {
                "Game": [game_at_id],
                "Player": [player_at_id_map[player]],
                "Agent": self.agents[player],
                "Assists": self.assists[player],
                "ACS": self.acss[player],
            }
            to_insert.append(entry)
        for player in self.team_info["team2_players"]:
            entry = {
                "Game": [game_at_id],
                "Player": [player_at_id_map[player]],
                "Agent": self.agents[player],
                "Assists": self.assists[player],
                "ACS": self.acss[player],
            }
            to_insert.append(entry)

        map_info_table.batch_insert(to_insert)

    def insert_kds(self, kd_table, game_at_id, player_at_id_map):
        to_insert = []
        for player1 in self.team_info["team1_players"]:
            for player2 in self.team_info["team2_players"]:
                entry = {
                    "Game": [game_at_id],
                    "Team 1 Player": [player_at_id_map[player1]],
                    "Team 2 Player": [player_at_id_map[player2]],
                    "Kills": self.kds[player1][player2]["kills"],
                    "Deaths": self.kds[player1][player2]["deaths"],
                }
                to_insert.append(entry)

        kd_table.batch_insert(to_insert)

    def to_airtable(self):
        with open("config.json") as f:
            config = json.load(f)
            base_key = config["base_key"]
            api_key = config["api_key"]

        games_table = Airtable(base_key, "Games", api_key)
        players_table = Airtable(base_key, "Players", api_key)
        map_info_table = Airtable(base_key, "Player Map Info", api_key)
        kd_table = Airtable(base_key, "Map KDs", api_key)

        if not self.find_existing_game(games_table):
            team1_at_ids, team2_at_ids, player_at_id_map = self.get_or_insert_players(
                players_table
            )
            game_at_id = self.insert_game(games_table, team1_at_ids, team2_at_ids)
            self.insert_player_map_info(map_info_table, game_at_id, player_at_id_map)
            self.insert_kds(kd_table, game_at_id, player_at_id_map)
