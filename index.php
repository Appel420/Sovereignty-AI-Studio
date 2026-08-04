<?php

declare(strict_types=1);

require __DIR__ . '/scripts/php_local_bootstrap.php';

$config = json_decode((string) file_get_contents(__DIR__ . '/phpwin.json'), true, 512, JSON_THROW_ON_ERROR);
$gate = require __DIR__ . '/DevAssist420/Sovereignty-AI/GateOne/bootstrap.php';
$bus = require __DIR__ . '/SGHv119/bus.php';
$audit = require __DIR__ . '/AUDIT/bootstrap.php';

function local_bridge_status(array $config): array
{
    $url = (string) ($config['devassist']['status_url'] ?? 'http://127.0.0.1:9899/api/devassist/status');
    $parts = parse_url($url);
    $host = $parts['host'] ?? '';
    if (!in_array($host, ['127.0.0.1', 'localhost', '::1'], true)) {
        return ['state' => 'UNAVAILABLE', 'reason' => 'non-loopback endpoint rejected'];
    }

    $context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'timeout' => 1.5,
            'ignore_errors' => true,
        ],
    ]);
    $raw = @file_get_contents($url, false, $context);
    if ($raw === false) {
        return ['state' => 'UNAVAILABLE', 'reason' => 'loopback bridge not reachable', 'url' => $url];
    }
    $status = json_decode($raw, true);
    if (!is_array($status)) {
        return ['state' => 'UNAVAILABLE', 'reason' => 'invalid bridge status response', 'url' => $url];
    }
    return [
        'state' => (string) ($status['state'] ?? 'UNAVAILABLE'),
        'service' => $status['service'] ?? 'DevAssist420',
        'mode' => $status['mode'] ?? 'local',
        'network' => $status['network'] ?? 'loopback-only',
        'url' => $url,
    ];
}

$mode = $_SERVER['HTTP_X_SOVEREIGN_MODE'] ?? $config['mode']['default'];
$modeResult = $gate['mode']->resolve($mode, $_SERVER['HTTP_X_SOVEREIGN_OWNER_APPROVAL'] ?? null);

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if ($path === '/health') {
    header('Content-Type: application/json');
    echo json_encode([
        'status' => 'ok',
        'mode' => $modeResult['mode'],
        'network' => $modeResult['network'],
        'devassist' => local_bridge_status($config),
    ], JSON_THROW_ON_ERROR);
    exit;
}

if ($path === '/api/status') {
    header('Content-Type: application/json');
    echo json_encode([
        'service' => 'Sovereignty AI Studio PHPWin node',
        'mode' => $modeResult,
        'oauth' => $config['oauth'],
        'network' => $config['network'],
        'devassist' => local_bridge_status($config),
        'audit' => $audit['status'](),
    ], JSON_THROW_ON_ERROR);
    exit;
}

if ($path === '/api/event' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $payload = json_decode((string) file_get_contents('php://input'), true) ?: [];
    $event = $bus['emit']('local.request', $payload, $modeResult);
    $audit['record']('LOCAL_REQUEST', $event);
    header('Content-Type: application/json');
    echo json_encode(['accepted' => true, 'event' => $event], JSON_THROW_ON_ERROR);
    exit;
}

header('Content-Type: text/html; charset=utf-8');
echo '<h1>Sovereignty AI Studio</h1><p>Mode: ' . htmlspecialchars($modeResult['mode'], ENT_QUOTES, 'UTF-8') . '</p>';
