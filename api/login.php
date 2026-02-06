<?php
/**
 * User Login API
 * Korea Working Visa Application Platform
 */

require_once 'config.php';

setCORSHeaders();
session_start();

// Only accept POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    sendResponse(false, 'Method not allowed');
}

$input = getJSONInput();

// Validate required fields
if (empty($input['email']) || empty($input['password'])) {
    sendResponse(false, '이메일과 비밀번호를 입력해주세요.');
}

$email = sanitize($input['email']);
$password = $input['password'];
$rememberMe = !empty($input['rememberMe']);

try {
    $pdo = getDBConnection();

    // Get user by email
    $stmt = $pdo->prepare('
        SELECT id, email, password, first_name, last_name, korean_name,
               nationality, status, last_login
        FROM users
        WHERE email = ?
    ');
    $stmt->execute([$email]);
    $user = $stmt->fetch();

    // User not found or password incorrect
    if (!$user || !password_verify($password, $user['password'])) {
        // Add delay to prevent brute force
        sleep(1);
        sendResponse(false, '이메일 또는 비밀번호가 올바르지 않습니다.');
    }

    // Check if account is active
    if ($user['status'] !== 'active') {
        sendResponse(false, '비활성화된 계정입니다. 관리자에게 문의하세요.');
    }

    // Update last login
    $stmt = $pdo->prepare('UPDATE users SET last_login = NOW() WHERE id = ?');
    $stmt->execute([$user['id']]);

    // Create session
    $_SESSION['user_id'] = $user['id'];
    $_SESSION['user_email'] = $user['email'];
    $_SESSION['logged_in'] = true;

    // Set session lifetime if remember me
    if ($rememberMe) {
        $lifetime = SESSION_LIFETIME;
        setcookie(session_name(), session_id(), time() + $lifetime, '/');
    }

    // Prepare user data for response (exclude password)
    unset($user['password']);

    sendResponse(true, '로그인 성공', [
        'user' => $user,
        'redirect' => 'kwv-dashboard.html'
    ]);

} catch (PDOException $e) {
    error_log("Login error: " . $e->getMessage());
    sendResponse(false, '로그인 처리 중 오류가 발생했습니다.');
}
