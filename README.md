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

This project uses [uv](https://docs.astral.sh/uv/) to manage Python versions and
dependencies. Install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repo and sync dependencies:

```bash
git clone git@github.com:Pack144/packman.git
cd packman
uv sync
```

`uv sync` will automatically download Python 3.13 if it isn't already installed,
create a `.venv`, and install all dependencies.

### Environment setup

Copy the example environment file and edit it to suit your environment:

```bash
cp env.example-local .env
```

Configure your database, secret key, email, etc. in `.env`.

### Set up the database

```bash
uv run python manage.py migrate
```

### Create a superuser

```bash
uv run python manage.py createsuperuser
```

### Run the development server

```bash
uv run python manage.py runserver
```

Or use the provided helper script which handles migrations and static assets automatically:

```bash
./util/start_local.sh
```

You should now be able to access the development server at http://localhost:8000.


## Requirements

* [Python 3.14](https://python.org)
* [Django 5.2](https://djangoproject.com)
* [npm](https://www.npmjs.com/)


## Running locally with a backup of production Postgres on SQLite

You can run the site locally against a copy of the production PostgreSQL database,
converted to SQLite — no local Postgres installation required.

### 1. Obtain a production pg_dump

Get a `.sql` or `.sql.gz` dump from the production server.

### 2. Convert the dump to SQLite

```bash
uv run python util/pg_to_sqlite.py /path/to/django-YYYYMMDDHHII.sql.gz \
    --output /path/to/output.sqlite3
```

Add `--django` to also run Django migrations after the data is loaded (useful
if the dump is slightly behind the current schema):

```bash
uv run python util/pg_to_sqlite.py /path/to/django-YYYYMMDDHHII.sql.gz \
    --output /path/to/output.sqlite3 \
    --django
```

Run `uv run python util/pg_to_sqlite.py --help` for all options.

### 3. Point your .env at the SQLite file

Copy `env.example-local` to `.env` (if you haven't already), then set `DATABASE_URL`
to the absolute path of the file you just created:

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
`manage.py migrate` automatically before starting the server. You should now be
able to access the site at http://localhost:8000 with production data.


## Running tests

```bash
uv run python manage.py test
```


## Running pre-commit hooks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

While pre-commit hooks will automatically run on GitHub after you've created a PR,
it is of course best practice to run these locally first.


## Production deployment

### First-time setup

Create the virtualenv using uv (remove any existing one first):

```bash
rm -rf ~/apps/django/env
uv venv ~/apps/django/env --python 3.14
```

Then follow the deploy steps below.

### Deploying

```bash
cd ~/apps/django
git pull
touch ~/apps/django/tmp/restart.txt
```

Run these additional steps (prior to restart) when the pull includes the relevant changes:

| Change | Command |
|---|---|
| `uv.lock` updated | `cd ~/apps/django/packman && UV_PROJECT_ENVIRONMENT=~/apps/django/env uv sync --group production` |
| New db migrations | `~/apps/django/env/bin/python packman/manage.py migrate` |
| Static files changed | `DJANGO_SETTINGS_MODULE=packman.settings.production ~/apps/django/env/bin/python packman/manage.py collectstatic --no-input` |
