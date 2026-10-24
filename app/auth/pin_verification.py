import time
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

class PinVerifier:
    def __init__(self, repository, settings):
        self.repository = repository
        self.settings = settings
        self.failures = {}  # customer-wide: creating a session cannot reset lockout
        self.hasher = PasswordHasher()

    def verify(self, customer, pin):
        count, until = self.failures.get(customer, (0, 0))
        if until > time.time():
            return 'locked'
        if until:
            count = 0
        encoded = self.repository.pin_hash(customer)
        if not encoded:
            return 'unavailable'
        try:
            valid = self.hasher.verify(encoded, pin)
        except (Argon2Error, ValueError):
            valid = False
        if valid:
            self.failures.pop(customer, None)
            return 'verified'
        count += 1
        self.failures[customer] = (count, time.time()+self.settings.pin_lock_seconds if count >= self.settings.pin_max_failures else 0)
        return 'locked' if count >= self.settings.pin_max_failures else 'invalid'
