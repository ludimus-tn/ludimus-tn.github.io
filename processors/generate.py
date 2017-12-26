import glob
import json
import os
import hashlib


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
    1234,    # once-upon-time-storytelling-card-game
    26859,   # kragmortha
    12747,   # scarabeo
    124856,  # anno-domini-penne-e-pennelli
    1931,    # anti-monopoly
}

HIDDEN_GAMES = {
    67492,   # battles-westeros
    463,     # magic-gathering
}

boardgame_tmpl = '\n'.join(open('./layouts/partials/boardgame.html').readlines())
google_analytics = '\n'.join(open('./layouts/partials/google-analytics.html').readlines())
style_hash = hashlib.md5(open('./style.css').read().encode('utf-8')).hexdigest()
input_data = json.loads(''.join(open('./processors/games.json').readlines()))

item_to_print = []

for item in input_data.get('items', []):
    if item['idBGG'] in HIDDEN_GAMES:
        continue

    image = item['image'].replace('.jpg', '_md.jpg').replace('.png', '_md.png')
    if item['idBGG'] in GAMES_WITHOUT_MD:
        image = item['image'].replace('.jpg', '_t.jpg').replace('.png', '_t.png')

    item_to_print.append(boardgame_tmpl.format(
        name=item['nomeGioco'],
        image=image,
        link='https://boardgamegeek.com/boardgame/{}/-'.format(item['idBGG']),
        vote='{0:0.1f}'.format(item['votoMedio']),
        players=item['numGiocatori'].replace('Min:', 'da ').replace(' - Max:', ' a '),
        time=item['durata'],
        weight='{0:0.1f}'.format(item['pesoMedio']),
    ))


with open('./layouts/index.html') as base_index_tmpl, \
        open('./index.html', 'w') as output_index:

    for line in base_index_tmpl:
        if '{{ number_of_games }}' in line:
            output_index.write(line.replace('{{ number_of_games }}', str(len(item_to_print))))
        elif '{{ hash }}' in line:
            output_index.write(line.replace('{{ hash }}', style_hash))
        elif '{{ google_analytics }}' in line:
            output_index.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ blog_post }}' in line:
            for post in glob.glob('./layouts/blog/*'):
                file_name = post.replace('./layouts/blog/', '')
                title = file_name[10:].replace('.html', '').replace('-', ' ').title()
                output_index.write('<li><img src="../static/img/meeple.svg" /> <a href="/blog/{}">{}</a></li>'.format(file_name, title))
        else:
            output_index.write(line)


with open('./layouts/games.html') as base_games_tmpl, \
        open('./games.html', 'w') as output_games:

    for line in base_games_tmpl:
        if '{{ hash }}' in line:
            output_games.write(line.replace('{{ hash }}', style_hash))
        elif '{{ games }}' in line:
            for item in item_to_print:
                output_games.write(item)
        elif '{{ number_of_games }}' in line:
            output_games.write(line.replace('{{ number_of_games }}', str(len(item_to_print))))
        elif '{{ google_analytics }}' in line:
            output_games.write(line.replace('{{ google_analytics }}', google_analytics))
        else:
            output_games.write(line)


posts = glob.glob('./layouts/blog/*')
for post in posts:
    post_name = post.rsplit('/', 1)[1]

    with open(post) as post_tmpl, \
            open('./blog/{}'.format(post_name), 'w+') as output_post:

        for line in post_tmpl:
            if '{{ hash }}' in line:
                output_post.write(line.replace('{{ hash }}', style_hash))
            elif '{{ google_analytics }}' in line:
                output_post.write(line.replace('{{ google_analytics }}', google_analytics))
            else:
                output_post.write(line)
