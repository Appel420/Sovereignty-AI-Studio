# PHPWin/iOS local runtime configuration

The supplied `phpinfo()` report identifies a native embedded PHP 8.2.31 runtime
inside PHPWin on iOS 26 / Darwin ARM64, served by CocoaHTTPServer on
`https://127.0.0.1`.

Because PHPWin reports no loaded `php.ini`, this repository provides two local
configuration layers:

1. `config/php/local.ini` for PHP CLI or a server invocation that accepts `-c`.
2. `scripts/php_local_bootstrap.php` for application startup when the embedded
   server does not load a PHP configuration file.

The profile disables PHP information leakage, display errors, remote includes,
and URL fopen in offline mode. It also enables safer HTTPS session-cookie
settings. It does not claim to disable compiled PHP extensions; application
routes must still enforce loopback destination checks with
`sovereignty_require_loopback()` before any cURL or stream request.

Use locally:

```bash
python3 scripts/validate-php-ios-environment.py
php -c config/php/local.ini -r 'phpinfo(INFO_CONFIGURATION);'
```

For PHPWin, include the bootstrap at the first application entry point:

```php
require __DIR__ . '/scripts/php_local_bootstrap.php';
```

Keep the PHPWin server bound to `127.0.0.1`. Hybrid and online behavior must
remain explicit runtime modes; a local PHP failure must not silently create an
external request.
