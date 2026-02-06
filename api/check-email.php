<?php
/**
 * Email Availability Check API
 * Korea Working Visa Application Platform
 */

require_once 'config.php';

setCORSHeaders();

// Only accept POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    sendResponse(false, 'Method not allowed');
}

$input = getJSONInput();

if (empty($input['email'])) {
    sendResponse(false, '이메일을 입력해주세요.');
}

$email = sanitize($input['email']);

if (!isValidEmail($email)) {
    sendResponse(false, '올바른 이메일 형식이 아닙니다.', ['available' => false]);
}

try {
    $pdo = getDBConnection();

    $stmt = $pdo->prepare('SELECT id FROM users WHERE email = ?');
    $stmt->execute([$email]);

    $exists = $stmt->fetch() !== false;

    sendResponse(true, '', [
        'available' => !$exists,
        'message' => $exists ? '이미 사용 중인 이메일입니다.' : '사용 가능한 이메일입니다.'
    ]);

} catch (PDOException $e) {
    error_log("Email check error: " . $e->getMessage());
    sendResponse(false, '확인 중 오류가 발생했습니다.', ['available' => false]);
}
