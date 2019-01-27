import csv
import time
from boardgamegeek import BoardGameGeek
import json
import diskcache as dc
import progressbar

cache = dc.Cache('tmp')

name = {
    'Ludimus': 'Ludimus',
    'Pufforrohk': 'Alessio',
    'Masnonet': 'Davide',
    'earendil02': 'Riccardo',
    'nostalgiaz': 'Mattia',
    'melachel': 'Stefano',
    'hina00': 'Sofia',
    'Leouz': 'Leonardo',
    'ResN91': 'Andrea',
    'Sambaita': 'Samantha'
}

bgg = BoardGameGeek(retries=10)


def create_line(pair):
    id, owners = pair

    if cache.get(id, default=False):
        return json.loads(cache[id])

    try:
        game = bgg.game(game_id=id)
    except:
        time.sleep(1)
        try:
            game = bgg.game(game_id=id)
        except:
            return None
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
        'thumbnail': game.thumbnail,
    }
    cache[id] = json.dumps(fields)
    return fields

dic = {}
for user in name:
    print('Fetching collection of', user)
    c = 0
    found = False
    while not found and c<5:
        try:
            hislist = bgg.collection(user_name=user)
            found = True
        except:
            pass
    if not found:
        exit(1)
    for item in hislist:
        if item.owned:
            dic[item.id] = dic.get(item.id,[]) + [user]

print('Fetching all the games!')
ready = []
total_count = len(dic.keys())
count = 0
with progressbar.ProgressBar(max_value=total_count) as bar:
    for game in dic.items():
        count += 1
        bar.update(count)
        ready.append(create_line(game))

filtered = [game for game in ready if game]

with open('./processors/games.json', 'w') as fw:
    fw.write(json.dumps({'items': sorted(filtered, key=lambda x: x['idBGG'])}, indent=True))
