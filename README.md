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
`config/settings.py`. Adjust them there or, to have your own settings that are
not overridden by source updates, create a separate `.env`
file and put your custom settings there. Anything made in this file will overwrite
the project settings file. Use this to configure your own database, secret key,
email, etc.

After you've updated the settings for your own environment, it's time to populate
the database and run Django.
```
pipenv shell

python manage.py migrate

python manage.py runserver
```



## Requirements
Review the included requirements.txt for detailed package requirements.  Our
application is using:

* [Python 3.6](https://python.org)
* [Django 3.2](https://djangoproject.com)
* [Yarn](https://yarnpkg.com/)
