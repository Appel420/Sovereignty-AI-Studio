<?php

declare(strict_types=1);

final class SgHvBus
{
    public function emit(string $type, array $payload, array $mode): array
    {
        return [
            'id' => bin2hex(random_bytes(16)),
            'type' => $type,
            'mode' => $mode,
            'payload' => $payload,
            'timestamp' => gmdate('c'),
        ];
    }
}

$bus = new SgHvBus();
return ['emit' => $bus->emit(...), 'class' => SgHvBus::class];
