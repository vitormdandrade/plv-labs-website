from html.parser import HTMLParser
from pathlib import Path
import unittest


class TextCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class AndroidMeasurementDisclosureTest(unittest.TestCase):
    def test_android_measurement_discloses_sdk_processing_without_false_controls(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        parser = TextCollector()
        parser.feed(policy)
        text = " ".join(" ".join(parser.parts).split())
        for required in [
            "Medição no aplicativo Android",
            "Google Analytics para Firebase",
            "app_first_open", "signup_completed", "first_quote_created",
            "first_quote_shared", "activated_professional", "paywall_viewed",
            "acquisition_source", "campaign",
            "não incluem conteúdo de orçamentos",
            "identificador da instância do aplicativo",
            "não são anônimos na origem",
            "localização aproximada derivada do endereço IP mascarado",
            "compras e assinaturas", "produto, preço e moeda",
            "identificador de publicidade do Android",
            "Google Ads", "desempenho de campanhas",
            "eventos: 2 meses", "usuários: 14 meses",
            "renovação do prazo dos identificadores de usuário a cada nova atividade",
            "não se aplicam aos relatórios agregados padrão",
            "medição é opcional", "consentimento",
            "continuar sem permitir a medição",
            "Ajustes", "não limita o acesso",
            "recusa imediatamente novos eventos personalizados de medição neste uso do app",
            "exclusão da conta não apaga automaticamente os dados de medição",
            "admin@plvlabs.com.br",
            "7 de outubro de 2026",
        ]:
            with self.subTest(disclosure=required):
                self.assertIn(required, text)
        self.assertNotIn("Cookies de medição só são usados de forma agregada.", text)
        self.assertIn('lang="pt-BR"', policy)
        self.assertIn("PLV LABS LTDA", text)
        self.assertIn("66.394.393/0001-73", text)
        self.assertEqual(policy.count('<h1>'), 1)
        self.assertEqual(policy.count('<h2>'), 11)

    def test_optional_measurement_controls_match_the_android_choice(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for disclosure in [
            "Permitir medição", "Continuar sem rastreamento",
            "Medição opcional no Android", "Ajustes",
            "Antes do consentimento", "ações anteriores ao consentimento",
            "não podem ser canceladas retroativamente",
            "identificadores de medição locais",
        ]:
            with self.subTest(disclosure=disclosure):
                self.assertIn(disclosure, policy)
        self.assertNotIn("Configurações do aplicativo", policy)
        self.assertNotIn("sem nenhum envio imediato", policy)

    def test_google_product_sharing_disabled_does_not_hide_remaining_selections(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for disclosure in [
            "compartilhar dados de medição para melhorar os produtos e serviços do Google está desativada",
            "contribuições de modelagem e comparações agregadas",
            "suporte técnico", "recomendações para o negócio",
            "outros produtos vinculados",
        ]:
            with self.subTest(disclosure=disclosure):
                self.assertIn(disclosure, policy)
        self.assertNotIn("Compartilhamos apenas com operadores necessários", policy)
        self.assertNotIn("as configurações atuais do Google Analytics também permitem uso para melhorar os produtos", policy)
        self.assertNotIn("Não compartilhamos dados com o Google", policy)

    def test_initial_denial_and_normally_remembered_affirmative_choice(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for required in [
            "A medição começa recusada enquanto não houver uma permissão salva válida",
            "Sua escolha é guardada no aparelho e lembrada nas próximas aberturas, em condições normais",
            "não pedimos uma nova permissão a cada abertura",
            "essa permissão pode ser usada nas próximas aberturas até você mudar sua escolha em Ajustes",
        ]:
            with self.subTest(disclosure=required):
                self.assertTrue(required in policy, required)


    def test_withdrawal_denies_current_custom_events_without_promising_sdk_completion(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for required in [
            "recusa imediatamente novos eventos personalizados de medição neste uso do app",
            "solicita ao Firebase a desativação da coleta, a recusa do armazenamento de análise e a redefinição dos dados locais do SDK",
            "confirmação desses pedidos indica apenas sua submissão",
            "não comprova a conclusão do trabalho assíncrono do SDK",
            "nem garante que todo tráfego de medição já tenha cessado",
        ]:
            with self.subTest(disclosure=required):
                self.assertTrue(required in policy, required)
        self.assertNotIn("interrompe novas coletas", policy)


    def test_withdrawal_attempts_durable_refusal_and_local_removal_not_server_deletion(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for required in [
            "tenta salvar a recusa para as próximas aberturas, invalidar a permissão anterior e remover os identificadores de medição locais e os registros de ações pendentes",
            "Essas tentativas de gravação, exclusão e redefinição local podem falhar",
            "Remover dados locais ou redefinir o SDK não equivale a excluir dados dos servidores do Google",
            "a retirada não apaga automaticamente os dados já enviados ao Analytics",
            "A exclusão da conta não apaga automaticamente os dados de medição já enviados ao Analytics",
        ]:
            with self.subTest(disclosure=required):
                self.assertTrue(required in policy, required)
        self.assertFalse("e remove os identificadores de medição locais" in policy)


    def test_storage_failure_can_restore_old_permission_on_restart(self):
        # Exact warning fixtures from measurement_choice_widgets.dart; source
        # hashes and line references are recorded in the correction receipt.
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for required in [
            "impedir todas as gravações e exclusões necessárias e uma permissão anterior continuar legível",
            "essa permissão pode voltar ao reiniciar o app",
            "Não foi possível salvar sua escolha. A medição está recusada neste uso do app. Tente novamente.",
            "Não foi possível confirmar a recusa para a próxima abertura do app. Uma permissão anterior pode voltar ao reiniciar.",
        ]:
            with self.subTest(disclosure=required):
                self.assertTrue(required in policy, required)


    def test_sdk_submission_failure_warns_automatic_measurement_may_continue(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        for required in [
            "a medição automática pode continuar ativa mesmo com a recusa indicada no app",
            "Não foi possível confirmar o pedido de parada da medição automática. Ela pode continuar ativa. Tente novamente; isso não apaga dados já enviados.",
        ]:
            with self.subTest(disclosure=required):
                self.assertTrue(required in policy, required)


    def test_failure_status_persists_with_deny_only_retry_without_blocking_features(self):
        policy = (Path(__file__).resolve().parents[1] / "orcamentozap/privacidade.html").read_text()
        parser = TextCollector()
        parser.feed(policy)
        text = " ".join(" ".join(parser.parts).split())
        for required in [
            "mantém um aviso visível após a escolha e em Ajustes, mesmo depois de fechar a explicação",
            "Tentar novamente sem rastreamento",
            "tentar registrar a recusa e pedir novamente a parada",
            "essa tentativa não permite novamente a medição",
            "não garante, por si só, a resolução da falha",
            "Você pode continuar usando as funcionalidades do app",
        ]:
            with self.subTest(disclosure=required):
                self.assertTrue(required in text, required)


if __name__ == "__main__":
    unittest.main()
