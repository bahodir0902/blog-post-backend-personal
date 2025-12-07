# flake8: noqa
"""
Django management command to generate mock data for Posts, Users, Categories, Comments,
CommentEditHistory and CommentReactions.

Place this file in one of your apps under `management/commands/`, for example:

    apps/posts/management/commands/generate_mock_data.py

Run with:

    python manage.py generate_mock_data

Options:
    --seed N        Set random seed for reproducible output
    --dry-run       Don't save to DB; just print counts (uses transactions rollback)

Notes:
 - This script intentionally avoids writing to Post.content (JSONField) as you requested.
 - It uses your app models at: apps.categories, apps.users, apps.posts, apps.comments
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.utils import timezone

# Adjust these numbers if you want different volumes
NUM_USERS = 50
NUM_CATEGORIES = 8
NUM_POSTS = 8
NUM_COMMENTS = 75
NUM_REACTIONS = 45

# Local imports (match your project structure)
from apps.categories.models import Category
from apps.comments.models import Comment, CommentEditHistory, CommentReaction
from apps.posts.models import Post
from apps.users.models.user import Role, User

SAMPLE_CATEGORY_NAMES = [
    "Tech",
    "Life",
    "DevOps",
    "Python",
    "Django",
    "Productivity",
    "Databases",
    "AI",
    "Career",
]

SAMPLE_TITLES = [
    "Understanding the Event Loop",
    "How to write clean Django views",
    "A short guide to indexes",
    "Why tests matter",
    "Deploying on a budget",
    "Optimizing query performance",
    "Writing maintainable migrations",
    "Handling file uploads safely",
    "Designing good serializers",
    "Refactoring for readability",
]

SAMPLE_SENTENCES = [
    "Totally agree with this approach.",
    "I found a slightly different solution using transactions.",
    "Can you explain why this is better than the previous version?",
    "Thanks for sharing — this was very helpful!",
    "I ran into an edge case where this fails.",
    "Small typo in the example, but overall good.",
    "This reminded me of a bug I had last year.",
    "Would love to see a follow-up about testing.",
    "What about performance when the dataset grows?",
    "Great write-up, saved me a lot of time.",
]

FIRST_NAMES = [f"UserFN{i}" for i in range(1, NUM_USERS)]
LAST_NAMES = [f"UserLN{i}" for i in range(1, NUM_USERS)]


def _pick_text(samples, n=1):
    return " ".join(random.choice(samples) for _ in range(n))


class Command(BaseCommand):
    help = "Generate mock data for posts, comments and reactions"

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, help="Random seed", default=None)
        parser.add_argument("--dry-run", action="store_true", help="Don't commit changes")

    def handle(self, *args, **options):
        seed = options.get("seed")
        dry_run = options.get("dry_run")
        if seed is not None:
            random.seed(seed)

        self.stdout.write(self.style.NOTICE("Starting mock data generation..."))

        # Use atomic so --dry-run can rollback
        try:
            with transaction.atomic():
                created = self._create_all()

                # If dry-run, raise to rollback; we'll print counts before rolling back
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING("Dry-run enabled: rolling back transaction.")
                    )
                    raise RuntimeError("dry-run rollback")

        except RuntimeError as e:
            if str(e) != "dry-run rollback":
                raise

        # Print summary
        self.stdout.write("")
        for k, v in created.items():
            self.stdout.write(f"{k}: {v}")

        self.stdout.write(self.style.SUCCESS("Mock data generation finished."))

    def _create_all(self):
        created = {}

        # 1) Categories
        categories = []
        cat_names = SAMPLE_CATEGORY_NAMES[:NUM_CATEGORIES]
        for name in cat_names:
            c, _ = Category.objects.get_or_create(
                name=name, defaults={"description": f"Posts about {name}."}
            )
            categories.append(c)
        created["categories"] = len(categories)

        # 2) Users
        users = []
        for i in range(NUM_USERS):
            email = f"user{i+1}@example.com"
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            # Avoid unique conflicts by using get_or_create
            user, created_flag = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_active": True,
                },
            )
            if created_flag:
                # set password using manager's create_user would also create profile, but
                # get_or_create above bypasses create_user; set_password and save.
                user.set_password("password123")
                user.save()
            users.append(user)

        created["users"] = len(users)

        # Promote a few users to authors
        num_authors = max(2, NUM_USERS // 6)
        authors = random.sample(users, num_authors)
        for u in authors:
            u.role = Role.AUTHOR
            u.save(update_fields=["role"])

        # Make sure at least one admin exists
        admin = users[0]
        admin.role = Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.email_verified = True
        admin.must_set_password = False
        admin.save(
            update_fields=[
                "role",
                "is_staff",
                "is_superuser",
                "email_verified",
                "must_set_password",
            ]
        )

        # 3) Posts
        posts = []
        for i in range(NUM_POSTS):
            title = SAMPLE_TITLES[i % len(SAMPLE_TITLES)] + f" ({i+1})"
            category = random.choice(categories)
            author = random.choice(authors)
            short_description = _pick_text(SAMPLE_SENTENCES, n=2)
            post = Post.objects.create(
                title=title,
                category=category,
                author=author,
                short_description=short_description,
                # content is intentionally left default / empty as requested
            )
            # Randomly mark some as published
            if random.random() < 0.7:
                post.status = Post.Status.PUBLISHED
                post.published_at = timezone.now() - timedelta(days=random.randint(0, 60))
                post.save(update_fields=["status", "published_at"])
            posts.append(post)

        created["posts"] = len(posts)

        # 4) Comments (including nested replies)
        comments = []
        comments_by_post = {post.id: [] for post in posts}

        # First, create a pool of top-level comments distributed across posts
        for i in range(NUM_COMMENTS):
            post = random.choice(posts)
            author = random.choice(users)
            content = _pick_text(SAMPLE_SENTENCES, n=random.randint(1, 3))
            comment = Comment.objects.create(post=post, author=author, content=content)
            comments.append(comment)
            comments_by_post[post.id].append(comment)

        # Create nested replies: for a fraction of comments, add replies (1-3 levels deep)
        extra_replies = []
        for _ in range(NUM_COMMENTS // 4):
            # choose a post, then a parent in that post
            post = random.choice(posts)
            existing_comments = comments_by_post.get(post.id) or []
            if not existing_comments:
                continue
            parent = random.choice(existing_comments)
            author = random.choice(users)
            reply = Comment.objects.create(
                post=post, author=author, content=_pick_text(SAMPLE_SENTENCES, n=1), parent=parent
            )
            comments.append(reply)
            comments_by_post[post.id].append(reply)
            extra_replies.append(reply)

        # Chance to create a reply-to-reply (deeper nesting)
        for _ in range(NUM_COMMENTS // 10):
            parent = random.choice(extra_replies) if extra_replies else None
            if not parent:
                continue
            author = random.choice(users)
            reply = Comment.objects.create(
                post=parent.post,
                author=author,
                content=_pick_text(SAMPLE_SENTENCES, n=1),
                parent=parent,
            )
            comments.append(reply)
            comments_by_post[parent.post.id].append(reply)

        created["comments_total"] = len(comments)

        # 5) Edit history: mark some comments as edited and create history rows
        num_edited = max(1, len(comments) // 8)
        edited_comments = random.sample(comments, num_edited)
        for c in edited_comments:
            prev = c.content
            new_content = prev + " (edited)"
            # create history
            CommentEditHistory.objects.create(comment=c, previous_content=prev)
            c.content = new_content
            c.is_edited = True
            c.save(update_fields=["content", "is_edited"])

        created["comments_edited"] = len(edited_comments)

        # 6) Reactions
        reactions_created = 0
        possible_reactions = [rt[0] for rt in CommentReaction.CommentReactionType.choices]
        for _ in range(NUM_REACTIONS):
            user = random.choice(users)
            comment = random.choice(comments)
            reaction = random.choice(possible_reactions)
            try:
                CommentReaction.objects.create(user=user, comment=comment, reaction=reaction)
                reactions_created += 1
            except IntegrityError:
                # user already reacted to this comment, skip
                continue

        created["reactions"] = reactions_created

        # 7) A few soft-deleted comments for testing
        num_deleted = max(0, len(comments) // 20)
        for c in random.sample(comments, num_deleted):
            c.soft_delete()

        created["comments_deleted"] = num_deleted

        return created
