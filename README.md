# Packman
[![Django CI](https://github.com/Pack144/packman/actions/workflows/django.yml/badge.svg)](https://github.com/Pack144/packman/actions/workflows/django.yml)
[![CodeQL](https://github.com/Pack144/packman/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Pack144/packman/actions/workflows/codeql-analysis.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Cub Scout pack management web application, written in Python and Django

## Features
* Membership management - complete with address book for keeping track of things
  such as phone numbers and addresses.
    * Parents
    * Scouts
    * Friends of the Pack
* Den Assignments - so you know what cubs belong to which den.
* Committee assignments - Cubs aren't the only ones who get to have all the fun. A
  well run pack has lots of parent involvement.
* Calendar of Events - Always know when the next Pack Meeting, Community Service event,
  or Den Meeting is scheduled.
* Documents Repository. So you have a secure place to make files available to members
  of the pack.
* Dynamic content, manageable through Django's built-in admin frameworks.

## Why this app?
Packman was written specifically for the purpose of managing Cub Scout Pack 144,
a pack based in Seattle, WA.  We are the oldest and one of the largest Cub Scout
Pack in the state of Washington.  We like to do things our way, but that doesn't mean
that what we do doesn't work for your pack.  We built this for ourselves, but we are
sure that there's use for other packs out there too.

Being a pack headquartered in a tech-heavy community in the Pacific Northwest, naturally
we wanted to have a website that we could adapt for our own specific needs.
At the same time, not all of our pack members are tech savvy and we need to ensure that
the frameworks we put in place with our web app are accessible to everyone in the pack.
We chose the Django framework because it is highly flexible, maintainable, and most
importantly understandable.  That means that even members who do not live web development
day to day should be able to pick it up and continue to maintain the site.

## How do I get started?
To help manage the proper Python versions and dependencies, we recommend using [pyenv](https://github.com/pyenv/pyenv) to manage your Python versions.  You can install pyenv using your favorite package manager or by following the instructions in the link above.

Once you have pyenv installed, install the required Python version:
```bash
pyenv install 3.13
```

Then set the local Python version for this project:

```bash
pyenv local
```

As with any Python and Django project, it is highly recommended that you install
Packman in its own virtual environment. You can choose which virtual environment
you want to use. Both pip and pipenv files are provided for installing project
requirements.

To begin using virtual environments, we'll use pipenv. Install using your favorite
package manager or use pip that ships with Python.
```
pip install --user pipenv
```

Once Pipenv is installed, clone this repository and create your virtual environment
```
git clone git@bitbucket.org:pack144/packman.git
cd packman
pipenv install
```

Once you have the project downloaded and a virtual environment running you can set
up Packman for your own needs. Many of the project settings are available in
`config/settings/*.py`. Adjust them there or, to have your own settings that are
not overridden by source updates, create a separate `.env`
file and put your custom settings there. Anything made in this file will overwrite
the project settings file. Use this to configure your own database, secret key,
email, etc.

### Optional Environment Setup
Copy the example environment file to a new file named `.env` in the root of the
project directory.
```bash
cp .env.example .env
```

And you can modify the settings in `.env` to suit your own environment.

After you've updated the settings for your own environment, it's time to enter the virtual environment and set up the database.

#### Enter the virtual environment
```bash
pipenv shell
```

#### Set up the database
```bash
python manage.py migrate
```

#### Create a superuser
```bash
# Create a superuser so you can log into the admin interface
python manage.py createsuperuser
```

#### Run the development server
```bash
python manage.py runserver
```

You should now be able to access the development server at http://localhost:8000

If you want to exit the virtual environment, just type `exit` at the command prompt.


## Requirements
Review the included requirements.txt for detailed package requirements.  Our
application is using:

* [Python 3.10](https://python.org)
* [Django 5.2.6](https://djangoproject.com)
* [Npm](https://www.npmjs.com/)


## Running locally with a backup of production Postgres on SQLite

You can run the site locally against a copy of the production PostgreSQL database,
converted to SQLite — no local Postgres installation required.

### 1. Obtain a production pg_dump

Get a `.sql` or `.sql.gz` dump from the production server.

### 2. Convert the dump to SQLite

```bash
python util/pg_to_sqlite.py /path/to/django-YYYYMMDDHHII.sql.gz \
    --output /path/to/output.sqlite3
```

Add `--django` to also run Django migrations after the data is loaded (useful
if the dump is slightly behind the current schema):

```bash
python util/pg_to_sqlite.py /path/to/django-YYYYMMDDHHII.sql.gz \
    --output /path/to/output.sqlite3 \
    --django
```

Run `python util/pg_to_sqlite.py --help` for all options.

### 3. Point your .env at the SQLite file

Copy `env.example-local` to `.env` (if you haven't already), then edit `.env`
and set `DATABASE_URL` to the absolute path of the file you just created:

```bash
cp env.example-local .env
```

```bash
# in .env
DATABASE_URL="sqlite:////path/to/output.sqlite3"
```

> Note the four slashes — three are part of the `sqlite:///` scheme, the fourth
> begins the absolute path.

### 4. Start the development server

```bash
./util/start_local.sh
```

`util/start_local.sh` sets `DJANGO_SETTINGS_MODULE=packman.settings.local` and runs
`manage.py migrate` automatically before starting the server.  You should now be
able to access the site at http://localhost:8000 with production data.


## How to run tests

To run the tests, first ensure that you are in the virtual environment.  Then run:

```bash
python manage.py test
```

or

```bash
pipenv run python manage.py test
```


## How to run pre-commit hooks

To run the pre-commit hooks, first ensure that you are in the virtual environment.
Then run:

```bash
pre-commit install
pre-commit run --all-files
```

or

```base
pipenv run pre-commit run --all-files
```

While pre-commit hooks will automatically run in github after you've created a PR, it is of course best to run these locally first.
