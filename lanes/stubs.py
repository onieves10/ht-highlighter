"""
Stubbed lanes — labeled placeholders so the demo runs on one paid key. Each
points at the real prompt/config it would use in production. Returns are
strings that synthesis treats as empty lanes (and logs as gaps).
"""


def news(domain, account_name=None):
    return ("STUBBED news lane — production: Perplexity Sonar Pro "
            "(see prompts/news_perplexity.md).")


def site(domain, account_name=None):
    return ("STUBBED site lane — production: Firecrawl "
            "(see prompts/site_firecrawl.md).")


def clay_account(domain, account_name=None):
    return ("STUBBED account-LinkedIn lane — production: Clay/Claygent "
            "(see prompts/linkedin_claygent.md).")


def clay_prospect(contact, account_name=None):
    return ("STUBBED prospect-LinkedIn lane — production: Clay/Claygent "
            "(see prompts/linkedin_claygent.md).")
