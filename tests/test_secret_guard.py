from repo_cleanroom.safety.secret_guard import is_protected_path, protected_reason


def test_secret_guard_blocks_env_and_keys():
    assert is_protected_path(".env")
    assert is_protected_path("id_ed25519")
    assert is_protected_path("server.pem")
    assert is_protected_path("wallet-backup.json")


def test_secret_guard_allows_normal_artifact_name():
    assert not is_protected_path("node_modules")
    assert protected_reason("node_modules") is None
