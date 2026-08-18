<?php

declare(strict_types=1);

final class SovereigntyMode
{
    private const MODES = ['local', 'hybrid', 'online'];

    public function __construct(private readonly array $config)
    {
        if (!isset($config['default']) || !in_array($config['default'], self::MODES, true)) {
            throw new InvalidArgumentException('Invalid SovereigntyMode default');
        }
        if (!isset($config['fallback']) || !in_array($config['fallback'], self::MODES, true)) {
            throw new InvalidArgumentException('Invalid SovereigntyMode fallback');
        }
    }

    public function resolve(string $requested, ?string $approval): array
    {
        $mode = strtolower(trim($requested));
        if (!in_array($mode, self::MODES, true)) {
            $mode = $this->config['default'];
        }

        if ($mode === 'online' && !$this->approvalAccepted($approval)) {
            $mode = $this->config['fallback'];
        }

        return [
            'mode' => $mode,
            'network' => match ($mode) {
                'local' => 'loopback-only',
                'hybrid' => 'scoped-approval',
                'online' => 'owner-approved',
            },
            'state' => 'device-local',
            'external_memory' => false,
        ];
    }

    private function approvalAccepted(?string $approval): bool
    {
        if ($approval === null || $approval === '') {
            return false;
        }

        $verifier = $this->config['approval_verifier'] ?? null;
        if (is_callable($verifier)) {
            return (bool) $verifier($approval);
        }

        $expected = $this->config['online_approval'] ?? null;
        return is_string($expected)
            && $expected !== ''
            && hash_equals($expected, $approval);
    }
}

return [
    'mode' => new SovereigntyMode([
        'default' => 'local',
        'fallback' => 'hybrid',
        'online_approval' => getenv('SOVEREIGNTY_ONLINE_APPROVAL') ?: null,
    ]),
];
