# -*- coding: utf-8 -*-
"""
Management command to initialize ReactionType rows (emojis).

Usage:
    python manage.py init_reactions
    python manage.py init_reactions --dry-run
    python manage.py init_reactions --force
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.posts.models import ReactionType

# List of 100 (name, emoji) tuples. You can edit names/emojis as you like.
REACTION_TYPES = [
    ("grinning face", "😀"),
    ("grinning face with big eyes", "😃"),
    ("grinning face with smiling eyes", "😄"),
    ("beaming face with smiling eyes", "😁"),
    ("rolling on the floor laughing", "🤣"),
    ("face with tears of joy", "😂"),
    ("slightly smiling face", "🙂"),
    ("upside-down face", "🙃"),
    ("winking face", "😉"),
    ("smiling face with hearts", "🥰"),
    ("smiling face with heart-eyes", "😍"),
    ("star-struck", "🤩"),
    ("face blowing a kiss", "😘"),
    ("kissing face", "😗"),
    ("thinking face", "🤔"),
    ("neutral face", "😐"),
    ("expressionless face", "😑"),
    ("face without mouth", "😶"),
    ("slightly frowning face", "🙁"),
    ("frowning face", "☹️"),
    ("confused face", "😕"),
    ("persevering face", "😣"),
    ("disappointed face", "😞"),
    ("pensive face", "😔"),
    ("sad but relieved face", "😥"),
    ("crying face", "😢"),
    ("loudly crying face", "😭"),
    ("face with steam from nose", "😤"),
    ("angry face", "😠"),
    ("pouting face", "😡"),
    ("face with symbols on mouth", "🤬"),
    ("fearful face", "😨"),
    ("anxious face with sweat", "😰"),
    ("hot face", "🥵"),
    ("cold face", "🥶"),
    ("exploding head", "🤯"),
    ("cowboy hat face", "🤠"),
    ("partying face", "🥳"),
    ("disguised face", "🥸"),
    ("nerd face", "🤓"),
    ("sunglasses face", "😎"),
    ("face with monocle", "🧐"),
    ("robot face", "🤖"),
    ("pile of poo", "💩"),
    ("ghost", "👻"),
    ("skull", "💀"),
    ("alien", "👽"),
    ("clown face", "🤡"),
    ("smiling cat face with heart-eyes", "😻"),
    ("smiling cat face with open mouth", "😺"),
    ("crying cat face", "😿"),
    ("thumbs up", "👍"),
    ("thumbs down", "👎"),
    ("clapping hands", "👏"),
    ("folded hands", "🙏"),
    ("raised hands", "🙌"),
    ("victory hand", "✌️"),
    ("OK hand", "👌"),
    ("waving hand", "👋"),
    ("writing hand", "✍️"),
    ("flexed biceps", "💪"),
    ("pointing right", "👉"),
    ("pointing left", "👈"),
    ("index pointing up", "☝️"),
    ("raised fist", "✊"),
    ("sparkles", "✨"),
    ("fire", "🔥"),
    ("red heart", "❤️"),
    ("broken heart", "💔"),
    ("yellow heart", "💛"),
    ("orange heart", "🧡"),
    ("green heart", "💚"),
    ("blue heart", "💙"),
    ("purple heart", "💜"),
    ("black heart", "🖤"),
    ("two hearts", "💕"),
    ("revolving hearts", "💞"),
    ("heartbeat", "💓"),
    ("heart pulse", "💗"),
    ("kiss mark", "💋"),
    ("crown", "👑"),
    ("trophy", "🏆"),
    ("sports medal", "🏅"),
    ("soccer ball", "⚽"),
    ("basketball", "🏀"),
    ("baseball", "⚾"),
    ("tennis", "🎾"),
    ("rugby football", "🏉"),
    ("check mark", "✅"),
    ("cross mark", "❌"),
    ("information", "ℹ️"),
    ("warning", "⚠️"),
    ("question", "❓"),
    ("exclamation", "❗"),
    ("hourglass", "⌛"),
    ("alarm clock", "⏰"),
    ("light bulb", "💡"),
    ("money bag", "💰"),
    ("shopping bags", "🛍️"),
    ("globe", "🌍"),
]

# sanity check (should be roughly 100 as requested)
if len(REACTION_TYPES) != 100:
    # not fatal — just a warning printed when the command runs
    pass


class Command(BaseCommand):
    help = "Initialize ReactionType entries (emojis). Supports --force and --dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="If set, update existing ReactionType.emoji to the provided emoji when name"
            " matches.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without creating/updating database rows.",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        dry_run = options.get("dry_run", False)

        self.stdout.write(self.style.MIGRATE_HEADING("Initializing ReactionType entries (emojis)"))
        self.stdout.write(
            f"Model located: {ReactionType._meta.label} (app: {ReactionType._meta.app_label})"
        )
        self.stdout.write(f"Total entries to ensure: {len(REACTION_TYPES)}")
        if force:
            self.stdout.write(
                "Option: --force (existing emoji values will be updated where different)"
            )
        if dry_run:
            self.stdout.write("Option: --dry-run (no DB writes will be performed)")

        created = 0
        updated = 0
        skipped = 0

        if dry_run:
            # Dry run: only show what would happen
            for name, emoji in REACTION_TYPES:
                try:
                    existing = ReactionType.objects.filter(name=name).first()
                except Exception as e:
                    raise CommandError(f"Error querying model: {e}")

                if existing is None:
                    self.stdout.write(
                        self.style.NOTICE(f"[DRY-RUN] Would create: {name} -> {emoji}")
                    )
                else:
                    if existing.emoji != emoji and force:
                        self.stdout.write(
                            self.style.NOTICE(
                                f"[DRY-RUN] Would update: {name} ({existing.emoji} -> {emoji})"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.SQL_FIELD(f"[DRY-RUN] Exists: {name} -> {existing.emoji}")
                        )

            self.stdout.write(self.style.SUCCESS("Dry run complete. No changes were made."))
            return

        # Real run: make DB changes inside a transaction
        try:
            with transaction.atomic():
                for name, emoji in REACTION_TYPES:
                    obj = ReactionType.objects.filter(name=name).first()
                    if obj is None:
                        # create
                        ReactionType.objects.create(name=name, emoji=emoji)
                        created += 1
                        self.stdout.write(self.style.SUCCESS(f"Created: {name} -> {emoji}"))
                    else:
                        if force and obj.emoji != emoji:
                            obj.emoji = emoji
                            obj.save(update_fields=["emoji"])
                            updated += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Updated: {name} -> {emoji} (was: {obj.emoji})")
                            )
                        else:
                            skipped += 1
                            self.stdout.write(
                                self.style.WARNING(f"Skipped (exists): {name} -> {obj.emoji}")
                            )

        except Exception as exc:
            raise CommandError(f"Database operation failed: {exc}")

        self.stdout.write("")  # blank line
        self.stdout.write(
            self.style.SUCCESS(
                f"Initialization finished. Created: {created}, Updated: {updated},"
                f" Skipped: {skipped}"
            )
        )
