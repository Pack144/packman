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

- Use `./util/packman.sh dev start` as the canonical way to start the
  development server. It checks and installs Python and npm dependencies as
  needed, applies pending migrations, and starts Django on port 8000 by default.
  Use `./util/packman.sh dev stop` to stop this checkout's server.
- For browser or end-to-end testing, find the local test account email and
  password in `.env` under `SYNC_RESET_PW_EMAIL` and `SYNC_RESET_PW`.
- When a task needs the running site or visual verification, start
  `./util/packman.sh dev start --detach` directly rather than asking the user
  to run it. Confirm the site is reachable before relying on it. Caddy is
  optional; without it, use the direct `http://localhost:8000` URL.
- Do not duplicate the script's environment, dependency, or migration setup
  with a sequence of ad hoc commands unless the script fails and the failure is
  being diagnosed.
- The Django admin is mounted at `/administration/`, not `/admin/`.

## Beta deployment

- Only deploy to beta when the user explicitly asks to deploy the current
  change. A request to deploy one change is not permission to deploy later
  changes.
- Deploy the pushed branch with
  `./util/packman.sh beta deploy --branch <branch> --compact`. It runs safety
  checks, triggers the Deploy workflow, and waits for it to finish. Use
  `--dry-run` to run only the checks.
- Never deploy to prod.
- Never pass `--force` or `--reset-db` unless the user explicitly requests it.
  If a check blocks the deploy, report the warnings to the user instead of
  bypassing them.
- Do not spend time checking for competing deployments; the workflow queues
  deploys to the same environment.
- Report the `Run URL:` line and the result.

## Implementation conventions

- Follow existing Django patterns before adding abstractions. Put reusable data
  selection and aggregation in custom QuerySets/managers rather than duplicating
  ORM expressions across views, reports, admin, and templates.
- Before implementing UI behavior such as sorting, filtering, downloads,
  navigation, or interactive controls, make a quick, targeted search of likely
  templates, JavaScript, and CSS for relevant patterns and data attributes.
  Reuse an established approach when it fits the new behavior cleanly, but do
  not spend significant time searching or force reuse when a different
  implementation would be clearer or better suited to the task.
- Preserve authorization and family/member scoping when changing querysets or
  endpoints. Packman contains private youth and family data: do not expose it
  through broader queries, API serializers, logs, fixtures, or error output.
- Use timezone-aware Django APIs (`django.utils.timezone`) for application dates
  and times. Account for the configured `America/Los_Angeles` timezone when a
  calendar date is derived from a timestamp.
- Use `gettext`/`gettext_lazy` and Django template translation tags for
  user-facing text. Keep templates accessible and consistent with the existing
  Bootstrap 5 markup, including labels, semantic elements, and ARIA attributes.
- For guidance above an admin changelist, override the `object-tools` block,
  render `{{ block.super }}` first, and place the guidance after it with
  `clear: both` so the Add button cannot overlap the guidance.
- Style admin guidance with Django admin's existing patterns. Use ordinary help
  text by default. Only use `ul.messagelist` with an `info` or `warning` item
  when the guidance needs extra prominence, reserving warnings for cautions.
  Give longer notices a short, bold heading on its own line, followed by concise
  prose. Avoid bespoke CSS when admin classes and variables provide the needed
  presentation.
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
