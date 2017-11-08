import csv
import time
from boardgamegeek import BoardGameGeek
import json

name = {
    'Ludimus': 'Ludimus',
    'Pufforrohk': 'Alessio',
    'Masnonet': 'Davide',
    'earendil02': 'Riccardo',
    'nostalgiaz': 'Mattia',
    'melachel': 'Stefano',
    'hina00': 'Sofia',
    'Leouz': 'Leonardo',
    'ResN91': 'Andrea'
}

bgg = BoardGameGeek()

header = [
    "Id", "BGG rank", "Name", "Url", "Playing time", "Players", "Rating", "Users rated", "Weight", "NumOwners",
    "Owners", "Image"
]


def create_line(pair):
    time.sleep(1)
    id, owners = pair
    try:
        game = bgg.game(game_id=id)
        print(game.name)
    except:
        print(" ---Retrying")
        time.sleep(5)
        try:
            game = bgg.game(game_id=id)            
            print(game.name)
        except:
            print("Could not download {}".format(id))
            return False
    if game.expansion:
        return None
    fields = {
        'idBGG': id,
        'rankBGG': game.boardgame_rank,
        'nomeGioco': game.name,
        'autore': ",".join(game.designers),
        'votoMedio': game.rating_average,
        'pesoMedio': game.data()["averageweight"],
        'numeroVoti': game.users_rated,
        'proprietari': ",".join([name[x] for x in owners]),
        'numGiocatori': "Min:%d - Max:%d" % (game.data()["minplayers"], game.data()["maxplayers"]),
        'annoPubblicazione': game.year,
        'durata': game.playing_time,
        'image': game.image,
    }
    return fields

dic = {}
for user in name:
    print(user)
    hislist = bgg.collection(user_name=user)
    for item in hislist:
        if item.owned:
            dic[item.id] = dic.get(item.id,[]) + [user]

ready = [create_line(game) for game in dic.items()]
filtered = [game for game in ready if game]

with open('./processors/games.json', 'w') as fw:
    fw.write(json.dumps({'items': filtered}, indent=True))
