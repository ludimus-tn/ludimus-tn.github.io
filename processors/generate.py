from ast import If
import datetime
import glob
import json
import os
import hashlib
import markdown2
import re
import os
from random import Random


HIDDEN_GAMES = {
    67492,   # battles-westeros
    463,     # magic-gathering
}

markdowner = markdown2.Markdown()

boardgame_tmpl = '\n'.join(open('./layouts/partials/boardgame.html').readlines())
footer = ''.join(open('./layouts/partials/footer.html').readlines())
league_ranking = ''.join(open('./layouts/partials/league-ranking.html').readlines())
league_rules = ''.join(markdowner.convert(open('./static/docs/league/2019-20-Regolamento.md').read().encode('utf-8')))
style_hash = hashlib.md5(open('./style.css').read().encode('utf-8')).hexdigest()
input_data = json.loads(''.join(open('./processors/games.json').readlines()))
blog_post_tmpl = open('./layouts/partials/blog-post.html').readlines()
blog_preview_tmpl = open('./layouts/partials/blog-preview.html').readlines()
event_link_tmpl = open('./layouts/partials/event-link.html').readlines()
events_tmpl = open('./layouts/partials/event.html').readlines()
escaperoom_link_tmpl = open('./layouts/partials/escaperoom-link.html').readlines()

board_games = []
for item in sorted(input_data.get('items', []), key=lambda x: x.get('idBGG', 0), reverse=True):
    if item['idBGG'] in HIDDEN_GAMES:
        continue

    image = item['thumbnail']
    if not 'pesoMedio' in item or item['pesoMedio'] is None:
        pesoMedio = '?'
    else:
        pesoMedio = '{0:0.1f}'.format(item['pesoMedio'])

    board_games.append(boardgame_tmpl.format(
        name=item['nomeGioco'],
        image=image if image else 'https://ludimus.it/images/no-image-available.png',
        link='https://boardgamegeek.com/boardgame/{}/-'.format(item['idBGG']),
        # vote='{0:0.1f}'.format(item['votoMedio']),
        players=item['numGiocatori'].replace('Min:', 'da ').replace(' - Max:', ' a '),
        time=item['durata'],
        weight=pesoMedio,
        location=item['proprietari']
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

events = sorted(glob.glob('./layouts/events/*'), reverse=True)

escaperooms = sorted(glob.glob('./layouts/escaperooms/*'), reverse=True)

###############################################################################
## Homepage
###############################################################################

with open('./layouts/index.html') as base_index_tmpl, \
        open('./index.html', 'w') as output_index:

    for line in base_index_tmpl:
        if '{{ number_of_games }}' in line:
            output_index.write(line.replace('{{ number_of_games }}', str(len(board_games))))
        elif '{{ hash }}' in line:
            output_index.write(line.replace('{{ hash }}', style_hash))
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
        if '{{ footer }}' in line:
            output_games.write(line.replace('{{ footer }}', footer))
        else:
            output_games.write(line)

###############################################################################
## Trasparenza
###############################################################################

with open('./layouts/trasparenza.html') as trasparenza_tmpl, \
        open('./trasparenza.html', 'w') as output_trasparenza:
    for line in trasparenza_tmpl:
        if '{{ footer }}' in line:
            output_trasparenza.write(line.replace('{{ footer }}', footer))
        else:
            output_trasparenza.write(line)

###############################################################################
## League
###############################################################################

with open('./layouts/league.html') as base_league_tmpl, \
        open('./league.html', 'w') as output_league:
    for line in base_league_tmpl:
        if '{{ footer }}' in line:
            output_league.write(line.replace('{{ footer }}', footer))
        else:
            output_league.write(line)

###############################################################################
## League Rules
###############################################################################

with open('./layouts/league-rules.html') as base_league_tmpl, \
        open('./league-rules.html', 'w') as output_league:
    for line in base_league_tmpl:
        if '{{ league_rules }}' in line: 
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
        if '{{ league_ranking }}' in line: 
            output_league.write(line.replace('{{ league_ranking }}', league_ranking))
        else:
            output_league.write(line)


###############################################################################
## ARCHIVED EVENTS
###############################################################################

archived_events = []
for event in sorted(events, reverse=True):
    event_name = event.replace('./layouts/events/', '')
    event_date_tmp = event_name[:10].split('-')
    event_day = int(event_date_tmp[2])
    event_month = int(event_date_tmp[1])
    event_year = int(event_date_tmp[0])

    event_date = datetime.datetime(event_year, event_month, event_day)
    now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if event_date >= now:
        continue
    archived_events.append(event)

with open('./layouts/archive.html') as base_archive_events_tmpl, \
        open('./archive.html', 'w') as output_archive_events:
    for line in base_archive_events_tmpl:
        if '{{ footer }}' in line:
            output_archive_events.write(line.replace('{{ footer }}', footer))
        elif '{{ archived_events }}' in line: 
            for archived_event in archived_events:
                event_name = archived_event.replace('./layouts/events/', '')
                event_title = event_name[10:].replace('.html', '').replace('.md', '').replace('-', ' ').title()
                event_date_tmp = event_name[:10].split('-')
                event_date = '{}/{}/{}'.format(event_date_tmp[2], event_date_tmp[1], event_date_tmp[0])
                event_url = event_name.replace('.md', '.html')

                event_body = open(archived_event).readlines()
                for event_line in event_body:
                    if 'event_title: ' in event_line:
                        event_title = event_line.replace('event_title: ', '').strip()

                for line in event_link_tmpl:
                    if '{{ title }}' in line:
                        output_archive_events.write(line.replace('{{ title }}', event_title))
                    elif '{{ date }}' in line:
                        output_archive_events.write(line.replace('{{ date }}', event_date))
                    elif '{{ event_url }}' in line:
                        output_archive_events.write(line.replace('{{ event_url }}', event_url))
                    else:
                        output_archive_events.write(line)
        else:
            output_archive_events.write(line)

###############################################################################
## EVENTS
###############################################################################

next_events = []
for event in sorted(events, reverse=False):
    event_name = event.replace('./layouts/events/', '')
    event_date_tmp = event_name[:10].split('-')
    event_day = int(event_date_tmp[2])
    event_month = int(event_date_tmp[1])
    event_year = int(event_date_tmp[0])

    event_date = datetime.datetime(event_year, event_month, event_day)
    now = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if event_date < now:
        continue
    next_events.append(event)

with open('./layouts/events.html') as base_events_tmpl, \
        open('./events.html', 'w') as output_events:
    for line in base_events_tmpl:
        if '{{ footer }}' in line:
            output_events.write(line.replace('{{ footer }}', footer))
        elif '{{ next_events }}' in line:
            if len(next_events) == 0:
                output_events.write('Al momento non ci sono eventi in programma 🎲')
                continue
            for event in next_events:
                event_name = event.replace('./layouts/events/', '')
                event_title = event_name[10:].replace('.html', '').replace('.md', '').replace('-', ' ').title()
                event_date_tmp = event_name[:10].split('-')
                event_date = '{}/{}/{}'.format(event_date_tmp[2], event_date_tmp[1], event_date_tmp[0])
                event_url = event_name.replace('.md', '.html')

                event_body = open(event).readlines()
                for event_line in event_body:
                    if 'event_title: ' in event_line:
                        event_title = event_line.replace('event_title: ', '').strip()

                for line in event_link_tmpl:
                    if '{{ title }}' in line:
                        output_events.write(line.replace('{{ title }}', event_title))
                    elif '{{ date }}' in line:
                        output_events.write(line.replace('{{ date }}', event_date))
                    elif '{{ event_url }}' in line:
                        output_events.write(line.replace('{{ event_url }}', event_url))
                    else:
                        output_events.write(line)
        else:
            output_events.write(line)

###############################################################################
## EVENT
###############################################################################

static_events = [
    "ala",
    "bicigrillruotalibera",
    "cantiere26",
    "doppiomalto",
    "le-petit-jardin",
    "luogo-comune-riva",
    "savot-ala",
    "simposio",
    "smartlab",
]

done = {event: False for event in static_events}

events = sorted(glob.glob('./layouts/events/*'), reverse=True)
for event in events:
    event_name = event.rsplit('/', 1)[1]
    
    must_do_static = False
    try:
        event_type = event_name.split('serata-')
        if len(event_type) >= 2:
            event_type = event_type[1].split('.')[0]
            if event_type in static_events:
                date = datetime.datetime.strptime(event_name[:10], '%Y-%m-%d')
                today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if today <= date < today + datetime.timedelta(days=7):
                    must_do_static = True
    except IndexError:
        pass

    with open(event) as event_tmpl, \
            open('./events/{}'.format(event_name.replace('.md', '.html')), 'w+') as output_event:

        event_body = event_tmpl.readlines()

        title = None
        description = None
        og_image = None
        date = None
        place = None
        content = []

        for line in event_body:
            if 'event_title: ' in line:
                title = line.replace('event_title: ', '').strip()
            elif 'event_description: ' in line:
                description = line.replace('event_description: ', '').strip()
            elif 'event_date: ' in line:
                date = line.replace('event_date: ', '').strip()
            elif 'event_place: ' in line:
                place = line.replace('event_place: ', '').strip()
            elif 'event_og: ' in line:
                og_image = line.replace('event_og: ', '').strip()
            else:
                content.append(line)

        for line in events_tmpl:
            if '{{ hash }}' in line:
                output_event.write(line.replace('{{ hash }}', style_hash))
            elif '{{ footer }}' in line:
                output_event.write(line.replace('{{ footer }}', footer))
            elif '{{ event_title }}' in line:
                output_event.write(line.replace('{{ event_title }}', title))
            elif '{{ event_description }}' in line:
                output_event.write(line.replace('{{ event_description }}', description))
            elif '{{ event_body }}' in line:
                output_event.write(line.replace('{{ event_body }}', markdown2.markdown(''.join(content), extras={'break-on-newline': True})))
            elif '{{ event_og }}' in line:
                output_event.write(line.replace('{{ event_og }}', og_image))
            else:
                output_event.write(line)

        if must_do_static:
            if not done[event_type]:
                with open('./events/{}.html'.format(event_type), 'w') as static_event:
                    static_event.write('<meta http-equiv="refresh" content="0; url=/events/{}.html" />'.format(event_name.replace('.md', '')))
                    done[event_type] = True

    for static_event in static_events:
        if not done[static_event]:
            with open('./events/{}.html'.format(static_event), 'w') as static_event:
                static_event.write('<meta http-equiv="refresh" content="0; url=/events" />'.format(static_event))

###############################################################################
## T-Shirt Requirements
###############################################################################

with open('./layouts/maglietta.html') as base_tshirt_tmpl, \
        open('./maglietta.html', 'w') as output_event:
    for line in base_tshirt_tmpl:
        if '{{ footer }}' in line:
            output_event.write(line.replace('{{ footer }}', footer))
        else:
            output_event.write(line)

###############################################################################
## GAS
###############################################################################

with open('./layouts/gas.html') as gas_tmpl, \
        open('./gas.html', 'w') as output_gas:
    for line in gas_tmpl:
        if '{{ footer }}' in line:
            output_gas.write(line.replace('{{ footer }}', footer))
        else:
            output_gas.write(line)

###############################################################################
## BLOG PAGE
###############################################################################

with open('./layouts/blog.html') as base_blog_tmpl, \
        open('./blog.html', 'w') as output_blog:
    for line in base_blog_tmpl:
        if '{{ hash }}' in line:
            output_blog.write(line.replace('{{ hash }}', style_hash))
        elif '{{ footer }}' in line:
            output_blog.write(line.replace('{{ footer }}', footer))
        elif '{{ blog_posts }}' in line:
            for post in sorted(glob.glob('./layouts/blog/*'), reverse=True):
                output_blog.write(blog_file_to_tmpl[post])
        else:
            output_blog.write(line)
            
###############################################################################
## BLOG
###############################################################################

posts = glob.glob('./layouts/blog/*')
do_posts = os.getenv('DO_BLOG_POSTS', False)
if not do_posts:
    posts = []
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
                use_random = os.getenv('SHUFFLE_BLOG_LINKS', False)
                if use_random:
                    Random(post).shuffle(post_blogs_links)
                read_more_files = post_blogs_links[:4]
                for post in read_more_files:
                    output_post.write(blog_file_to_tmpl[post])
            else:
                output_post.write(line)

###############################################################################
## LUDICAMP
###############################################################################

with open('./layouts/ludicamp.html') as base_ludicamp_tmpl, \
        open('./ludicamp.html', 'w') as output_ludicamp:
    for line in base_ludicamp_tmpl:
        if '{{ footer }}' in line:
            output_ludicamp.write(line.replace('{{ footer }}', footer))
        else:
            output_ludicamp.write(line)

###############################################################################
## CRONACHE AHRANILES
###############################################################################

with open('./layouts/cronache-ahraniles.html') as cronache_tmpl, \
        open('./cronache-ahraniles.html', 'w') as output_cronache:
    for line in cronache_tmpl:
        if '{{ footer }}' in line:
            output_cronache.write(line.replace('{{ footer }}', footer))
        else:
            output_cronache.write(line)

###############################################################################
## ESCAPEROOMS
###############################################################################

with open('./layouts/escaperooms.html') as base_escaperooms_tmpl, \
        open('./escaperooms.html', 'w') as output_escaperooms:
    for line in base_escaperooms_tmpl:
        if '{{ footer }}' in line:
            output_escaperooms.write(line.replace('{{ footer }}', footer))
        else:
            output_escaperooms.write(line)


# ###############################################################################
# ## ESCAPEROOM
# ###############################################################################

# escaperooms = glob.glob('./layouts/escaperooms/*')
# for escaperoom in escaperooms:
#     escaperoom_name = escaperoom.rsplit('/', 1)[1]

#     with open(escaperoom) as escaperoom_tmpl, \
#             open('./escaperooms/{}'.format(escaperoom_name), 'w+') as output_escaperoom:
#         for line in cronache_tmpl:
#             if '{{ footer }}' in line:
#                 output_escaperoom.write(line.replace('{{ footer }}', footer))
#             else:
#                 output_escaperoom.write(line)
