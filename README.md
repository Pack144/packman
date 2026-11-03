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

Either start with a blank database:

```bash
mkdir -p .local
uv run python manage.py migrate
```

Or pull a fresh copy of the beta database and configured media files instead:

```bash
./util/packman.sh dev sync
```

Use `./util/packman.sh dev sync --sync-env prod` to sync from production.

### Optional Caddy setup

Install and start Caddy on macOS when you want to use the `packman.localhost` route:

```sh
brew install caddy
```

Create the Homebrew Caddy configuration directory and seed the basic config.

```sh
mkdir -p "$(brew --prefix)/etc"
cat >"$(brew --prefix)/etc/Caddyfile" <<'EOF'
{
	admin 127.0.0.1:2019
	auto_https off
}

http://localhost {
	respond "Caddy is running" 200
}
EOF
```

Start Caddy as a Homebrew service so `launchd` restarts it after login or reboot:

```sh
brew services start caddy
```

### Run the development server


```bash
./util/packman.sh dev start
```


Stop the server with:

```bash
./util/packman.sh dev stop
```

If Caddy is installed and its background service is running, open
`http://packman.localhost`. Without Caddy, the launcher prints the direct
`http://localhost:PORT` URL.


## Requirements

* [Python 3.14](https://python.org)
* [Django 5.2](https://djangoproject.com)
* [npm](https://www.npmjs.com/)


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
uv venv ~/apps/django-beta/env --python 3.14
```

### Deploying

Deployment should first be validated in beta prior to deploying in prod.
Deploys normally run through the [Deploy](.github/workflows/deploy.yml)
GitHub Actions workflow, which SSHes into the target server, checks out the
selected branch, and runs [util/server/deploy.sh](util/server/deploy.sh).

#### Deploying from the command line

The deploy command requires the GitHub CLI, installed and authenticated:

```bash
brew install gh
gh auth login
```

Deploy the current branch to beta. This fails if your workspace has
uncommitted changes or is ahead of or behind the branch on origin:

```bash
./util/packman.sh beta deploy
```

Deploy a different branch to beta. Whatever is on origin for that branch is
deployed; your local copy of it is not checked:

```bash
./util/packman.sh beta deploy --branch my-branch
```

Deploy `main` to beta after replacing beta's database with a copy of prod:

```bash
./util/packman.sh beta deploy --branch main --reset-db
```

Deploy `main` to prod. The command refuses to deploy any other branch to prod
(use the GitHub Actions UI for that). It also requires that CI passed on the
latest `origin/main` commit, and asks you to confirm (`--yes` skips the
prompt). Validate the change on beta first:

```bash
./util/packman.sh prod deploy --branch main
```

The command prints the workflow run URL and waits for the run to finish. Other
useful options:

* `--dry-run` — run the checks and print the `gh` command without deploying.
* `--compact` — show only relevant or failed steps while waiting.
* `--force` — deploy despite workspace warnings.

#### Deploying via the GitHub Actions UI

Go to the *Actions* tab, select the Deploy workflow, click *Run workflow*,
pick the branch to deploy, and choose the `target` environment (`beta` or
`prod`). This is the only way to deploy a branch other than `main` to prod.

When deploying to `beta`, you can also check the `reset_db` option to first
wipe beta's database and replace it with a fresh copy of production (via
[sync_beta_db.sh](util/server/sync_beta_db.sh)) before deploying — handy for
refreshing beta with production data and the latest `main` in one run.

The workflow requires the following secrets to be configured.
* `SERVICE_HOST` — SSH host for the target server
* `SERVICE_SSH_USERNAME` — SSH username
* `SERVICE_AUTHORIZED_SSH_KEY` — private key with access to the target deployment
* `SERVICE_SSH_PORT` — *(optional)* SSH port, defaults to `22`
* `SERVICE_APP_DIR` — app directory on the server to deploy

#### Deploying manually

If GitHub Actions is unavailable, SSH into the server and run the deploy
script directly (repeat in the prod directory after validating beta):

```bash
cd ~/apps/django-beta/packman
git pull
util/server/deploy.sh ~/apps/django-beta
```
