from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class InlineCmsMigrationTests(TransactionTestCase):
    migrate_from = ("pages", "0026_page_nav_placement")
    migrate_to = ("pages", "0027_inline_cms_pages")

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        Page = old_apps.get_model("pages", "Page")
        ContentBlock = old_apps.get_model("pages", "ContentBlock")

        home = Page.objects.create(title="Custom Home", slug="welcome", nav_placement=4)
        signup = Page.objects.create(title="Join the Pack", slug="apply", nav_placement=5)
        ContentBlock.objects.create(page=home, body="<p>Home body</p>", visibility="P")
        ContentBlock.objects.create(page=signup, body="<p>Join body</p>", visibility="P")

        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_to])
        self.apps = self.executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_migrates_home_and_signup_pages_to_inline_cms(self):
        Page = self.apps.get_model("pages", "Page")

        home = Page.objects.get(slug="cms-home")
        signup = Page.objects.get(slug="cms-join-us")

        self.assertEqual(home.nav_placement, 7)
        self.assertEqual(signup.nav_placement, 7)
        self.assertEqual(home.content_blocks.get().body, "<p>Home body</p>")
        self.assertEqual(signup.content_blocks.get().body, "<p>Join body</p>")

    def test_reverse_restores_standard_placements(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        Page = old_apps.get_model("pages", "Page")

        self.assertTrue(Page.objects.filter(nav_placement=4, slug="home").exists())
        self.assertTrue(Page.objects.filter(nav_placement=5, slug="signup").exists())


class InlineCmsDefaultsMigrationTests(TransactionTestCase):
    migrate_from = ("pages", "0027_inline_cms_pages")
    migrate_to = ("pages", "0028_seed_inline_cms_defaults")

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_from])
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_to])
        self.apps = self.executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_seeds_all_inline_cms_defaults(self):
        Page = self.apps.get_model("pages", "Page")

        home = Page.objects.get(slug="cms-home")
        signup = Page.objects.get(slug="cms-join-us")
        compliance = Page.objects.get(slug="cms-compliance-help")

        self.assertEqual(home.nav_placement, 7)
        self.assertEqual(home.title, "Welcome to Pack 144")
        self.assertEqual(home.order, 11)
        self.assertEqual(home.content_blocks.count(), 2)
        self.assertEqual(
            list(home.content_blocks.values_list("heading", "visibility", "order")),
            [("Welcome to Pack 144", "A", 0), ("Welcome, Scouts!", "S", 1)],
        )
        self.assertIn("currently not logged in", home.content_blocks.get(order=0).body)
        self.assertIn("INFO: Akela Challenge", home.content_blocks.get(order=1).body)

        self.assertEqual(signup.nav_placement, 7)
        self.assertEqual(signup.title, "Join Us")
        self.assertEqual(signup.order, 12)
        self.assertEqual(signup.content_blocks.get().heading, "")
        self.assertEqual(signup.content_blocks.get().visibility, "P")
        self.assertIn("Membership Application Process", signup.content_blocks.get().body)

        self.assertEqual(compliance.nav_placement, 7)
        self.assertEqual(compliance.content_blocks.get().heading, "")
        self.assertEqual(compliance.content_blocks.get().visibility, "S")
        self.assertIn('href="/committees/membership/"', compliance.content_blocks.get().body)
        self.assertIn("QuickBooks request", compliance.content_blocks.get().body)
        self.assertNotIn("$144", compliance.content_blocks.get().body)
        self.assertLess(
            compliance.content_blocks.get().body.index("Pack leadership keeps these records"),
            compliance.content_blocks.get().body.index("Use the guidance below"),
        )

    def test_reverse_removes_unmodified_seeded_entries(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        Page = old_apps.get_model("pages", "Page")

        self.assertFalse(Page.objects.filter(slug__in=("cms-home", "cms-join-us", "cms-compliance-help")).exists())


class ExistingInlineCmsDefaultsMigrationTests(TransactionTestCase):
    migrate_from = ("pages", "0027_inline_cms_pages")
    migrate_to = ("pages", "0028_seed_inline_cms_defaults")

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        Page = old_apps.get_model("pages", "Page")
        ContentBlock = old_apps.get_model("pages", "ContentBlock")

        home = Page.objects.create(title="Custom Home", slug="cms-home", nav_placement=7)
        ContentBlock.objects.create(page=home, body="<p>Custom home</p>", visibility="P")
        Page.objects.create(title="Custom Join Us", slug="cms-join-us", nav_placement=7)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_to])
        self.apps = self.executor.loader.project_state([self.migrate_to]).apps

    def tearDown(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_preserves_populated_entry_and_fills_empty_entry(self):
        Page = self.apps.get_model("pages", "Page")

        home = Page.objects.get(slug="cms-home")
        signup = Page.objects.get(slug="cms-join-us")

        self.assertEqual(home.content_blocks.get().body, "<p>Custom home</p>")
        self.assertEqual(signup.title, "Custom Join Us")
        self.assertIn("Membership Application Process", signup.content_blocks.get().body)

    def test_reverse_preserves_existing_and_edited_content(self):
        Page = self.apps.get_model("pages", "Page")
        signup = Page.objects.get(slug="cms-join-us")
        signup_block = signup.content_blocks.get()
        signup_block.body = "<p>Edited instructions</p>"
        signup_block.save(update_fields=["body"])

        self.executor = MigrationExecutor(connection)
        self.executor.migrate([self.migrate_from])
        old_apps = self.executor.loader.project_state([self.migrate_from]).apps
        Page = old_apps.get_model("pages", "Page")

        self.assertEqual(Page.objects.get(slug="cms-home").content_blocks.get().body, "<p>Custom home</p>")
        self.assertEqual(Page.objects.get(slug="cms-join-us").content_blocks.get().body, "<p>Edited instructions</p>")
        self.assertFalse(Page.objects.filter(slug="cms-compliance-help").exists())
