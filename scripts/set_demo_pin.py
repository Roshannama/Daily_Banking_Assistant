"""Interactive local setup. Never prints or persists the plaintext PIN."""
from pathlib import Path
from getpass import getpass
from argon2 import PasswordHasher
from dotenv import set_key

root=Path(__file__).resolve().parents[1]
pin=getpass('Choose a development-only PIN (4-12 digits): ')
repeat=getpass('Repeat PIN: ')
if pin!=repeat or not pin.isdigit() or not 4<=len(pin)<=12:
    raise SystemExit('PIN mismatch or invalid format. Nothing changed.')
env=root/'.env'
if not env.exists():
    env.write_text((root/'.env.example').read_text(),encoding='utf-8')
set_key(str(env),'DEMO_PIN_HASH',PasswordHasher().hash(pin))
del pin,repeat
print('Salted development PIN hash saved to .env. Restart FastAPI to apply. Use only fictional demo credentials.')
