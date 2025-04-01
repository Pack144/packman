# Generated by Django 2.2.14 on 2020-07-30 16:34

from django.db import migrations, models
import django.db.models.deletion
import easy_thumbnails.fields
import packman.membership.managers
import packman.membership.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("dens", "0001_initial"),
        ("auth", "0011_update_proxy_permissions"),
        ("address_book", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Family",
            fields=[
                ("name", models.CharField(blank=True, max_length=64, null=True)),
                (
                    "pack_comments",
                    models.TextField(
                        blank=True,
                        help_text="Used by pack leadership to keep notes about a specific family. This information is not generally disclosed to members unless they are granted access to Membership.",
                        null=True,
                        verbose_name="Pack Comments",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "legacy_id",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, unique=True
                    ),
                ),
                ("date_added", models.DateField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Family",
                "verbose_name_plural": "Families",
                "ordering": ["date_added"],
            },
        ),
        migrations.CreateModel(
            name="Member",
            fields=[
                (
                    "first_name",
                    models.CharField(max_length=30, verbose_name="First Name"),
                ),
                (
                    "middle_name",
                    models.CharField(
                        blank=True, max_length=32, null=True, verbose_name="Middle Name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(max_length=150, verbose_name="Last Name"),
                ),
                (
                    "suffix",
                    models.CharField(
                        blank=True, max_length=8, null=True, verbose_name="Suffix"
                    ),
                ),
                (
                    "nickname",
                    models.CharField(
                        blank=True,
                        help_text="If there is another name you prefer to be called, tell us and we will use it any time we refer to you on the website.",
                        max_length=32,
                        null=True,
                        verbose_name="Nickname",
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        choices=[
                            ("M", "Male"),
                            ("F", "Female"),
                            ("O", "Prefer not to say"),
                        ],
                        default=None,
                        max_length=1,
                        null=True,
                        verbose_name="Gender",
                    ),
                ),
                (
                    "photo",
                    easy_thumbnails.fields.ThumbnailerImageField(
                        blank=True,
                        help_text="We use member photos on the website to help match names with faces.",
                        null=True,
                        upload_to=packman.membership.models.get_photo_path,
                        verbose_name="Headshot Photo",
                    ),
                ),
                (
                    "date_of_birth",
                    models.DateField(blank=True, null=True, verbose_name="Birthday"),
                ),
                ("slug", models.SlugField(blank=True, null=True, unique=True)),
                (
                    "pack_comments",
                    models.TextField(
                        blank=True,
                        help_text="Used by pack leadership to keep notes about a specific member. This information is not generally disclosed to the member unless they are granted access to Membership.",
                        null=True,
                        verbose_name="Pack Comments",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("date_added", models.DateTimeField(auto_now_add=True)),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["last_name", "nickname", "first_name"],
            },
        ),
        migrations.CreateModel(
            name="Adult",
            fields=[
                (
                    "member_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="membership.Member",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=254, unique=True, verbose_name="Email Address"
                    ),
                ),
                (
                    "is_published",
                    models.BooleanField(
                        default=True,
                        help_text="Display this address to other members of the pack.",
                        verbose_name="Published",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("P", "Parent"),
                            ("G", "Guardian"),
                            ("C", "Friend of the Pack"),
                        ],
                        default="P",
                        max_length=1,
                        verbose_name="Role",
                    ),
                ),
                (
                    "_is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="Staff",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="Active",
                    ),
                ),
            ],
            options={
                "verbose_name": "Adult",
                "verbose_name_plural": "Adults",
                "ordering": ["last_name", "nickname", "first_name"],
            },
            bases=("membership.member", models.Model),
            managers=[
                ("objects", packman.membership.managers.MemberManager()),
            ],
        ),
        migrations.CreateModel(
            name="Scout",
            fields=[
                (
                    "member_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="membership.Member",
                    ),
                ),
                (
                    "reference",
                    models.CharField(
                        blank=True,
                        help_text="If you know someone who is already in the pack, you can tell us their name so we can credit them for referring you.",
                        max_length=128,
                        null=True,
                        verbose_name="Referral(s)",
                    ),
                ),
                (
                    "member_comments",
                    models.TextField(
                        blank=True,
                        help_text="What other information should we consider when reviewing your application?",
                        null=True,
                        verbose_name="Comments",
                    ),
                ),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Application Withdrawn"),
                            (1, "Applied"),
                            (2, "Denied"),
                            (3, "Approved"),
                            (4, "Active"),
                            (5, "Inactive"),
			    (6, "Graduated"),
                            (7, "Waitlist"),
                        ],
                        default=1,
                        help_text="What is the Cub's current status? A new cub who has not been reviewed will start as 'Applied'. Membership can choose then to approve or decline the application, or make them active. Once a Cub is no longer active in the pack, either through graduation or attrition, note that change' here. Any adult member connected to this Cub will get access only once the Cub's status is 'Active' or 'Approved'.",
                        verbose_name="Status",
                    ),
                ),
                (
                    "started_school",
                    models.PositiveSmallIntegerField(
                        help_text="What year did your child start kindergarten? We use this to calculate their grade year in school and assign your child to an appropriate den.",
                        null=True,
                        verbose_name="Kindergarten Year",
                    ),
                ),
                (
                    "started_pack",
                    models.DateField(
                        blank=True,
                        help_text="When does this cub join their first activity with the pack?",
                        null=True,
                        verbose_name="Date Started",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cub",
                "verbose_name_plural": "Cubs",
            },
            bases=("membership.member",),
        ),
        migrations.AddIndex(
            model_name="member",
            index=models.Index(
                fields=["first_name", "middle_name", "nickname", "last_name", "gender"],
                name="membership__first_n_e5db24_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="family",
            index=models.Index(fields=["name"], name="membership__name_2becb1_idx"),
        ),
        migrations.AddField(
            model_name="scout",
            name="dens",
            field=models.ManyToManyField(
                blank=True, through="dens.Membership", to="dens.Den"
            ),
        ),
        migrations.AddField(
            model_name="scout",
            name="family",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="membership.Family",
            ),
        ),
        migrations.AddField(
            model_name="scout",
            name="school",
            field=models.ForeignKey(
                blank=True,
                help_text="Tell us what school your child attends. If your school isn't listed, tell us in the comments section.",
                limit_choices_to={"type__type__icontains": "School"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="address_book.Venue",
            ),
        ),
        migrations.AddField(
            model_name="adult",
            name="family",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="adults",
                to="membership.Family",
            ),
        ),
        migrations.AddField(
            model_name="adult",
            name="groups",
            field=models.ManyToManyField(
                blank=True,
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                related_name="user_set",
                related_query_name="user",
                to="auth.Group",
                verbose_name="groups",
            ),
        ),
        migrations.AddField(
            model_name="adult",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.Permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.AddIndex(
            model_name="scout",
            index=models.Index(
                fields=["school", "family", "status", "started_school"],
                name="membership__school__97a599_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="adult",
            index=models.Index(
                fields=["role", "email", "family"], name="membership__role_589eeb_idx"
            ),
        ),
    ]
