<?php

declare(strict_types=1);

ini_set('expose_php', '0');
ini_set('display_errors', '0');
ini_set('display_startup_errors', '0');
ini_set('log_errors', '1');
ini_set('allow_url_include', '0');
ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.cookie_httponly', '1');
ini_set('session.cookie_secure', '1');
ini_set('session.cookie_samesite', 'Lax');

function sovereignty_is_loopback(): bool
{
    $remote = $_SERVER['REMOTE_ADDR'] ?? '';
    $host = parse_url('https://' . ($_SERVER['HTTP_HOST'] ?? ''), PHP_URL_HOST);
    return in_array($remote, ['127.0.0.1', '::1', 'localhost'], true)
        && in_array($host, ['127.0.0.1', '::1', 'localhost'], true);
}

function sovereignty_require_loopback(): void
{
    if (!sovereignty_is_loopback()) {
        http_response_code(403);
        exit('Loopback access only');
    }
}
