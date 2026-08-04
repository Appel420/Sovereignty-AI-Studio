<?php

declare(strict_types=1);

require dirname(__DIR__) . '/scripts/php_local_bootstrap.php';
sovereignty_require_loopback();

$config = json_decode((string) file_get_contents(dirname(__DIR__) . '/phpwin.json'), true, 512, JSON_THROW_ON_ERROR);
if (($config['diagnostics']['phpinfo_enabled'] ?? false) !== true) {
    http_response_code(404);
    exit('Diagnostics disabled');
}
if (($_SERVER['HTTP_X_SOVEREIGNTY_DIAGNOSTICS'] ?? '') !== 'OWNER_LOCAL_ONLY') {
    http_response_code(403);
    exit('Owner diagnostics header required');
}

phpinfo(INFO_GENERAL | INFO_CONFIGURATION | INFO_MODULES);
