"""O bicho mudou de nome (SatoshiPet), mas o pet antigo tem que vir junto."""
import json

from satoshipet import license, migracao


def test_migra_config_pasta_e_token(tmp_path):
    (tmp_path / ".tamagoshi_cripto.json").write_text(json.dumps({"nome_pet": "Satoshinho", "xp": 999}))
    (tmp_path / ".tamagoshi_cripto" / "skins" / "minha").mkdir(parents=True)
    (tmp_path / ".tamagoshi_cripto" / "skins" / "minha" / "skin.json").write_text("{}")
    (tmp_path / ".tamagoshi_api_token").write_text("tok")
    feitos = migracao.migrar_arquivos(home=tmp_path)
    assert set(feitos) == {".satoshipet.json", ".satoshipet", ".satoshipet_api_token"}
    assert json.loads((tmp_path / ".satoshipet.json").read_text())["nome_pet"] == "Satoshinho"
    assert (tmp_path / ".satoshipet" / "skins" / "minha" / "skin.json").exists()
    assert (tmp_path / ".tamagoshi_cripto.json").exists()  # copia, não move: o antigo fica de backup
    # 2ª vez não sobrescreve o novo
    (tmp_path / ".satoshipet.json").write_text('{"nome_pet": "Novo"}')
    assert migracao.migrar_arquivos(home=tmp_path) == []
    assert "Novo" in (tmp_path / ".satoshipet.json").read_text()


def test_sem_app_antigo_nao_faz_nada(tmp_path):
    assert migracao.migrar_arquivos(home=tmp_path) == []


def test_chaveiro_antigo(tmp_path):
    class KR:
        d = {("tamagoshi-cripto", "ai_key"): "sk-velha"}

        def get_password(self, s, c):
            return self.d.get((s, c))

        def set_password(self, s, c, v):
            self.d[(s, c)] = v
    kr = KR()
    assert migracao.migrar_chaveiro(kr, "satoshipet", "ai_key") == "sk-velha"
    assert kr.d[("satoshipet", "ai_key")] == "sk-velha"


def test_autostart_antigo_vira_novo():
    log = []
    assert migracao.migrar_autostart(lambda: True, lambda: log.append("apaga"), lambda: log.append("liga"))
    assert log == ["apaga", "liga"]
    assert not migracao.migrar_autostart(lambda: False, lambda: log.append("x"), lambda: log.append("y"))


def test_env_antigo_ainda_vale(monkeypatch):
    monkeypatch.delenv("SATOSHIPET_API_PORT", raising=False)
    monkeypatch.setenv("TAMAGOSHI_API_PORT", "9999")
    assert migracao.env("API_PORT") == "9999"
    monkeypatch.setenv("SATOSHIPET_API_PORT", "1111")
    assert migracao.env("API_PORT") == "1111"


def test_chave_pro_antiga_continua_valida():
    # chave = HMAC do e-mail, sem prefixo de produto: trocar o nome não invalida ninguém
    c = license.gerar_chave("fa@exemplo.com")
    assert license.validar("fa@exemplo.com", c) and license.validar("fa@exemplo.com", c.lower())
