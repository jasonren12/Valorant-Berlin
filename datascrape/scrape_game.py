import requests
from lxml import etree, html
from io import StringIO
from collections import defaultdict
import json

from game import Game

STAT_NODES = ["vm-stats-game ", "vm-stats-game mod-active"]
MAPS_TEAMS_NODE = ["match-header-note"]
DATE_NODE = ["match-header-date"]


def print_single_node(node, level=None):
    if level:
        print(f"Level {level}")
    print(f"Tag: {node.tag}, Attribs: {node.attrib}")
    if node.text:
        print(f"Text: {node.text.strip()}")
    print()


def iterate_from_bfs(node, print_nodes=False):
    track = [(node, 0)]
    q = [(node, 0)]
    while q:
        next_node, level = q.pop(0)
        if print_nodes:
            print_single_node(next_node, level)
        for child in next_node:
            q.append((child, level + 1))
            track.append((child, level + 1))

    return track


def find_nodes(node_names, root):
    out = []
    q = [root]
    while q:
        node = q.pop(0)
        node_class = node.attrib.get("class", None)
        if node_class and node_class in node_names:
            out.append(node)

        for child in node:
            q.append(child)

    print(f"Found {len(out)} nodes searching {node_names}")

    return out


def get_date(overview_root):
    date_node = find_nodes(DATE_NODE, overview_root)[0]
    date_nodes = iterate_from_bfs(date_node, False)
    game_date = date_nodes[1][0].attrib["data-utc-ts"]
    return game_date


def get_kds(kd_container_node):

    nodes = iterate_from_bfs(kd_container_node, False)
    stat_nodes = [x[0] for x in nodes if x[1] == 6]

    team_nodes = [x[0] for x in nodes if x[1] == 7]
    team2 = team_nodes[0].text.strip()
    team1 = team_nodes[5].text.strip()

    team1_names = []
    team2_names = []

    for i in range(1, 11, 2):
        team2_names.append(stat_nodes[i].text.strip())

    for i in range(11, 80, 17):
        team1_names.append(stat_nodes[i].text.strip())

    start = 11
    team1_idx = 0
    team2_idx = 0
    kds = {t1: {t2: None for t2 in team2_names} for t1 in team1_names}
    while team1_idx < 5:
        # 10 for team2 names, 2 for initial team1 name in row
        start = 10 + team1_idx * 17 + 2
        for i in range(start, start + 15, 3):
            team2_idx = (i - start) // 3
            team1_player = team1_names[team1_idx]
            team2_player = team2_names[team2_idx]

            try:
                kills = int(stat_nodes[i].text.strip())
            except ValueError as e:
                kills = 0
            try:
                deaths = int(stat_nodes[i + 1].text.strip())
            except ValueError as e:
                deaths = 0

            kds[team1_player][team2_player] = {"kills": kills, "deaths": deaths}

        team1_idx += 1

    return kds


def get_meta(container_node):
    nodes = iterate_from_bfs(container_node, False)
    meta_nodes = [x[0] for x in nodes if x[1] == 4]

    second_team_idx = [
        i for i, x in enumerate(meta_nodes) if x.attrib.get("class", "") == "team-name"
    ][1]
    map_name = meta_nodes[second_team_idx - 1].text.strip()
    team1 = meta_nodes[0].text.strip()
    team2 = meta_nodes[second_team_idx].text.strip()

    score_nodes = [
        x[0] for x in nodes if x[1] == 3 and "score" in x[0].attrib.get("class", "")
    ]
    team1_rounds = int(score_nodes[0].text.strip())
    team2_rounds = int(score_nodes[1].text.strip())

    player_nodes = [x[0] for x in nodes if x[1] == 9]
    team1_abbrev = player_nodes[1].text.strip()
    team2_abbrev = player_nodes[16].text.strip()

    meta = {
        "map_name": map_name,
        "team1": team1,
        "team2": team2,
        "team1_abbrev": team1_abbrev,
        "team2_abbrev": team2_abbrev,
        "team1_rounds": team1_rounds,
        "team2_rounds": team2_rounds,
    }

    return meta


def get_player_map_stats(container_node):

    nodes = iterate_from_bfs(container_node, False)

    table_nodes = [x[0] for x in nodes if x[1] == 7]
    stat_nodes = [x for x in table_nodes if "stats-sq" in x.attrib.get("class", "")]

    kills = []
    kill_idxs = range(1, 101, 10)
    for i in kill_idxs:
        kills.append(int(stat_nodes[i].text.strip()))

    deaths = []
    death_idxs = range(2, 102, 10)
    for i in death_idxs:
        death_nodes = iterate_from_bfs(stat_nodes[i], False)
        deaths.append(int(death_nodes[2][0].text.strip()))

    assists = []
    assist_idxs = range(3, 103, 10)
    for i in assist_idxs:
        assists.append(int(stat_nodes[i].text.strip()))

    acss = []
    acs_idxs = range(0, 100, 10)
    for i in acs_idxs:
        acss.append(int(stat_nodes[i].text.strip()))

    player_nodes = [x[0] for x in nodes if x[1] == 9]

    map_player_order = []
    player_info = defaultdict(dict)
    for i in range(0, 30, 3):
        player = player_nodes[i].text.strip()
        team = player_nodes[i + 1].text.strip()
        agent = player_nodes[i + 2].attrib["title"]
        map_player_order.append(player)
        player_info[player]["team"] = team
        player_info[player]["agent"] = agent
        player_num = i // 3
        player_info[player]["kills"] = kills[player_num]
        player_info[player]["deaths"] = deaths[player_num]
        player_info[player]["assists"] = assists[player_num]
        player_info[player]["acs"] = acss[player_num]

    return player_info


def print_kd_dict(kd):
    for (player1, player2), stats in kd.items():
        print(f"{player1} vs {player2}: {stats}")


def scrape_match(base_url):
    base_url = base_url + "/?game=all&tab="
    overview_url = base_url + "overview"
    overview_page = requests.get(overview_url)
    overview_root = html.fromstring(overview_page.content)
    overview_container_nodes = find_nodes(STAT_NODES, overview_root)

    performance_url = base_url + "performance"
    performance_page = requests.get(performance_url)
    performance_root = html.fromstring(performance_page.content)
    performance_container_nodes = find_nodes(STAT_NODES, performance_root)

    zipped_nodes = []
    for onode in overview_container_nodes:
        game_id = onode.attrib["data-game-id"]
        if game_id == "all":
            continue

        pnode = [
            x
            for x in performance_container_nodes
            if x.attrib["data-game-id"] == game_id
        ][0]
        zipped_nodes.append((onode, pnode))

    game_date = get_date(overview_root)
    games = []
    for onode, pnode in zipped_nodes:
        try:
            meta = get_meta(onode)
            player_map_stats = get_player_map_stats(onode)
            kds = get_kds(pnode)
        except Exception as e:
            print(f"Error scraping {base_url}: {e}")
            continue

        team1_abbrev = meta["team1_abbrev"]
        team2_abbrev = meta["team2_abbrev"]
        team1_players = [
            player
            for player, info in player_map_stats.items()
            if info["team"] == team1_abbrev
        ]
        team2_players = [
            player
            for player, info in player_map_stats.items()
            if info["team"] == team2_abbrev
        ]

        if set(team1_players) != set(kds.keys()) or set(team2_players) != set(
            list(kds.values())[0].keys()
        ):
            print("Warning, might be a >5 man roster, skipping.")
            # TODO: finish this for more complete data
            # impute_kds(player_map_stats, kds, team1_players, team2_players)
            continue

        assists = {
            player: player_info["assists"]
            for player, player_info in player_map_stats.items()
        }
        acss = {
            player: player_info["acs"]
            for player, player_info in player_map_stats.items()
        }
        agents = {
            player: player_info["agent"]
            for player, player_info in player_map_stats.items()
        }

        game = Game(
            game_date=game_date,
            map_name=meta["map_name"],
            team_info={
                "team1": meta["team1"],
                "team2": meta["team2"],
                "team1_abbrev": team1_abbrev,
                "team2_abbrev": team2_abbrev,
                "team1_players": team1_players,
                "team2_players": team2_players,
            },
            team1_rounds=meta["team1_rounds"],
            team2_rounds=meta["team2_rounds"],
            agents=agents,
            assists=assists,
            acss=acss,
            kds=kds,
        )
        games.append(game)

    return games


def impute_kds(player_map_stats, kds, team1_players, team2_players):
    pass
    # truth_players = player_map_stats.keys()
    # benched_players = []
    # tot_kills_and_deaths = defaultdict(int)
    # for player1, kds1 in kds.items():
    #     for player2, pair_kd in kds1.items():
    #         kills_and_deaths = pair_kd["kills"] + pair_kd["deaths"]
    #         tot_kills_and_deaths[player1] += kills_and_deaths
    #         tot_kills_and_deaths[player2] += kills_and_deaths
