<?php

declare(strict_types=1);

final class SovereigntyMode
{
    public function __construct(private readonly array $config) {}

    public function resolve(string $requested, ?string $approval): array
    {
        $mode = strtolower(trim($requested));
        if (!in_array($mode, ['local', 'hybrid', 'online'], true)) {
            $mode = $this->config['default'];
        }
        if ($mode === 'online' && !hash_equals('OWNER_APPROVED', (string) $approval)) {
            $mode = 'hybrid';
        }
        return [
            'mode' => $mode,
            'network' => $mode === 'local' ? 'loopback-only' : ($mode === 'hybrid' ? 'scoped-approval' : 'owner-approved'),
            'state' => 'device-local',
            'external_memory' => false,
        ];
    }
}

return [
    'mode' => new SovereigntyMode([
        'default' => 'local',
        'fallback' => 'hybrid',
    ]),
];
