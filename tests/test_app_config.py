import yaml

from main import AppConfig

MINIMAL_CONFIG = {
    "firewall": {
        "rule_name": "my_rule",
        "remote_ip": "192.0.2.7",
        "test_port": 443,
    },
    "hotkeys": {"toggle_nosave": "ctrl+f9"},
}


def _write(path, config):
    path.write_text(yaml.dump(config))
    return path


def test_load_creates_a_default_config_when_missing(tmp_path):
    path = tmp_path / "nested" / "config.yaml"

    config = AppConfig.load(path)

    assert path.exists()
    assert config.rule_name == "gtanosavemode_rule"
    assert config.test_port == 80
    assert config.require_game_focus is True
    assert config.auto_stop_on_unfocus is True
    assert config.hotkeys["toggle_nosave"] == "ctrl+f9"


def test_load_reads_firewall_settings_from_disk(tmp_path):
    config = AppConfig.load(_write(tmp_path / "config.yaml", MINIMAL_CONFIG))

    assert (config.rule_name, config.remote_ip, config.test_port) == (
        "my_rule",
        "192.0.2.7",
        443,
    )


def test_load_backfills_hotkeys_added_in_later_versions(tmp_path):
    config = AppConfig.load(_write(tmp_path / "config.yaml", MINIMAL_CONFIG))

    assert config.hotkeys["open_settings"] == "ctrl+f7"
    assert config.hotkeys["armor_snack_combo"] == "ctrl+x"


def test_load_keeps_user_overrides_of_backfilled_hotkeys(tmp_path):
    data = {**MINIMAL_CONFIG, "hotkeys": {"open_settings": "ctrl+f1"}}
    config = AppConfig.load(_write(tmp_path / "config.yaml", data))

    assert config.hotkeys["open_settings"] == "ctrl+f1"


def test_load_defaults_focus_flags_when_absent(tmp_path):
    config = AppConfig.load(_write(tmp_path / "config.yaml", MINIMAL_CONFIG))

    assert config.require_game_focus is True
    assert config.auto_stop_on_unfocus is True


def test_load_honours_explicit_focus_flags(tmp_path):
    data = {**MINIMAL_CONFIG, "require_game_focus": False, "auto_stop_on_unfocus": False}
    config = AppConfig.load(_write(tmp_path / "config.yaml", data))

    assert config.require_game_focus is False
    assert config.auto_stop_on_unfocus is False


def test_save_round_trips_through_load(tmp_path):
    path = tmp_path / "config.yaml"
    config = AppConfig.load(_write(path, MINIMAL_CONFIG))

    config.hotkeys["autoclicker"] = "ctrl+shift+k"
    config.require_game_focus = False
    config.save(path)

    reloaded = AppConfig.load(path)
    assert reloaded.hotkeys["autoclicker"] == "ctrl+shift+k"
    assert reloaded.require_game_focus is False
    assert reloaded.rule_name == "my_rule"


def test_save_writes_the_documented_file_shape(tmp_path):
    path = tmp_path / "config.yaml"
    AppConfig.load(_write(path, MINIMAL_CONFIG)).save(path)

    written = yaml.safe_load(path.read_text())
    assert set(written) == {
        "firewall",
        "require_game_focus",
        "auto_stop_on_unfocus",
        "hotkeys",
    }
    assert set(written["firewall"]) == {"rule_name", "remote_ip", "test_port"}
