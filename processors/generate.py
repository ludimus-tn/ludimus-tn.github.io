import json
import os

GAMES_WITHOUT_MD = {
    102548,  # dungeon-fighter
    197551,  # hall-fame
    161995,  # hexemonia
    11336,   # magor-magician
    136143,  # squillo
    205359,  # star-wars-destiny
    121408,  # trains
    35761,   # sylla
    171668,  # grizzled
    169302,  # warage-enascentia
    53953,   # thunderstone
    21790,   # thurn-and-taxis
    71836,   # onirim
    84876,   # castles-burgundy
    24850,   # templaria
    189628,  # tesseract
    28143,   # race-galaxy
    167400,  # ashes-rise-phoenixborn
    154883,  # si-oscuro-signore-seconda-edizione
    161261,  # bim-bum-bam
    136888,  # bruges
    154509,  # kingsport-festival
    12956,   # futurisiko
}

BASE_ITEM = """
<div class="card">
    <img class="card-img-top" src="{image}" />

    <div class="card-block">
        <h3 class="card-title">{name}</h3>
    </div>

    <ul class="list-group list-group-flush">
        <li class="list-group-item d-flex justify-content-between align-items-center">
            Voto <span class="badge badge-light">{vote} / 10</span>
        </li>
        <li class="list-group-item d-flex justify-content-between align-items-center">
            Giocatori <span class="badge badge-light">{players}</span>
        </li>
        <li class="list-group-item d-flex justify-content-between align-items-center">
            Durata <span class="badge badge-light">{time} min</span>
        </li>
        <li class="list-group-item d-flex justify-content-between align-items-center">
            Complessità <span class="badge badge-light">{weight} / 5</span>
        </li>
    </ul>

    <div class="card-block">
        <a href="{link}" target="_blank">Dettagli ⇢</a>
    </div>
</div>
"""

with open('./base/index.html') as base_index_tmpl, \
        open('./base/games.html') as base_games_tmpl, \
        open('./processors/games.json') as data, \
        open('./index.html', 'w') as output_index, \
        open('./games.html', 'w') as output_games:

    input_data = json.loads(''.join(data.readlines()))

    for line in base_index_tmpl:
        output_index.write(line.replace('{{ number_of_games }}', str(len(input_data.get('items', [])))))

    for line in base_games_tmpl:
        if line.strip() != '{{ games }}':
            output_games.write(line.replace('{{ number_of_games }}', str(len(input_data.get('items', [])))))
        else:
            break

    for item in input_data.get('items', []):
        image = item['image'].replace('.jpg', '_md.jpg').replace('.png', '_md.png')
        if item['idBGG'] in GAMES_WITHOUT_MD:
            image = item['image'].replace('.jpg', '_t.jpg').replace('.png', '_t.png')

        item_with_template = BASE_ITEM.format(
            name=item['nomeGioco'],
            image=image,
            link='https://boardgamegeek.com/boardgame/{}/-'.format(item['idBGG']),
            vote='{0:0.1f}'.format(item['votoMedio']),
            players=item['numGiocatori'].replace('Min:', 'da ').replace(' - Max:', ' a '),
            time=item['durata'],
            weight='{0:0.1f}'.format(item['pesoMedio']),
        )
        output_games.write(item_with_template)

    for line in base_games_tmpl:
        output_games.write(line)
