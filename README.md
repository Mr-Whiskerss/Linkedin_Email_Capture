# linkedin-email-harvest

A Python OSINT tool for penetration testers that collects employee names from LinkedIn via Google dorking and generates candidate email addresses in configurable formats.

Intended for use during the reconnaissance phase of authorised engagements.

---

## Disclaimer

This tool is intended for use by security professionals on systems and organisations they have explicit written authorisation to test. Unauthorised use against third-party systems may violate the Computer Misuse Act 1990, CFAA, GDPR, and LinkedIn's Terms of Service. The author accepts no liability for misuse.

---

## Features

- Three name input modes: Google dork, text file, or interactive manual entry
- Ten email format templates covering the most common corporate conventions
- Accent and special character normalisation (e.g. O'Brien, Müller)
- Outputs a tab-separated results file and a clean email-only list for piping into downstream tools
- Configurable Google dork page depth with randomised rate-limit delays

---

## Requirements

- Python 3.8+
- requests
- beautifulsoup4

```
pip install requests beautifulsoup4
```

---

## Usage

```
python3 linkedin_email_harvest.py [--company | --names | --manual] --domain DOMAIN [options]
```

### Arguments

| Argument | Description |
|---|---|
| `--company`, `-c` | Company name to search LinkedIn for via Google dork |
| `--names`, `-n` | Path to a text file of full names, one per line |
| `--manual`, `-m` | Enter names interactively at the prompt |
| `--domain`, `-d` | Target email domain, e.g. `acme.com` (required) |
| `--format`, `-f` | Email format(s), comma-separated (default: `firstname.lastname`) |
| `--all-formats` | Generate all 10 format variants per person |
| `--pages`, `-p` | Number of Google search pages to dork (default: 3) |
| `--output`, `-o` | Output file path (default: `<domain>_emails.txt`) |

---

## Examples

**Google dork LinkedIn for a company:**
```bash
python3 linkedin_email_harvest.py --company "Acme Corp" --domain acme.com
```

**Load names from a file, single format:**
```bash
python3 linkedin_email_harvest.py --names names.txt --domain acme.com --format f.lastname
```

**Load names from a file, multiple formats:**
```bash
python3 linkedin_email_harvest.py --names names.txt --domain acme.com \
  --format "firstname.lastname,f.lastname,flastname"
```

**Generate all format variants:**
```bash
python3 linkedin_email_harvest.py --names names.txt --domain acme.com --all-formats
```

**Interactive entry:**
```bash
python3 linkedin_email_harvest.py --manual --domain acme.com
```

---

## Email Formats

| Key | Example output |
|---|---|
| `firstname.lastname` | matt.smith@acme.com |
| `f.lastname` | m.smith@acme.com |
| `firstnamelastname` | mattsmith@acme.com |
| `flastname` | msmith@acme.com |
| `firstname` | matt@acme.com |
| `lastname.firstname` | smith.matt@acme.com |
| `firstname_lastname` | matt_smith@acme.com |
| `f_lastname` | m_smith@acme.com |
| `lastname` | smith@acme.com |
| `firstnamel` | matts@acme.com |

---

## Output

Two files are written on each run:

- `<domain>_emails.txt` — tab-separated, name and email address per line, suitable for review
- `<domain>_emails_only.txt` — email addresses only, suitable for piping into validation tools

Example output:

```
matt.smith@acme.com                 (Matt Smith)
m.smith@acme.com                    (Matt Smith)
jane.doe@acme.com                   (Jane Doe)
```

---

## Integration

The email-only output file can be fed directly into common validation and spraying tools:

```bash
# SMTP user enumeration
smtp-user-enum -M VRFY -U acme_emails_only.txt -t mail.acme.com

# Office 365 validation
o365spray --validate --userfile acme_emails_only.txt --domain acme.com

# curl or custom tooling
while read email; do
  echo "[*] Testing $email"
done < acme_emails_only.txt
```

---

## Notes on Google Dork Mode

- LinkedIn blocks direct scraping, so the dork mode queries Google rather than LinkedIn directly
- Google may return a CAPTCHA after several pages; if this happens, reduce `--pages` or switch to `--names` file input
- A randomised delay of 5-10 seconds is applied between pages to reduce detection likelihood
- For larger targets (50+ employees) the file-based approach is more reliable

---

## Input File Format

Plain text, one full name per line. Lines beginning with `#` are treated as comments.

```
# Acme Corp employees
Matt Smith
Jane Doe
Alice Johnson
Bob O'Brien
```


Use only against organisations you have written authorisation to test. Ensure your engagement scope explicitly covers OSINT and credential enumeration activities. In the UK, refer to the Computer Misuse Act 1990 before use.
