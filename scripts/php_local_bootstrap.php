<?php
/**
 * Sovereignty AI Studio PHPWin/iOS local bootstrap.
 *
 * This file is intentionally local-only and does not make network calls.
 * Include it before application routes when PHPWin does not load a php.ini.
 */

declare(strict_types=1);

$localMode = getenv('SG_NETWORK_MODE') ?: 'offline';

ini_set('expose_php', '0');
ini_set('display_errors', '0');
ini_set('display_startup_errors', '0');
ini_set('log_errors', '1');
ini_set('allow_url_include', '0');

if ($localMode === 'offline') {
    ini_set('allow_url_fopen', '0');
}

ini_set('session.use_strict_mode', '1');
ini_set('session.use_only_cookies', '1');
ini_set('session.cookie_httponly', '1');
ini_set('session.cookie_secure', '1');
ini_set('session.cookie_samesite', 'Lax');

function sovereignty_local_destination(string $url): bool
{
    $host = parse_url($url, PHP_URL_HOST);
    return in_array($host, ['127.0.0.1', 'localhost', '::1'], true);
}

function sovereignty_require_loopback(string $url): void
{
    if (!sovereignty_local_destination($url)) {
        throw new RuntimeException('External destination blocked in LOCAL mode');
    }
}
