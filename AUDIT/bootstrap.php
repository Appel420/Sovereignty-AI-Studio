<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$events = $root . '/AUDIT/events';
if (!is_dir($events)) {
    mkdir($events, 0700, true);
}

$record = static function (string $type, array $payload) use ($events): array {
    $entry = [
        'id' => bin2hex(random_bytes(16)),
        'type' => $type,
        'timestamp' => gmdate('c'),
        'payload' => $payload,
    ];
    file_put_contents($events . '/events.jsonl', json_encode($entry, JSON_THROW_ON_ERROR) . PHP_EOL, FILE_APPEND | LOCK_EX);
    return $entry;
};

$status = static function () use ($events): array {
    $file = $events . '/events.jsonl';
    return ['enabled' => true, 'path' => 'AUDIT/events/events.jsonl', 'entries' => is_file($file) ? count(file($file, FILE_IGNORE_NEW_LINES)) : 0];
};

return ['record' => $record, 'status' => $status];
