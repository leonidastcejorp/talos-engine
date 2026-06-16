"""
Talos Engine - Identity Generator

Generates realistic synthetic identities (name, email, password, DOB)
for account creation automation.
"""

import random
import string
from dataclasses import dataclass
from typing import List


@dataclass
class Identity:
    """A synthetic identity for account registration."""
    username: str
    email: str
    password: str
    birth_date: str  # MM/DD/YYYY
    first_name: str = ""
    last_name: str = ""


class IdentityGenerator:
    """Generates realistic but synthetic identities."""

    # Common first names (gender-neutral selection)
    FIRST_NAMES = [
        "alex", "jordan", "casey", "morgan", "riley", "taylor",
        "quinn", "avery", "blake", "cameron", "dakota", "emerson",
        "finley", "hayden", "jesse", "kendall", "logan", "parker",
        "reese", "skyler", "jamie", "charlie", "sam", "drew",
        "bailey", "harper", "peyton", "sawyer", "rowan", "ashton",
    ]

    # Animal/weather themed surnames
    LAST_NAMES = [
        "storm", "wolf", "fox", "hawk", "frost", "shadow", "phoenix",
        "raven", "hunter", "flint", "slate", "ash", "stone", "thunder",
        "blaze", "ember", "cipher", "onyx", "forge", "shade",
    ]

    # Free email domains
    EMAIL_DOMAINS = [
        "gmail.com", "outlook.com", "proton.me", "yahoo.com",
    ]

    @classmethod
    def generate(cls) -> Identity:
        """Generate a single synthetic identity."""
        first = random.choice(cls.FIRST_NAMES).capitalize()
        last = random.choice(cls.LAST_NAMES).capitalize()

        # Username generation
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        username = f"{first.lower()}_{last.lower()}_{suffix}"

        # Email
        domain = random.choice(cls.EMAIL_DOMAINS)
        email = f"{username}@{domain}"

        # Password
        password = cls._generate_password()

        # Birth date (ages 20-35)
        birth_date = cls._generate_birth_date()

        return Identity(
            username=username,
            email=email,
            password=password,
            birth_date=birth_date,
            first_name=first,
            last_name=last,
        )

    @classmethod
    def batch(cls, count: int) -> List[Identity]:
        """Generate multiple identities."""
        return [cls.generate() for _ in range(count)]

    @staticmethod
    def _generate_password(length: int = 16) -> str:
        """Generate a secure random password."""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(random.choices(chars, k=length))

    @staticmethod
    def _generate_birth_date() -> str:
        """Generate a random birth date between ages 20-35."""
        import datetime
        today = datetime.date.today()
        year = today.year - random.randint(20, 35)
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Safe for all months
        return f"{month:02d}/{day:02d}/{year}"
