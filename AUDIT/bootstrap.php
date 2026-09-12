<?php

declare(strict_types=1);

enum SovereigntyModeName: string
{
    case GHOST = 'ghost';
    case HYBRID = 'hybrid';
    case ONLINE = 'online';
}

final class SovereigntyMode
{
    public function __construct(
        private readonly array $config
    ) {}

    public function resolve(
        string $requested,
        ?string $approval = null
    ): array {
        $requestedMode = strtolower(trim($requested));

        $mode = match ($requestedMode) {
            'ghost', 'local' => SovereigntyModeName::GHOST,
            'hybrid' => SovereigntyModeName::HYBRID,
            'online' => SovereigntyModeName::ONLINE,
            default => $this->defaultMode(),
        };

        /*
         * Online capability NEVER implies external-memory capability.
         * Explicit owner authorization is required for Online.
         */
        if (
            $mode === SovereigntyModeName::ONLINE
            && !hash_equals(
                'OWNER_APPROVED',
                (string) $approval
            )
        ) {
            $mode = SovereigntyModeName::HYBRID;
        }

        return match ($mode) {
            SovereigntyModeName::GHOST => [
                'mode' => 'ghost',
                'network' => false,
                'external_memory' => false,
                'external_sync' => false,
                'state_location' => 'DEVICE_LOCAL',
                'state_policy' => [
                    'required_state_location' => 'DEVICE_ONLY',
                    'allow_external_memory' => false,
                    'allow_provider_training' => false,
                    'allow_cross_session_sync' => false,
                    'allow_telemetry' => false,
                ],
            ],

            SovereigntyModeName::HYBRID => [
                'mode' => 'hybrid',
                'network' => true,
                'external_memory' => 'PER_OPERATION',
                'external_sync' => 'PER_OPERATION',
                'state_location' => 'DEVICE_LOCAL',
                'state_policy' => [
                    'required_state_location' => 'DEVICE_FIRST',
                    'allow_external_memory' => false,
                    'allow_provider_training' => false,
                    'allow_cross_session_sync' => false,
                    'allow_telemetry' => true,
                ],
            ],

            SovereigntyModeName::ONLINE => [
                'mode' => 'online',
                'network' => true,
                'external_memory' => 'OPT_IN_ONLY',
                'external_sync' => 'OPT_IN_ONLY',
                'state_location' => 'DEVICE_LOCAL',
                'state_policy' => [
                    'required_state_location' => 'DEVICE_FIRST',
                    'allow_external_memory' => false,
                    'allow_provider_training' => false,
                    'allow_cross_session_sync' => false,
                    'allow_telemetry' => true,
                ],
            ],
        };
    }

    private function defaultMode(): SovereigntyModeName
    {
        $default = strtolower(
            trim((string) ($this->config['default'] ?? 'ghost'))
        );

        return match ($default) {
            'ghost', 'local' => SovereigntyModeName::GHOST,
            'hybrid' => SovereigntyModeName::HYBRID,
            'online' => SovereigntyModeName::ONLINE,
            default => SovereigntyModeName::GHOST,
        };
    }
}

return [
    'mode' => new SovereigntyMode([
        'default' => 'ghost',
        'fallback' => 'hybrid',
    ]),
];
