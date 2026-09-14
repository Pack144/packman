import uuid

from django.db import migrations

INLINE_CMS = 7

def crlf(value):
    return "\r\n".join(value.strip().splitlines())


HOME_ANONYMOUS_BODY = crlf(
    """
<p>If you are an active P144 member and are reading this, you are currently not logged in.</p>
<p>Please log in using the 'Sign in' link in the upper right corner to access pack member content. If you need support, please use the 'contact us' page.</p>
<p>If you are interested in joining P144, please use the links above to learn more and apply. We do have a waitlist for most of our dens, and issue invitations to waitlisted kids in the spring each year. We start with the full roster in September with the start of school.</p>
"""
)

HOME_PRIVATE_BODY = crlf(
    """
<p>If you are reading this, you are logged in. You should have access to the full calendar, our pack documents, the SmugMug page, and our trackers. If you encounter any issues, please reach out to the&nbsp;<a href="https://pack144.org/committees/technology/">Technology Committee</a>.</p>
<h1><a href="https://docs.google.com/forms/d/e/1FAIpQLSeQrW4tKyFrrb2U9lpmjFmiu2zx0uKgiVvVXietmk5HpHCafA/viewform?usp=dialog">INFO: Akela Challenge</a></h1>
"""
)

JOIN_US_BODY = crlf(
    """
<p>Pack 144 is a Cub Scout Pack, historically sponsored by "A Group of Dads", in Northeast Seattle. We meet on Wednesday nights, usually at Bryant Elementary. We are very proud of <a href="../../../../../history/">our&nbsp;history</a> as the oldest Cub Scout Pack in Washington State and one of the oldest in the country.</p>
<p>We're a very active Pack, with 3 all-Pack meetings and 1 Den meeting per month, plus 3-4 weekends Campouts per year. All of our Pack activities are focused on quality Parent-Cub time. <span style="text-decoration: underline;">Parent participation is required at all meetings &amp; campouts</span>.</p>
<p>We are also a large Pack, with around 95 kids in the Pack at a time. We have boys and girls ranging from 1st to 5th grades, and most of our Cubs continue onto BSA Scouts after graduation. Unlike some Cub Scout Packs, we do not have a Lion (Kindergarten) offering.</p>
<h3>Membership Application Process</h3>
<ol>
<li>Fill out the form below to create an account on the website and tell us how to contact you.&nbsp;<em>(Existing members can skip this step)</em></li>
<li>Log into the website and select 'My Family' from the naviation bar at the top of the page.</li>
<li>Select 'Nominate a cub' to complete the application for your new Scout.</li>
<li>We will handle the rest from here. In the meantime, you can add addional family members or make updates to your application.</li>
</ol>
<h3>Important Considerations</h3>
<ul>
<li>Applications are accepted at any time during the year. Your child qualifies for Cub Scouts based on their school grade year in September of the year they would join the Pack.</li>
<li>In the spring (April-May), we will send out emails to confirm your continued interest in joining Pack 144. If you have changed your email or phone number, make sure to notify us during the year by contacting <a href="mailto:membership@pack144.org?subject=Update%20Contact%20Information">membership@pack144.org</a>.</li>
<li>We make our selection of new Scouts in early June depending on several criteria including the number of openings we have due to Scouts leaving the Pack, siblings coming into the Pack (automatic preference), length of time on the waitlist and other factors.</li>
<li>Membership confirmation/decline emails are sent by end of July. All of those on the waitlist who did not get admitted to the Pack will automatically remain on the waitlist unless you notify us otherwise.</li>
</ul>
<p><em>NOTE:&nbsp;</em>It becomes increasingly difficult to gain admittance into the Pack as your kid gets older. Once he/she is past 2nd grade, the odds of getting into the Pack drop quickly. While we would love to admit everyone into the Pack and experience what we have to offer, we can only manage so many kids at a time. We encourage you to explore other Cub Scouting options in our region. Please go to <a href="https://beascout.scouting.org/Why_Scouting/CubScout.aspx">Boy Scouts of America</a> to look up other great Cub Scout Packs in Northeast Seattle.</p>
<h3>Current Status</h3>
<p>We are starting to review our waitlist and open spots for next year. If you have previously applied, you should have received an email in May from our membership team to confirm your continued interest in Pack 144. Simply reply to that email and we will confirm your interest or remove you from the waitlist. If you did not hear from us but believe that you should have, please email us directly at <a href="mailto:membership@pack144.org?subject=Status%20Request">membership@pack144.org</a></p>
<p><em>Thank you for your interest in Pack 144.</em></p>
"""
)

COMPLIANCE_HELP_BODY = """
<p>Pack leadership keeps these records. If something looks wrong, please contact the
<a href="/committees/membership/">Membership Committee</a>. Please note that verification is done manually by the
Membership Committee and Treasurer, so updates may take some time to appear in the system.</p>
<p>Use the guidance below to complete any outstanding requirements shown above.</p>
<ul>
<li><strong>Scouting America registration</strong>
<ul>
<li>New and transferring Cub Scouts can register with Scouting America using the
<a href="https://my.scouting.org/VES/OnlineReg/1.0.0/?tu=UF-MB-609paa0144">Pack 144 Scouting America registration
page</a>.</li>
</ul>
</li>
<li><strong>Medical forms</strong>
<ul>
<li>Scouting America requires medical forms for all Cub Scouts and participating adults.</li>
<li><strong>No adult or child can camp at Blake Island without these forms.</strong></li>
<li>Submit them through the
<a href="https://forms.gle/3Ngk74CcQNh7xof7A">Pack 144 Medical Forms collection form</a>.</li>
</ul>
</li>
<li><strong>Pack dues</strong>
<ul>
<li>Please watch your inbox for a QuickBooks request to pay by ACH or credit card.</li>
<li>Check the email accounts for all parents registered with the pack, including spam folders.</li>
</ul>
</li>
<li><strong>Financial assistance</strong>
<ul>
<li>Assistance is available for uniforms and dues.</li>
<li>Email <a href="mailto:membership@pack144.org">membership@pack144.org</a> if this applies to your family.</li>
<li>Requests are kept confidential, and cost should not exclude anyone from Scouting.</li>
</ul>
</li>
</ul>
""".strip()

SEEDS = (
    {
        "page_uuid": uuid.UUID("a82785b5-1720-4c83-a69e-0a5374e1c3e1"),
        "title": "Welcome to Pack 144",
        "slug": "cms-home",
        "order": 11,
        "blocks": (
            {
                "uuid": uuid.UUID("710f094a-a22f-43c5-b6aa-e349b1bed6d8"),
                "heading": "Welcome to Pack 144",
                "visibility": "A",
                "body": HOME_ANONYMOUS_BODY,
                "order": 0,
            },
            {
                "uuid": uuid.UUID("8072af51-bfd7-48c8-a675-fbf429059fcd"),
                "heading": "Welcome, Scouts!",
                "visibility": "S",
                "body": HOME_PRIVATE_BODY,
                "order": 1,
            },
        ),
    },
    {
        "page_uuid": uuid.UUID("0a1c5658-ec92-4d97-acb3-c0c15dcffbf4"),
        "title": "Join Us",
        "slug": "cms-join-us",
        "order": 12,
        "blocks": (
            {
                "uuid": uuid.UUID("0bb679ca-bc0f-4ba0-b131-924cd7bf8ec6"),
                "heading": "",
                "visibility": "P",
                "body": JOIN_US_BODY,
                "order": 0,
            },
        ),
    },
    {
        "page_uuid": uuid.UUID("a8337e00-ecb2-4e0e-a05c-e03c329ef125"),
        "title": "Compliance Help",
        "slug": "cms-compliance-help",
        "order": 13,
        "blocks": (
            {
                "uuid": uuid.UUID("5e84063e-d598-4b93-b939-54533ab96f76"),
                "heading": "",
                "visibility": "S",
                "body": COMPLIANCE_HELP_BODY,
                "order": 0,
            },
        ),
    },
)


def seed_inline_cms_defaults(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    ContentBlock = apps.get_model("pages", "ContentBlock")

    for seed in SEEDS:
        page = Page.objects.filter(slug=seed["slug"]).first()
        if page is None:
            if Page.objects.filter(pk=seed["page_uuid"]).exists():
                raise RuntimeError(f"Cannot seed {seed['slug']}: its reserved page UUID is already in use.")
            page = Page.objects.create(
                uuid=seed["page_uuid"],
                title=seed["title"],
                slug=seed["slug"],
                nav_placement=INLINE_CMS,
                order=seed["order"],
            )
        elif page.nav_placement != INLINE_CMS:
            raise RuntimeError(f"Cannot seed {seed['slug']}: its slug belongs to a non-inline page.")

        if ContentBlock.objects.filter(page=page).exists():
            continue
        for block in seed["blocks"]:
            if ContentBlock.objects.filter(pk=block["uuid"]).exists():
                raise RuntimeError(f"Cannot seed {seed['slug']}: a reserved content UUID is already in use.")
            ContentBlock.objects.create(
                uuid=block["uuid"],
                page=page,
                heading=block["heading"],
                visibility=block["visibility"],
                body=block["body"],
                order=block["order"],
            )


def remove_seeded_inline_cms_defaults(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    ContentBlock = apps.get_model("pages", "ContentBlock")

    for seed in reversed(SEEDS):
        page = Page.objects.filter(slug=seed["slug"]).first()
        if page is None:
            continue

        unmodified_blocks = []
        for seeded_block in seed["blocks"]:
            block = ContentBlock.objects.filter(pk=seeded_block["uuid"], page=page).first()
            if block is not None and all(
                (
                    block.heading == seeded_block["heading"],
                    block.visibility == seeded_block["visibility"],
                    block.body == seeded_block["body"],
                    block.bookmark is None,
                    block.order == seeded_block["order"],
                )
            ):
                unmodified_blocks.append(block)

        page_was_seeded = page.pk == seed["page_uuid"]
        page_is_unmodified = (
            page_was_seeded
            and page.title == seed["title"]
            and page.nav_placement == INLINE_CMS
            and page.order == seed["order"]
            and ContentBlock.objects.filter(page=page).count() == len(seed["blocks"])
            and len(unmodified_blocks) == len(seed["blocks"])
        )

        if page_is_unmodified:
            page.delete()
        elif not page_was_seeded:
            for block in unmodified_blocks:
                block.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0027_inline_cms_pages"),
    ]

    operations = [
        migrations.RunPython(seed_inline_cms_defaults, remove_seeded_inline_cms_defaults),
    ]
