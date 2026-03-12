#!/usr/bin/env python3
"""
LinkedIn Email Harvester - OSINT Recon Tool
For authorised penetration testing and security research only.

Sources:
  1. Google dorking LinkedIn (no auth required)
  2. Manual name input
  3. Names from a flat text file

Usage:
    python3 linkedin_email_harvest.py --company "Acme Corp" --domain acme.com
    python3 linkedin_email_harvest.py --company "Acme Corp" --domain acme.com --format firstname.lastname
    python3 linkedin_email_harvest.py --names names.txt --domain acme.com
    python3 linkedin_email_harvest.py --manual --domain acme.com
"""

import argparse
import sys
import re
import time
import random
import unicodedata
import urllib.parse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("[!] Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)


# ─── Email format templates ───────────────────────────────────────────────────

EMAIL_FORMATS = {
    "firstname.lastname":   lambda f, l: f"{f}.{l}",
    "f.lastname":           lambda f, l: f"{f[0]}.{l}",
    "firstnamelastname":    lambda f, l: f"{f}{l}",
    "flastname":            lambda f, l: f"{f[0]}{l}",
    "firstname":            lambda f, l: f"{f}",
    "lastname.firstname":   lambda f, l: f"{l}.{f}",
    "firstname_lastname":   lambda f, l: f"{f}_{l}",
    "f_lastname":           lambda f, l: f"{f[0]}_{l}",
    "lastname":             lambda f, l: f"{l}",
    "firstnamel":           lambda f, l: f"{f}{l[0]}",
}

COMMON_FORMATS = [
    "firstname.lastname",
    "f.lastname",
    "firstnamelastname",
    "flastname",
    "firstname_lastname",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def normalise(name: str) -> str:
    """Strip accents, lowercase, keep only alpha."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", ascii_str.lower())


def parse_full_name(full_name: str):
    """Return (first, last) normalised strings. Handles middle names."""
    parts = full_name.strip().split()
    if len(parts) < 2:
        return normalise(parts[0]), ""
    return normalise(parts[0]), normalise(parts[-1])


def build_emails(first: str, last: str, domain: str, formats: list) -> list:
    """Generate email addresses for the given name and formats."""
    emails = []
    if not first or not last:
        return emails
    for fmt in formats:
        fn = EMAIL_FORMATS.get(fmt)
        if fn:
            local = fn(first, last)
            emails.append(f"{local}@{domain}")
    return emails


# ─── Google-dork LinkedIn scraper ─────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

def google_dork_linkedin(company: str, max_pages: int = 3) -> set:
    """
    Use Google to find LinkedIn /in/ profile URLs for a company.
    Parses names from <title> tags. No LinkedIn auth required.
    Rate-limited to avoid triggering CAPTCHA.
    """
    names = set()
    query = f'site:linkedin.com/in/ "{company}"'

    print(f"\n[*] Google dorking LinkedIn for: {company}")
    print(f"    Query: {query}\n")

    for page in range(max_pages):
        start = page * 10
        params = {
            "q":     query,
            "start": start,
            "num":   10,
            "hl":    "en",
        }
        url = "https://www.google.com/search?" + urllib.parse.urlencode(params)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 429 or "unusual traffic" in resp.text.lower():
                print("[!] Google rate-limiting detected. Try again later or reduce pages.")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract names from result titles and snippets
            for tag in soup.select("h3"):
                text = tag.get_text()
                # LinkedIn titles: "Firstname Lastname - Job Title | LinkedIn"
                match = re.match(r"^([A-Z][a-z]+(?: [A-Z][a-z]+)+)", text)
                if match:
                    candidate = match.group(1)
                    if len(candidate.split()) >= 2:
                        names.add(candidate)

            # Also grab names from URL slugs  /in/firstname-lastname
            for link in soup.select("a[href]"):
                href = link["href"]
                slug = re.search(r"linkedin\.com/in/([a-z]+(?:-[a-z]+)+)", href)
                if slug:
                    parts = slug.group(1).split("-")
                    if len(parts) >= 2:
                        # Reconstruct capitalised name from slug
                        name_from_slug = " ".join(p.capitalize() for p in parts[:2])
                        names.add(name_from_slug)

            found_this_page = len(names)
            print(f"    [page {page+1}] Running total: {found_this_page} names")

            if page < max_pages - 1:
                delay = random.uniform(5, 10)
                print(f"    [*] Sleeping {delay:.1f}s to avoid rate limits...")
                time.sleep(delay)

        except requests.RequestException as e:
            print(f"[!] Request failed: {e}")
            break

    return names


# ─── Input methods ────────────────────────────────────────────────────────────

def load_names_from_file(path: str) -> list:
    names = []
    p = Path(path)
    if not p.exists():
        print(f"[!] File not found: {path}")
        sys.exit(1)
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                names.append(line)
    print(f"[+] Loaded {len(names)} names from {path}")
    return names


def manual_input() -> list:
    print("\n[*] Manual name entry mode. Enter one full name per line.")
    print("    Press ENTER on an empty line when done.\n")
    names = []
    while True:
        try:
            name = input("    Name: ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not name:
            break
        names.append(name)
    return names


# ─── Output ───────────────────────────────────────────────────────────────────

def write_output(results: list, outfile: str | None):
    """results = list of (full_name, email) tuples."""
    if not results:
        print("\n[-] No results generated.")
        return

    lines = [f"{name}\t{email}" for name, email in results]

    print("\n" + "=" * 60)
    print(f"  RESULTS ({len(results)} addresses)")
    print("=" * 60)
    for name, email in results:
        print(f"  {email:<40}  ({name})")

    if outfile:
        Path(outfile).write_text("\n".join(lines) + "\n")
        print(f"\n[+] Saved to: {outfile}")

    # Also write just the email addresses for easy piping
    emails_only = [e for _, e in results]
    email_file = (outfile or "output").replace(".txt", "") + "_emails_only.txt"
    Path(email_file).write_text("\n".join(emails_only) + "\n")
    print(f"[+] Emails only saved to: {email_file}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LinkedIn OSINT → Email Harvester | Authorised testing only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Formats available:
  firstname.lastname   →  matt.smith@domain.com      (default)
  f.lastname           →  m.smith@domain.com
  firstnamelastname    →  mattsmith@domain.com
  flastname            →  msmith@domain.com
  firstname            →  matt@domain.com
  lastname.firstname   →  smith.matt@domain.com
  firstname_lastname   →  matt_smith@domain.com
  f_lastname           →  m_smith@domain.com
  lastname             →  smith@domain.com
  firstnamel           →  matts@domain.com
  all                  →  generate ALL formats
        """
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--company", "-c",  help="Company name to dork LinkedIn for")
    source.add_argument("--names",   "-n",  help="Path to text file of full names (one per line)")
    source.add_argument("--manual",  "-m",  action="store_true", help="Enter names interactively")

    parser.add_argument("--domain",  "-d",  required=True, help="Target email domain (e.g. acme.com)")
    parser.add_argument("--format",  "-f",  default="firstname.lastname",
                        help="Email format(s), comma-separated or 'all' (default: firstname.lastname)")
    parser.add_argument("--pages",   "-p",  type=int, default=3,
                        help="Google dork pages to fetch (default: 3)")
    parser.add_argument("--output",  "-o",  help="Output file path (default: <domain>_emails.txt)")
    parser.add_argument("--all-formats", action="store_true",
                        help="Generate all email format variants per person")

    args = parser.parse_args()

    # Resolve formats
    if args.all_formats or args.format.lower() == "all":
        chosen_formats = list(EMAIL_FORMATS.keys())
    elif "," in args.format:
        chosen_formats = [f.strip() for f in args.format.split(",")]
    else:
        chosen_formats = [args.format.strip()]

    invalid = [f for f in chosen_formats if f not in EMAIL_FORMATS]
    if invalid:
        print(f"[!] Unknown format(s): {', '.join(invalid)}")
        print(f"    Valid: {', '.join(EMAIL_FORMATS.keys())}")
        sys.exit(1)

    domain = args.domain.lower().strip()
    outfile = args.output or f"{domain.split('.')[0]}_emails.txt"

    # ── Collect names ──────────────────────────────────────────────────────────
    raw_names: list = []

    if args.company:
        found = google_dork_linkedin(args.company, max_pages=args.pages)
        if not found:
            print("[!] No names retrieved via Google dork.")
            print("    Try --names or --manual to supply names directly.")
            sys.exit(1)
        raw_names = sorted(found)

    elif args.names:
        raw_names = load_names_from_file(args.names)

    elif args.manual:
        raw_names = manual_input()

    if not raw_names:
        print("[!] No names to process.")
        sys.exit(1)

    # ── Generate emails ────────────────────────────────────────────────────────
    results = []
    skipped = []

    print(f"\n[*] Generating emails for {len(raw_names)} name(s) → @{domain}")
    print(f"    Formats: {', '.join(chosen_formats)}\n")

    for name in raw_names:
        first, last = parse_full_name(name)
        if not first or not last:
            skipped.append(name)
            continue
        emails = build_emails(first, last, domain, chosen_formats)
        for email in emails:
            results.append((name, email))

    if skipped:
        print(f"[!] Skipped (single-word or unparseable): {', '.join(skipped)}")

    write_output(results, outfile)
    print(f"\n[*] Done. {len(results)} address(es) from {len(raw_names)} name(s).")


if __name__ == "__main__":
    main()
