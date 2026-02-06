<?php
/**
 * User Logout API
 * Korea Working Visa Application Platform
 */

require_once 'config.php';

setCORSHeaders();
session_start();

// Destroy session
$_SESSION = [];

if (ini_get("session.use_cookies")) {
    $params = session_get_cookie_params();
    setcookie(session_name(), '', time() - 42000,
        $params["path"], $params["domain"],
        $params["secure"], $params["httponly"]
    );
}

session_destroy();

sendResponse(true, '로그아웃 되었습니다.', [
    'redirect' => 'kwv-login.html'
]);
