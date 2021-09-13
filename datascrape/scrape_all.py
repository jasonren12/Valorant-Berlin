import requests
from lxml import etree, html
from io import StringIO
from collections import defaultdict
import json

from scrape_game import scrape_match, iterate_from_bfs, print_single_node


def find_match_nodes(root):
    out = []
    q = [root]
    while q:
        node = q.pop(0)
        node_class = node.attrib.get("class", None)
        node_href = node.attrib.get("href", None)
        if node_class and node_class.startswith("wf-module-item") and node_href:
            out.append(node)

        for child in node:
            q.append(child)

    print(f"Found {len(out)} matches")

    return out


def scrape_team(team_name, team_id):
    team_matches_url = f"https://www.vlr.gg/team/matches/{team_id}/{team_name}/"
    page = requests.get(team_matches_url)
    root = html.fromstring(page.content)
    match_nodes = find_match_nodes(root)

    all_games = []
    for node in match_nodes:
        match_url = f"https://www.vlr.gg{node.attrib['href']}"
        print("Starting scrape on", match_url)
        all_games.extend(scrape_match(match_url))
        print("DONE\n")

    print(f"Scraped {len(all_games)} games for {team_name}")
    return all_games


if __name__ == "__main__":
    with open("metadata/vlr_teams.json") as f:
        all_teams = json.load(f)

    for region, region_teams in all_teams.items():
        for team_name, team_id in region_teams.items():
            team_games = scrape_team(team_name, team_id)

            for i, game in enumerate(team_games):
                print(f"Writing game {i} out of {len(team_games)} to file.")
                with open(f"datasets/{region}_dataset.txt", "a+") as f:
                    f.write(str(game.to_vector()))
                    f.write("\n")
