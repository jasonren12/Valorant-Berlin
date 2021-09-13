# Valorant Berlin
Codebase for the model developed in https://www.youtube.com/watch?v=r1zI9o88efs

For questions, feel free to join the channel discord: https://discord.gg/QbCS5xP3WY and shoot me a question - I should be quite active on there.


## Preface

This codebase was largely just me messing around to build the model for the video quickly before the Masters tourney in Berlin started. I focused on speed and convenience rather than cleanliness, so it is NOT production ready whatsoever and there very well may be issues - sorry in advance.


## Setup

I used poetry for the requirements. If you are not familiar with poetry, see https://python-poetry.org/docs/. Once you have poetry installed, and this repo cloned, run on your command line
- `poetry install`
- `poetry shell`

You should be in the shell when running any python commands given below.


## Datascrape

`python scrape_all.py` should scrape game data off vlr.gg and write to `datascrape/datasets`


## Modelling

I did my modelling largely in a Google Colab Notebook. I downloaded the notebook to `notebooks/Valorant Berlin.ipynb`. I would recommend uploading this notebook to your google drive and opening with Colab. It should largely run top down, and there are form titles/comments that should describe high level what each block does.
