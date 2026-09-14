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
