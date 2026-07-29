from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_registry_example_is_local_only() -> None:
    registry = json.loads(
        (ROOT / 'registry' / 'provider-registry.example.json').read_text(encoding='utf-8')
    )
    assert registry['storage_root'] == 'device-local'
    assert registry['network'] == 'disabled'
    assert registry['external_memory'] == 'disabled'
    assert all(provider['network'] is False for provider in registry['providers'])
    assert registry['wake_word']['remote_recognition'] is False
    assert registry['wake_word']['recognition'] == 'local_engine_required'


def test_schema_files_are_valid_json() -> None:
    for path in (
        ROOT / 'schemas' / 'local-state' / 'provider-registry.schema.json',
        ROOT / 'schemas' / 'local-state' / 'voice-confirmation.schema.json',
    ):
        document = json.loads(path.read_text(encoding='utf-8'))
        assert document['$schema'].startswith('https://json-schema.org/')
        assert document['type'] == 'object'


def test_contract_files_do_not_generate_keys_or_use_network_tools() -> None:
    paths = [
        ROOT / 'scripts' / 'create-device-family-tree.sh',
        ROOT / 'frontend' / 'public' / 'voice-confirmation.js',
        ROOT / 'policies' / 'local-state-boundary.md',
    ]
    forbidden = ('curl', 'wget', 'git clone', 'generate_key', 'generate_keypair', 'token_urlsafe', 'token_hex', 'os.urandom')
    for path in paths:
        source = path.read_text(encoding='utf-8').lower()
        assert not any(token in source for token in forbidden), path


def test_migration_map_keeps_private_state_out_of_git() -> None:
    text = (ROOT / 'docs' / 'planning' / 'local-state-migration-map.md').read_text(encoding='utf-8')
    assert 'raw memory and conversations' in text
    assert 'private keys' in text
    assert 'No second repository is required for this stage.' in text
