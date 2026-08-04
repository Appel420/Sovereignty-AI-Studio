<?php

declare(strict_types=1);

require __DIR__ . '/scripts/php_local_bootstrap.php';

$config = json_decode((string) file_get_contents(__DIR__ . '/phpwin.json'), true, 512, JSON_THROW_ON_ERROR);
$gate = require __DIR__ . '/DevAssist420/Sovereignty-AI/GateOne/bootstrap.php';
$bus = require __DIR__ . '/SGHv119/bus.php';
$audit = require __DIR__ . '/AUDIT/bootstrap.php';

$mode = $_SERVER['HTTP_X_SOVEREIGN_MODE'] ?? $config['mode']['default'];
$modeResult = $gate['mode']->resolve($mode, $_SERVER['HTTP_X_SOVEREIGN_OWNER_APPROVAL'] ?? null);

$path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
if ($path === '/health') {
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok', 'mode' => $modeResult['mode'], 'network' => $modeResult['network']], JSON_THROW_ON_ERROR);
    exit;
}

if ($path === '/api/status') {
    header('Content-Type: application/json');
    echo json_encode([
        'service' => 'Sovereignty AI Studio PHPWin node',
        'mode' => $modeResult,
        'oauth' => $config['oauth'],
        'network' => $config['network'],
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
