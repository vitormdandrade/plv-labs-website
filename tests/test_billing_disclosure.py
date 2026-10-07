from pathlib import Path
import unittest


class BillingDisclosureTest(unittest.TestCase):
    def test_native_policy_discloses_account_linked_purchase_processing(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for required in ["RevenueCat", "Google Play", "App Store", "identificador interno da conta", "histórico", "restaurar compras", "comprovantes técnicos"]:
            self.assertIn(required, policy)
        self.assertIn("não armazenamos o número completo do cartão", policy.lower())


if __name__ == "__main__":
    unittest.main()
