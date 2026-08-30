from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
NGINX = (ROOT / "infra/nginx/nginx.conf").read_text(encoding="utf-8")
IOS_WORKFLOW = (ROOT / ".github/workflows/ios-sovereign-build.yml").read_text(encoding="utf-8")


def test_production_ingress_publishes_only_443() -> None:
    assert '"443:443"' in COMPOSE
    assert '"80:80"' not in COMPOSE
    assert '"9899:9899"' not in COMPOSE


def test_nginx_has_no_plaintext_listener_or_redirect() -> None:
    assert "listen 443 ssl" in NGINX
    assert "listen 80" not in NGINX
    assert "return 301 https://" not in NGINX
    assert "ws:" not in NGINX
    assert "wss:" in NGINX
    assert "ssl_protocols TLSv1.3;" in NGINX


def test_ios_workflow_performs_real_package_build_and_tests() -> None:
    assert "swift package dump-package" in IOS_WORKFLOW
    assert "swift build -v" in IOS_WORKFLOW
    assert "swift test -v" in IOS_WORKFLOW
    assert "swift_package_build': True" in IOS_WORKFLOW
    assert "swift_package_tests': True" in IOS_WORKFLOW
