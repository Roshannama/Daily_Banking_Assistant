import re

def deny_reason(message, customer):
    ids = re.findall(r'\bC\d{4}\b', message.upper())
    if any(i != customer for i in ids):
        return 'I can only help with records belonging to your authenticated customer session.'
    if re.search(r"\b(pin|password|secret|token|api.?key|otp)\b\s*(?:is|=|:)\s*\S+", message, re.I) or re.search(r'\b(pin|otp)\b.{0,30}\d{4,12}',message,re.I) or re.fullmatch(r'\s*\d{4,12}\s*', message):
        return 'Enter authentication values only in the secure PIN form, never in chat.'
    if re.search(r'ignore (?:all |previous |the )?instructions|system prompt|pin hash|password|bypass|session token|audit (?:trail|logs)|other customer|someone else|guaranteed (?:return|profit)|hack|steal|kill|racial|hate speech', message, re.I):
        return 'I cannot provide private credentials, bypass bank controls, or assist with unsafe requests. Contact an authorized bank employee for exceptional cases.'
    return None

def safe_history(message):
    if re.search(r'\b(pin|password|secret|token|otp|api.?key)\b', message, re.I) or re.search(r'\b\d{4,}\b', message):
        return '[Sensitive input omitted]'
    return message
