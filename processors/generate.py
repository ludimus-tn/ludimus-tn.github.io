import glob
import json
import os
import hashlib
import markdown2
import re


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
serata_speciale_tmpl = '\n'.join(open('./layouts/partials/serata-speciale.html').readlines())
google_analytics = '\n'.join(open('./layouts/partials/google-analytics.html').readlines())
footer = ''.join(open('./layouts/partials/footer.html').readlines())
style_hash = hashlib.md5(open('./style.css').read().encode('utf-8')).hexdigest()
input_data = json.loads(''.join(open('./processors/games.json').readlines()))
blog_post_tmpl = open('./layouts/partials/blog-post.html').readlines()

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

serate_speciali = []

for serata in sorted(glob.glob('./layouts/serate_speciali/*'), reverse=True):
    with open(serata) as fin:
        data = {
           k.split(': ')[0]: k.split(': ')[1].strip() for k in fin.readlines()
        }
        the_date = serata.rsplit('/', 1)[-1].split('-')[0]
        data['date'] = '{}/{}/{}'.format(the_date[6:8], the_date[4:6], the_date[0:4])
        serate_speciali.append(serata_speciale_tmpl.format(**data))

with open('./layouts/index.html') as base_index_tmpl, \
        open('./index.html', 'w') as output_index:

    for line in base_index_tmpl:
        if '{{ number_of_games }}' in line:
            output_index.write(line.replace('{{ number_of_games }}', str(len(item_to_print))))
        elif '{{ serate_speciali }}' in line:
            for serata in serate_speciali:
                output_index.write(serata)
        elif '{{ hash }}' in line:
            output_index.write(line.replace('{{ hash }}', style_hash))
        elif '{{ google_analytics }}' in line:
            output_index.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ footer }}' in line:
            output_index.write(line.replace('{{ footer }}', footer))
        elif '{{ blog_post }}' in line:
            for post in sorted(glob.glob('./layouts/blog/*'), reverse=True):
                file_name = post.replace('./layouts/blog/', '')
                title = file_name[10:].replace('.html', '').replace('.md', '').replace('-', ' ').title()
                file_url = file_name.replace('.md', '.html')

                if file_name.endswith('.html'):
                    with open(post) as post_tmpl:
                        author_img = None
                        for line in post_tmpl:
                            if '../static/img/staff/' in line and author_img is None:
                                tmp = line.replace('<img src="../static/img/staff/', '')
                                img_name, other = tmp.split('.')
                                author_img = (img_name + '.' + other[:3]).strip()
                                continue
                            if 'og:image"' in line:
                                og_image = line.replace('<meta property="og:image" content="', '').replace('" />', '').replace('"/>', '')
                                continue
                else:
                    with open(post) as post_tmpl:
                        for line in post_tmpl:
                            if 'blog_post_author_img: ' in line:
                                author_img = line.replace('blog_post_author_img: ', '')
                                continue
                            if 'blog_post_og: ' in line:
                                og_image = line.replace('blog_post_og: ', '')

                post_date_tmp = file_url[:10].split('-')
                post_date = '{}/{}/{}'.format(post_date_tmp[2], post_date_tmp[1], post_date_tmp[0])
                output_index.write(
                    '<a href="/blog/{}">' \
                    '<img src="{}?t=1"/>' \
                    '<h4>{}</h4>' \
                    '''
                        <em class="post-date">{}</em>
                        <div class="blog-post-writer__images">
                            <img src="../static/img/staff/{}">
                        </div>
                    '''\
                    '</a>\n'.format(file_url, og_image, title, post_date, author_img)
                )
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
        elif '{{ footer }}' in line:
            output_games.write(line.replace('{{ footer }}', footer))
        else:
            output_games.write(line)


with open('./layouts/informative.html') as base_games_tmpl, \
        open('./informative.html', 'w') as output_games:
    for line in base_games_tmpl:
        if '{{ google_analytics }}' in line:
            output_games.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ footer }}' in line:
            output_games.write(line.replace('{{ footer }}', footer))
        else:
            output_games.write(line)

with open('./layouts/league.html') as base_games_tmpl, \
        open('./league.html', 'w') as output_games:
    for line in base_games_tmpl:
        if '{{ google_analytics }}' in line:
            output_games.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ footer }}' in line:
            output_games.write(line.replace('{{ footer }}', footer))
        else:
            output_games.write(line)
            

posts = glob.glob('./layouts/blog/*')
for post in posts:
    post_name = post.rsplit('/', 1)[1]

    if post.endswith('.html'):
        with open(post) as post_tmpl, \
                open('./blog/{}'.format(post_name), 'w+') as output_post:

            for line in post_tmpl:
                if '{{ hash }}' in line:
                    output_post.write(line.replace('{{ hash }}', style_hash))
                elif '{{ google_analytics }}' in line:
                    output_post.write(line.replace('{{ google_analytics }}', google_analytics))
                elif '{{ footer }}' in line:
                    output_post.write(line.replace('{{ footer }}', footer))
                else:
                    output_post.write(line)
    else:
        with open(post) as post_tmpl, \
                open('./blog/{}'.format(post_name.replace('.md', '.html')), 'w+') as output_post:

            post_body = post_tmpl.readlines()

            title = None
            author = None
            author_img = None
            og_image = None
            post_blog_body = []

            for line in post_body:
                if 'blog_post_title: ' in line:
                    title = line.replace('blog_post_title: ', '').strip()
                elif 'blog_post_author: ' in line:
                    author = line.replace('blog_post_author: ', '').strip()
                elif 'blog_post_author_img: ' in line:
                    author_img = line.replace('blog_post_author_img: ', '').strip()
                elif 'blog_post_og: ' in line:
                    og_image = line.replace('blog_post_og: ', '').strip()
                else:
                    post_blog_body.append(line)

            for line in blog_post_tmpl:
                if '{{ hash }}' in line:
                    output_post.write(line.replace('{{ hash }}', style_hash))
                elif '{{ google_analytics }}' in line:
                    output_post.write(line.replace('{{ google_analytics }}', google_analytics))
                elif '{{ footer }}' in line:
                    output_post.write(line.replace('{{ footer }}', footer))
                elif '{{ blog_post_title }}' in line:
                    output_post.write(line.replace('{{ blog_post_title }}', title))
                elif '{{ blog_post_body }}' in line:
                    output_post.write(line.replace('{{ blog_post_body }}', markdown2.markdown('\n'.join(post_blog_body))))
                elif '{{ blog_post_author_img }}' in line:
                    output_post.write(line.replace('{{ blog_post_author_img }}', author_img))
                elif '{{ blog_post_author }}' in line:
                    output_post.write(line.replace('{{ blog_post_author }}', author))
                elif '{{ blog_post_og }}' in line:
                    output_post.write(line.replace('{{ blog_post_og }}', og_image))
                else:
                    output_post.write(line)


