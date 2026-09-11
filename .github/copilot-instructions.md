# Packman repository instructions

## Project map

- Packman is a Python 3.14, Django 5.2 application. Use `uv` for Python
  dependencies and commands; do not introduce an alternative environment or
  dependency manager.
- Django apps live under `packman/<app>/`. Keep models, managers, forms, views,
  URLs, admin configuration, templates, static assets, and management commands
  in the app that owns the behavior.
- Tests mirror the application layout under `tests/<app>/`. Reuse the existing
  Factory Boy factories in `packman/<app>/factories.py` when available.
- Shared templates and static assets live in `packman/templates/` and
  `packman/static/`. The mobile PWA and REST API live in `packman/mobile/`.
- Settings are split across `packman/settings/`; defaults belong in `base.py`
  and environment-specific overrides belong in the corresponding settings
  module.

## Local development

- Use `./util/start_local.sh` as the canonical way to start the development
  server. It prepares `.env`, reuses dependencies from the main checkout when
  running in a worktree, syncs Python and npm dependencies, applies pending
  migrations, and starts Django on port 8000.
- When a task needs the running site or visual verification, start
  `./util/start_local.sh --detach` directly rather than asking the user to run
  it. Confirm the site is reachable before relying on it.
- If another Packman server from this checkout occupies port 8000, ask whether
  to rerun with `--kill-existing` or use `--port <port>`. If an unrelated
  process owns the port, ask whether to terminate the exact PID outside the
  script or use another port. Never terminate a process or use
  `--kill-existing` without approval. Use `--no-install` or `--no-migrate` only
  when intentionally skipping those setup steps.
- Do not duplicate the script's environment, dependency, or migration setup
  with a sequence of ad hoc commands unless the script fails and the failure is
  being diagnosed.

## Implementation conventions

- Follow existing Django patterns before adding abstractions. Put reusable data
  selection and aggregation in custom QuerySets/managers rather than duplicating
  ORM expressions across views, reports, admin, and templates.
- Preserve authorization and family/member scoping when changing querysets or
  endpoints. Packman contains private youth and family data: do not expose it
  through broader queries, API serializers, logs, fixtures, or error output.
- Use timezone-aware Django APIs (`django.utils.timezone`) for application dates
  and times. Account for the configured `America/Los_Angeles` timezone when a
  calendar date is derived from a timestamp.
- Use `gettext`/`gettext_lazy` and Django template translation tags for
  user-facing text. Keep templates accessible and consistent with the existing
  Bootstrap 5 markup, including labels, semantic elements, and ARIA attributes.
- Prefer server-rendered Django behavior. For mobile changes, keep the REST
  serializer/API, JavaScript client, screen components, service worker, and
  tests consistent where the data contract crosses those layers.
- When changing a model, create and commit the Django migration. Do not edit an
  applied migration to represent a new schema change. Add data-migration tests
  when transformed production data or historical model state matters.
- Avoid unrelated formatting or modernization. Python is formatted with Black
  and isort at 119 columns; Django templates use djLint with 2-space
  indentation. Migrations are excluded from routine formatters.

## Tests and validation

- Add or update focused Django tests for changed behavior, including permissions,
  queryset boundaries, and rendered/API output where relevant. Prefer Django's
  `TestCase`, `self.client`, named URL reversal, and existing factories.
- Run the narrowest relevant test module first, for example:
  `uv run python manage.py test tests.campaigns.test_reports`.
- Before completing a change, run `uv run pre-commit run --all-files`; run the
  full `uv run python manage.py test` suite when the change is cross-cutting or
  the focused tests do not provide sufficient coverage.
