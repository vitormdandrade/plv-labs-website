"""Anti-drift guard for the published legal pages.

The store review teams read these pages, so a missing page, a placeholder, or a
page attributed to the wrong company is a submission blocker. This test reads
the static files in the repository (not the live site) and fails when any of
those conditions appears, so the defect is caught before a deploy.

Deliberately stdlib-only: it must run on the Mac Mini with the system Python.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOMAINS = {
    "https://plvlabs.com.br": {
        "legal": "PLV LABS LTDA",
        "cnpj": "66.394.393/0001-73",
        "email": "admin@plvlabs.com.br",
        "other_company_tokens": ["Consistency Labs", "45.394.272/0001-51"],
    },
    "https://consistencylabs.dev": {
        "legal": "Vitor Machado de Andrade Consultoria em Marketing LTDA",
        "cnpj": "45.394.272/0001-51",
        "email": "admin@consistencylabs.dev",
        "other_company_tokens": ["PLV LABS", "66.394.393/0001-73"],
    },
}

REQUIRED_PAGES = ("privacidade.html", "termos.html", "exclusao-de-conta.html")

URL_PATTERN = re.compile(r"https://(?:plvlabs\.com\.br|consistencylabs\.dev)/[A-Za-z0-9\-/]*")


def strip_tags(html):
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def placeholders(text):
    """Literal placeholders only.

    `TODO` is matched case-sensitively and on its own: in Portuguese "todo o
    tráfego" is a normal word, so a case-insensitive match flags every correct
    privacy page and trains you to ignore the guard.
    """
    patterns = [
        r"\[preencher",
        r"\[inserir",
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\{\{.*?\}\}",
        r"(?i)\blorem ipsum\b",
        r"\bXXX+\b",
        r"(?i)placeholder",
        r"<insert",
    ]
    found = []
    for pattern in patterns:
        flags = 0 if pattern.startswith(r"\bTODO") else re.S
        found.extend(m.group(0) for m in re.finditer(pattern, text, flags))
    return found


def legal_urls(html):
    return URL_PATTERN.findall(html)


def product_dirs(root=ROOT):
    return sorted(
        p for p in root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and (p / "privacidade.html").exists()
    )


def url_to_file(url, root=ROOT):
    path = url.split("//", 1)[1]
    _, _, tail = path.partition("/")
    tail = tail.strip("/")
    if not tail:
        return root / "index.html"
    candidate = root / tail
    if candidate.is_dir():
        return candidate / "index.html"
    return root / f"{tail}.html"


def company_for(html):
    for domain, cfg in DOMAINS.items():
        if domain + "/" in html:
            return domain, cfg
    return None, None


class LegalPagesTest(unittest.TestCase):
    def test_every_product_publishes_all_three_legal_pages(self):
        products = product_dirs()
        # A repository with no product folder would make this guard vacuous.
        self.assertTrue(products, "no product folder with a privacidade.html found")
        missing = []
        for product in products:
            for page in REQUIRED_PAGES:
                target = product / page
                if not target.exists():
                    missing.append(f"{product.name}/{page}")
                elif target.stat().st_size < 500:
                    missing.append(f"{product.name}/{page} (truncated)")
        self.assertEqual(missing, [], "missing or empty legal pages: " + ", ".join(missing))

    def test_root_publishes_privacy_terms_and_deletion(self):
        for page in ("privacidade.html", "termos.html", "exclusao-de-conta.html"):
            target = ROOT / page
            self.assertTrue(target.exists(), f"root {page} missing")
            self.assertGreater(target.stat().st_size, 500, f"root {page} looks empty")

    def test_pages_name_the_correct_company_and_cnpj(self):
        failures = []
        for page in ROOT.rglob("*.html"):
            if ".git" in page.parts:
                continue
            html = page.read_text(encoding="utf-8")
            text = strip_tags(html)
            domain, cfg = company_for(html)
            if cfg is None:
                continue
            relative = page.relative_to(ROOT)
            if cfg["cnpj"] not in text:
                failures.append(f"{relative}: CNPJ {cfg['cnpj']} missing")
            if cfg["legal"].split()[0] not in text:
                failures.append(f"{relative}: legal entity {cfg['legal']} missing")
            for token in cfg["other_company_tokens"]:
                if token in text:
                    failures.append(f"{relative}: names the other company ({token})")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_no_page_carries_a_placeholder(self):
        failures = []
        for page in ROOT.rglob("*.html"):
            if ".git" in page.parts:
                continue
            found = placeholders(strip_tags(page.read_text(encoding="utf-8")))
            if found:
                failures.append(f"{page.relative_to(ROOT)}: {found}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_every_legal_link_points_at_a_published_page(self):
        failures = []
        for page in ROOT.rglob("*.html"):
            if ".git" in page.parts:
                continue
            html = page.read_text(encoding="utf-8")
            for url in legal_urls(html):
                target = url_to_file(url)
                if not target.exists():
                    failures.append(f"{page.relative_to(ROOT)} -> {url} (no {target.relative_to(ROOT)})")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_product_pages_link_their_own_three_documents(self):
        failures = []
        for product in product_dirs():
            domain = None
            for page in REQUIRED_PAGES:
                html = (product / page).read_text(encoding="utf-8")
                domain, _ = company_for(html)
                if domain is None:
                    failures.append(f"{product.name}/{page}: no company domain")
                    continue
            if domain is None:
                continue
            for page in REQUIRED_PAGES:
                html = (product / page).read_text(encoding="utf-8")
                for suffix in ("privacidade", "termos", "exclusao-de-conta"):
                    expected = f"{domain}/{product.name}/{suffix}"
                    if expected not in html:
                        failures.append(f"{product.name}/{page}: missing link {expected}")
                canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
                if canonical and canonical.group(1) not in (domain, domain + "/"):
                    expected_canonical = f"{domain}/{product.name}/{page.replace('.html', '')}"
                    if canonical.group(1) != expected_canonical:
                        failures.append(
                            f"{product.name}/{page}: canonical {canonical.group(1)} != {expected_canonical}"
                        )
        self.assertEqual(failures, [], "\n".join(failures))

    def test_sitemap_only_lists_pages_that_exist(self):
        sitemap = ROOT / "sitemap.xml"
        if not sitemap.exists():
            self.skipTest("repository has no sitemap.xml")
        locs = re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))
        self.assertTrue(locs)
        missing = [loc for loc in locs if not url_to_file(loc.strip()).exists()]
        self.assertEqual(missing, [], "sitemap lists pages that do not exist: " + ", ".join(missing))
        published = {
            f"{domain}/{p.parent.name}/{p.stem}" if p.parent != ROOT else f"{domain}/{p.stem}"
            for p in ROOT.rglob("*.html")
            if ".git" not in p.parts and p.stem != "index"
            for domain in DOMAINS
            if domain + "/" in p.read_text(encoding="utf-8")
        }
        unlisted = sorted(u for u in published if u not in {loc.strip() for loc in locs})
        self.assertEqual(unlisted, [], "legal pages missing from sitemap: " + ", ".join(unlisted))

    def test_placeholder_rule_catches_a_real_placeholder_and_ignores_the_word_todo(self):
        self.assertTrue(placeholders("O controlador é [preencher CNPJ]"))
        self.assertTrue(placeholders("Empresa: TODO"))
        self.assertTrue(placeholders("lorem ipsum dolor"))
        self.assertEqual(placeholders("Isso vale para todo o tráfego de medição"), [])
        self.assertEqual(placeholders("PLV LABS LTDA · CNPJ 66.394.393/0001-73"), [])


if __name__ == "__main__":
    unittest.main()
