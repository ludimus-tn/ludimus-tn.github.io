# http://ludimus.it

## How to install

- mkvirtualenv ludimus  --python `which python3`
- pip install -r requirements.txt


## How to update boardgames

- python processors/fetch.py  # edit this file if needed


## How to generate the new website

- python processors/generate.py


## How to deploy

- git commit -am "do something cool" && git push


## Environment variables

- `SHUFFLE_BLOG_LINKS`: (default: False) if set to True, the suggested links in blog posts will be shuffled
- `DO_BLOG_POSTS`: (default: False) if set to True, blog posts will be generated
