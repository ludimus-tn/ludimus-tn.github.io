import glob
import json
import os
import hashlib
import markdown2
import re
from random import Random


HIDDEN_GAMES = {
    67492,   # battles-westeros
    463,     # magic-gathering
}

markdowner = markdown2.Markdown()

boardgame_tmpl = '\n'.join(open('./layouts/partials/boardgame.html').readlines())
google_analytics = '\n'.join(open('./layouts/partials/google-analytics.html').readlines())
footer = ''.join(open('./layouts/partials/footer.html').readlines())
league_ranking = ''.join(open('./layouts/partials/league-ranking.html').readlines())
league_rules = ''.join(markdowner.convert(open('./static/docs/league/2019-20-Regolamento.md').read().encode('utf-8')))
style_hash = hashlib.md5(open('./style.css').read().encode('utf-8')).hexdigest()
input_data = json.loads(''.join(open('./processors/games.json').readlines()))
buonconsiglio_event_details = ''.join(markdowner.convert(open('./static/docs/events/20200725-castello-buonconsiglio.md').read().encode('utf-8')))
blog_post_tmpl = open('./layouts/partials/blog-post.html').readlines()
blog_preview_tmpl = open('./layouts/partials/blog-preview.html').readlines()

board_games = []
for item in sorted(input_data.get('items', []), key=lambda x: x.get('votoMedio', 0), reverse=True):
    if item['idBGG'] in HIDDEN_GAMES:
        continue

    image = item['thumbnail']
    board_games.append(boardgame_tmpl.format(
        name=item['nomeGioco'],
        image=image,
        link='https://boardgamegeek.com/boardgame/{}/-'.format(item['idBGG']),
        vote='{0:0.1f}'.format(item['votoMedio']),
        players=item['numGiocatori'].replace('Min:', 'da ').replace(' - Max:', ' a '),
        time=item['durata'],
        weight='{0:0.1f}'.format(item['pesoMedio']),
    ))

blog_file_to_tmpl = {}
for post in sorted(glob.glob('./layouts/blog/*')):
    file_name = post.replace('./layouts/blog/', '')
    title = file_name[10:].replace('.html', '').replace('.md', '').replace('-', ' ').title()
    file_url = file_name.replace('.md', '.html')
    with open(post) as post_tmpl:
        for line in post_tmpl:
            if 'blog_post_author_img: ' in line:
                author_img = line.replace('blog_post_author_img: ', '')
                continue
            if 'blog_post_og: ' in line:
                og_image = line.replace('blog_post_og: ', '')
                continue
            if 'blog_post_abstract: ' in line:
                abstract = line.replace('blog_post_abstract: ', '')
                continue

    post_date_tmp = file_url[:10].split('-')
    post_date = '{}/{}/{}'.format(post_date_tmp[2], post_date_tmp[1], post_date_tmp[0])

    output_blog_tmpl = ''
    output_blog_tmpl += '<div class="col-lg-3 col-md-4 col-sm-6 col-xs-12" style="display: none;">'
    for blog_line in blog_preview_tmpl:
        if '{{ blog_url }}' in blog_line:
            output_blog_tmpl += blog_line.replace('{{ blog_url }}', file_url)
        elif '{{ image_url }}' in blog_line:
            output_blog_tmpl += blog_line.replace('{{ image_url }}', og_image.replace('https://ludimus.it/', '../'))
        elif '{{ title }}' in blog_line:
            output_blog_tmpl += blog_line.replace('{{ title }}', title)
        elif '{{ date }}' in blog_line:
            output_blog_tmpl += blog_line.replace('{{ date }}', post_date)
        elif '{{ author_img }}' in blog_line:
            output_blog_tmpl += blog_line.replace('{{ author_img }}', author_img)
        elif '{{ abstract }}' in blog_line:
            output_blog_tmpl += blog_line.replace('{{ abstract }}', abstract)
        else:
            output_blog_tmpl += blog_line
    output_blog_tmpl += '</div>'
    blog_file_to_tmpl[post] = output_blog_tmpl

###############################################################################
## Homepage
###############################################################################

with open('./layouts/index.html') as base_index_tmpl, \
        open('./index.html', 'w') as output_index:

    for line in base_index_tmpl:
        if '{{ number_of_games }}' in line:
            output_index.write(line.replace('{{ number_of_games }}', str(len(board_games))))
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
                output_index.write(blog_file_to_tmpl[post])

        else:
            output_index.write(line)

###############################################################################
## Games
###############################################################################

with open('./layouts/games.html') as base_games_tmpl, \
        open('./games.html', 'w') as output_games:

    for line in base_games_tmpl:
        if '{{ hash }}' in line:
            output_games.write(line.replace('{{ hash }}', style_hash))
        elif '{{ games }}' in line:
            for item in board_games:
                output_games.write(item)
        elif '{{ number_of_games }}' in line:
            output_games.write(line.replace('{{ number_of_games }}', str(len(board_games))))
        elif '{{ google_analytics }}' in line:
            output_games.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ footer }}' in line:
            output_games.write(line.replace('{{ footer }}', footer))
        else:
            output_games.write(line)

###############################################################################
## Informative
###############################################################################

with open('./layouts/informative.html') as base_games_tmpl, \
        open('./informative.html', 'w') as output_games:
    for line in base_games_tmpl:
        if '{{ google_analytics }}' in line:
            output_games.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ footer }}' in line:
            output_games.write(line.replace('{{ footer }}', footer))
        else:
            output_games.write(line)

###############################################################################
## League
###############################################################################

with open('./layouts/league.html') as base_league_tmpl, \
        open('./league.html', 'w') as output_league:
    for line in base_league_tmpl:
        if '{{ google_analytics }}' in line:
            output_league.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ league_ranking }}' in line:
            output_league.write(line.replace('{{ league_ranking }}', league_ranking))
        elif '{{ footer }}' in line:
            output_league.write(line.replace('{{ footer }}', footer))
        else:
            output_league.write(line)

###############################################################################
## League Rules
###############################################################################

with open('./layouts/league-rules.html') as base_league_tmpl, \
        open('./league-rules.html', 'w') as output_league:
    for line in base_league_tmpl:
        if '{{ google_analytics }}' in line:
            output_league.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ league_rules }}' in line: 
            output_league.write(line.replace('{{ league_rules }}', league_rules))
        elif '{{ footer }}' in line:
            output_league.write(line.replace('{{ footer }}', footer))
        else:
            output_league.write(line)

###############################################################################
## League Slideshow
###############################################################################

with open('./layouts/league-slideshow.html') as base_league_tmpl, \
        open('./league-slideshow.html', 'w') as output_league:
    for line in base_league_tmpl:
        if '{{ google_analytics }}' in line:
            output_league.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ league_ranking }}' in line: 
            output_league.write(line.replace('{{ league_ranking }}', league_ranking))
        else:
            output_league.write(line)


###############################################################################
## Event
###############################################################################

with open('./layouts/events/20200725-castello-buonconsiglio.html') as base_event_tmpl, \
        open('./events/20200725-castello-buonconsiglio.html', 'w') as output_event:
    for line in base_event_tmpl:
        if '{{ google_analytics }}' in line:
            output_event.write(line.replace('{{ google_analytics }}', google_analytics))
        elif '{{ buonconsiglio_event_details }}' in line: 
            output_event.write(line.replace('{{ buonconsiglio_event_details }}', buonconsiglio_event_details))
        elif '{{ footer }}' in line:
            output_event.write(line.replace('{{ footer }}', footer))
        else:
            output_event.write(line)
            
###############################################################################
## BLOG
###############################################################################

posts = glob.glob('./layouts/blog/*')
for post in posts:
    post_name = post.rsplit('/', 1)[1]

    with open(post) as post_tmpl, \
            open('./blog/{}'.format(post_name.replace('.md', '.html')), 'w+') as output_post:

        post_body = post_tmpl.readlines()

        title = None
        author = None
        author_img = None
        og_image = None
        post_blog_body = []
        read_more = []

        for line in post_body:
            if 'blog_post_title: ' in line:
                title = line.replace('blog_post_title: ', '').strip()
            elif 'blog_post_abstract: ' in line:
                continue  # we don't care about it right now!
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
                output_post.write(line.replace('{{ blog_post_body }}', markdown2.markdown(''.join(post_blog_body), extras={'break-on-newline': True})))
            elif '{{ blog_post_author_img }}' in line:
                output_post.write(line.replace('{{ blog_post_author_img }}', author_img))
            elif '{{ blog_post_author }}' in line:
                output_post.write(line.replace('{{ blog_post_author }}', author))
            elif '{{ blog_post_og }}' in line:
                output_post.write(line.replace('{{ blog_post_og }}', og_image))
            elif '{{ blog_post_read_more }}' in line:
                post_blogs_links = list(set(glob.glob('./layouts/blog/*')) - {post})
                Random(post).shuffle(post_blogs_links)
                read_more_files = post_blogs_links[:4]
                for post in read_more_files:
                    output_post.write(blog_file_to_tmpl[post])
            else:
                output_post.write(line)
