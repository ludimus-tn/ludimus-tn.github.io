#!/usr/bin/env python3
"""
Script to fetch games data from Ludidash API and convert it to games.json format.
Enriches data with BoardGameGeek API information.
"""
import json
import os
import sys
import time
from pathlib import Path
import requests
import xml.etree.ElementTree as ET


def load_env_vars():
    """Load environment variables from .envrc file."""
    envrc_path = Path(__file__).parent.parent / ".envrc"
    
    if not envrc_path.exists():
        print("Error: .envrc file not found", file=sys.stderr)
        sys.exit(1)
    
    env_vars = {}
    with open(envrc_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]  # Remove "export "
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value
    
    return env_vars


def fetch_games_data(endpoint, token):
    """Fetch games data from the API."""
    # The endpoint variable contains the base URL
    # We need to construct the full URL for /items/giochi
    url = f"{endpoint}/items/giochi"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "limit": 1000
    }
    
    print(f"Fetching data from: {url}")
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_bgg_data(game_id, cache):
    """Fetch game data from BoardGameGeek API with caching."""
    # Check cache first
    if game_id in cache:
        return cache[game_id]
    
    try:
        # Add delay to respect BGG API rate limits
        time.sleep(1)
        
        # Fetch game data from BGG XML API
        url = f"https://boardgamegeek.com/xmlapi2/thing?id={game_id}&stats=1"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        print(response.text)
        
        # Parse XML response
        root = ET.fromstring(response.content)
        item = root.find('item')
        
        if item is None:
            print(f"\nWarning: BGG returned no data for game ID {game_id}", file=sys.stderr)
            return {
                "rankBGG": None,
                "autore": None,
                "votoMedio": None,
                "numeroVoti": None,
                "annoPubblicazione": None
            }
        
        # Extract designer(s)
        designers = []
        for link in item.findall(".//link[@type='boardgamedesigner']"):
            designers.append(link.get('value'))
        designer_str = ", ".join(designers) if designers else None
        
        # Extract year published
        year_elem = item.find('yearpublished')
        year = int(year_elem.get('value')) if year_elem is not None and year_elem.get('value') else None
        
        # Extract ratings
        statistics = item.find('.//statistics')
        ratings = statistics.find('.//ratings') if statistics is not None else None
        
        rating_average = None
        users_rated = None
        if ratings is not None:
            avg_elem = ratings.find('average')
            if avg_elem is not None and avg_elem.get('value'):
                try:
                    rating_average = round(float(avg_elem.get('value')), 5)
                except (ValueError, TypeError):
                    pass
            
            users_elem = ratings.find('usersrated')
            if users_elem is not None and users_elem.get('value'):
                try:
                    users_rated = int(users_elem.get('value'))
                except (ValueError, TypeError):
                    pass
        
        # Extract boardgame rank
        rank = None
        if ratings is not None:
            for rank_elem in ratings.findall('.//rank'):
                if rank_elem.get('name') == 'boardgame' and rank_elem.get('value') not in ['Not Ranked', None]:
                    try:
                        rank = int(rank_elem.get('value'))
                    except (ValueError, TypeError):
                        pass
        
        bgg_data = {
            "rankBGG": rank,
            "autore": designer_str,
            "votoMedio": rating_average,
            "numeroVoti": users_rated,
            "annoPubblicazione": year
        }
        
        # Cache the result
        cache[game_id] = bgg_data
        return bgg_data
        
    except requests.exceptions.RequestException as e:
        print(f"\nWarning: HTTP error fetching BGG data for game {game_id}: {e}", file=sys.stderr)
        return {
            "rankBGG": None,
            "autore": None,
            "votoMedio": None,
            "numeroVoti": None,
            "annoPubblicazione": None
        }
    except Exception as e:
        print(f"\nWarning: Could not parse BGG data for game {game_id}: {e}", file=sys.stderr)
        return {
            "rankBGG": None,
            "autore": None,
            "votoMedio": None,
            "numeroVoti": None,
            "annoPubblicazione": None
        }


def transform_game(game, bgg_data=None):
    """Transform a game object from API format to games.json format."""
    # Format player count
    min_p = game.get("min_players")
    max_p = game.get("max_players")
    num_giocatori = ""
    if min_p is not None or max_p is not None:
        num_giocatori = f"Min:{min_p if min_p is not None else '?'} - Max:{max_p if max_p is not None else '?'}"
    
    # Base game data
    game_obj = {
        "idBGG": int(game.get("bgg")) if game.get("bgg") else -1,
        # "rankBGG": None,
        "nomeGioco": game.get("titolo", ""),
        # "autore": None,
        # "votoMedio": None,
        "pesoMedio": game.get("complexity"),
        # "numeroVoti": None,
        "proprietari": game.get("dove", ""),
        "numGiocatori": num_giocatori,
        # "annoPubblicazione": None,
        "durata": game.get("average_duration"),
        "thumbnail": game.get("thumb", "")
    }
    
    # Merge BGG data if available
    if bgg_data:
        game_obj.update(bgg_data)
    
    return game_obj


def main():
    """Main function to fetch and transform games data."""
    # Load environment variables
    env_vars = load_env_vars()
    token = env_vars.get("LUDIDASH_TOKEN")
    endpoint = env_vars.get("LUDIDASH_ENDPOINT")
    
    if not token or not endpoint:
        print("Error: Missing LUDIDASH_TOKEN or LUDIDASH_ENDPOINT in .envrc", file=sys.stderr)
        sys.exit(1)
    
    # Fetch data from API
    api_response = fetch_games_data(endpoint, token)
    
    # Extract the data array (API returns {"data": [...]})
    games_data = api_response.get("data", [])
    
    if not games_data:
        print("Warning: No games data found in API response", file=sys.stderr)
    
    # Initialize BGG cache
    print("Initializing BoardGameGeek cache...")
    bgg_cache = {}
    
    # Transform each game and enrich with BGG data
    # print(f"Enriching {len(games_data)} games with BGG data...")
    
    # transformed_games = []
    # for idx, game in enumerate(games_data):
    #     bgg_id = game.get("bgg")
    #     bgg_data = None
    #     
    #     # Fetch BGG data if the game has a BGG ID
    #     # if bgg_id:
    #     #     try:
    #     #         bgg_data = fetch_bgg_data(int(bgg_id), bgg_cache)
    #     #     except Exception as e:
    #     #         print(f"\nError fetching BGG data for {game.get('titolo')}: {e}", file=sys.stderr)
    #     
    #     transformed_games.append(transform_game(game, bgg_data))
    #     
    #     # Print progress every 10 games
    #     if (idx + 1) % 10 == 0 or (idx + 1) == len(games_data):
    #         print(f"  Progress: {idx + 1}/{len(games_data)} games processed")
    
    transformed_games = [transform_game(game) 
                         for game in games_data
                         if game.get("dove") != "venduti"]
    # Sort by BGG ID
    transformed_games.sort(key=lambda x: x.get("idBGG") or 0)
    
    # Create output structure
    output = {
        "items": transformed_games
    }
    
    # Write to games.json
    output_path = Path(__file__).parent / "games.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully wrote {len(transformed_games)} games to {output_path}")


if __name__ == "__main__":
    main()
