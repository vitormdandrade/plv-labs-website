"""Anti-drift guard driven by legal_standard.json (PLV Labs).

The store review teams and the LGPD pages read these files, so the company name,
the CNPJ, the contact address and the legal URLs have to be the same everywhere.
This test reads the static files in the repository (not the live site) and fails
when any of them drifts from the manifest, when a declared page is missing, or
when a legal page carries a placeholder.

Deliberately stdlib-only: it must run on the Mac Mini with the system Python.

Run it with:
    python3 -m unittest discover -s tests -v
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "legal_standard.json"

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PATH_SUFFIXES = ("privacidade", "termos", "exclusao-de-conta")


def load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def strip_tags(html):
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def placeholders(text):
    """Literal placeholders only.

    `TODO` is matched case-sensitively and on its own: in Portuguese "todo o
    tráfego" is an ordinary word, so a case-insensitive match would flag every
    correct privacy page and train the reader to ignore the guard.
    """
    patterns = (
        (r"\[preencher", re.S),
        (r"\[inserir", re.S),
        (r"\bTODO\b", 0),
        (r"\bFIXME\b", 0),
        (r"\{\{.*?\}\}", re.S),
        (r"(?i)\blorem ipsum\b", 0),
        (r"(?i)placeholder", 0),
        (r"<insert", 0),
    )
    found = []
    for pattern, flags in patterns:
        found.extend(match.group(0) for match in re.finditer(pattern, text, flags))
    return found


def url_to_file(url, root=ROOT):
    """Map a published URL to the static file that serves it (cleanUrls)."""
    root_domain = MANIFEST["root"]
    assert url.startswith(root_domain), url
    tail = url[len(root_domain):].strip("/")
    if not tail:
        return root / "index.html"
    candidate = root / tail
    if candidate.is_dir():
        return candidate / "index.html"
    return root / f"{tail}.html"


def legal_page_files():
    """Every file the manifest declares as a legal page."""
    files = []
    for key in ("privacy_url", "terms_url", "deletion_url"):
        files.append(url_to_file(MANIFEST["company_pages"][key]))
    for product in MANIFEST["products"]:
        for key in ("privacy_url", "terms_url", "deletion_url"):
            files.append(url_to_file(product[key]))
    return files


MANIFEST = load_manifest()


class LegalStandardTest(unittest.TestCase):
    def test_manifest_pins_the_plv_labs_standard(self):
        self.assertEqual(MANIFEST["company"], "PLV Labs")
        self.assertEqual(MANIFEST["legal_entity"], "PLV LABS LTDA")
        self.assertEqual(MANIFEST["cnpj"], "66.394.393/0001-73")
        self.assertEqual(MANIFEST["root"], "https://plvlabs.com.br")
        self.assertEqual(MANIFEST["contact_email"], "admin@plvlabs.com.br")
        self.assertIn("45.394.272/0001-51", MANIFEST["forbidden_company_tokens"])
        self.assertEqual(
            MANIFEST["company_pages"],
            {
                "privacy_url": "https://plvlabs.com.br/privacidade",
                "terms_url": "https://plvlabs.com.br/termos",
                "deletion_url": "https://plvlabs.com.br/exclusao-de-conta",
            },
        )
        self.assertEqual(
            [product["slug"] for product in MANIFEST["products"]],
            ["kiso", "orcamentozap", "payflo"],
        )

    def test_every_declared_url_is_a_product_page_under_the_root(self):
        root = MANIFEST["root"]
        for product in MANIFEST["products"]:
            for key in ("privacy_url", "terms_url", "deletion_url"):
                url = product[key]
                self.assertTrue(url.startswith(f"{root}/{product['slug']}/"), url)
                self.assertTrue(url.endswith(("/privacidade", "/termos", "/exclusao-de-conta")), url)

    def test_declared_pages_exist_and_carry_the_standard_in_their_body(self):
        failures = []
        for path in legal_page_files():
            relative = path.relative_to(ROOT)
            if not path.exists():
                failures.append(f"{relative}: file missing")
                continue
            if path.stat().st_size < 500:
                failures.append(f"{relative}: file looks empty ({path.stat().st_size} bytes)")
                continue
            html = path.read_text(encoding="utf-8")
            text = strip_tags(html)
            if MANIFEST["legal_entity"] not in text:
                failures.append(f"{relative}: legal entity missing from the body")
            if MANIFEST["cnpj"] not in text:
                failures.append(f"{relative}: CNPJ missing from the body")
            if MANIFEST["contact_email"] not in text:
                failures.append(f"{relative}: contact {MANIFEST['contact_email']} missing from the body")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_legal_pages_carry_only_the_standard_contact_address(self):
        failures = []
        for path in legal_page_files():
            if not path.exists():
                continue
            relative = path.relative_to(ROOT)
            emails = set(EMAIL_PATTERN.findall(path.read_text(encoding="utf-8")))
            unexpected = sorted(address for address in emails if address != MANIFEST["contact_email"])
            if unexpected:
                failures.append(f"{relative}: unexpected contact(s) {unexpected}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_canonical_link_stays_on_the_company_domain(self):
        failures = []
        for path in legal_page_files():
            if not path.exists():
                continue
            relative = path.relative_to(ROOT)
            match = re.search(r'<link rel="canonical" href="([^"]+)"', path.read_text(encoding="utf-8"))
            if match is None:
                failures.append(f"{relative}: no canonical link")
                continue
            if not match.group(1).startswith(MANIFEST["root"]):
                failures.append(f"{relative}: canonical {match.group(1)} is outside {MANIFEST['root']}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_product_pages_link_the_three_documents_the_manifest_declares(self):
        failures = []
        for product in MANIFEST["products"]:
            urls = [product[key] for key in ("privacy_url", "terms_url", "deletion_url")]
            for key in ("privacy_url", "terms_url", "deletion_url"):
                path = url_to_file(product[key])
                if not path.exists():
                    continue
                html = path.read_text(encoding="utf-8")
                relative = path.relative_to(ROOT)
                for url in urls:
                    if url not in html:
                        failures.append(f"{relative}: does not link {url}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_no_legal_page_names_the_other_company(self):
        failures = []
        for path in legal_page_files():
            if not path.exists():
                continue
            text = strip_tags(path.read_text(encoding="utf-8"))
            for token in MANIFEST["forbidden_company_tokens"]:
                if token in text:
                    failures.append(f"{path.relative_to(ROOT)}: names {token}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_no_legal_page_carries_a_placeholder(self):
        failures = []
        for path in legal_page_files():
            if not path.exists():
                continue
            found = placeholders(strip_tags(path.read_text(encoding="utf-8")))
            if found:
                failures.append(f"{path.relative_to(ROOT)}: {found}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_manifest_covers_every_product_folder_in_the_repository(self):
        declared = {url_to_file(product["privacy_url"]).parent for product in MANIFEST["products"]}
        found = {
            path
            for path in ROOT.iterdir()
            if path.is_dir()
            and not path.name.startswith(".")
            and (path / "privacidade.html").exists()
        }
        self.assertEqual(
            sorted(found - declared),
            [],
            "product folders with legal pages but no manifest entry",
        )
        self.assertEqual(sorted(declared - found), [], "manifest lists a product folder that is gone")

    def test_each_product_folder_publishes_the_three_pages(self):
        for product in MANIFEST["products"]:
            for suffix in PATH_SUFFIXES:
                path = ROOT / product["slug"] / f"{suffix}.html"
                self.assertTrue(path.exists(), f"{product['slug']}/{suffix}.html missing")

    def test_placeholder_rule_catches_a_real_placeholder_and_ignores_the_word_todo(self):
        self.assertTrue(placeholders("O controlador é [preencher CNPJ]"))
        self.assertTrue(placeholders("Empresa: TODO"))
        self.assertTrue(placeholders("lorem ipsum dolor"))
        self.assertEqual(placeholders("Isso vale para todo o tráfego de medição"), [])
        self.assertEqual(placeholders("PLV LABS LTDA · CNPJ 66.394.393/0001-73"), [])


if __name__ == "__main__":
    unittest.main()
