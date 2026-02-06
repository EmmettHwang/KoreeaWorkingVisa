<?php
/**
 * User Registration API
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

// Required fields
$requiredFields = ['email', 'password', 'firstName', 'lastName', 'birthDate', 'nationality', 'phone'];

foreach ($requiredFields as $field) {
    if (empty($input[$field])) {
        sendResponse(false, "필수 항목이 누락되었습니다: {$field}");
    }
}

// Validate email
$email = sanitize($input['email']);
if (!isValidEmail($email)) {
    sendResponse(false, '올바른 이메일 형식이 아닙니다.');
}

// Validate password
$password = $input['password'];
if (!isValidPassword($password)) {
    sendResponse(false, '비밀번호는 8자 이상이며, 영문과 숫자를 포함해야 합니다.');
}

// Sanitize other inputs
$firstName = sanitize($input['firstName']);
$lastName = sanitize($input['lastName']);
$koreanName = sanitize($input['koreanName'] ?? '');
$birthDate = sanitize($input['birthDate']);
$nationality = sanitize($input['nationality']);
$phone = sanitize($input['phone']);
$agreeMarketing = !empty($input['agreeMarketing']) ? 1 : 0;

try {
    $pdo = getDBConnection();

    // Check if email already exists
    $stmt = $pdo->prepare('SELECT id FROM users WHERE email = ?');
    $stmt->execute([$email]);

    if ($stmt->fetch()) {
        sendResponse(false, '이미 사용 중인 이메일입니다.');
    }

    // Hash password
    $hashedPassword = password_hash($password, PASSWORD_BCRYPT, ['cost' => HASH_COST]);

    // Insert new user
    $stmt = $pdo->prepare('
        INSERT INTO users (
            email, password, first_name, last_name, korean_name,
            birth_date, nationality, phone, agree_marketing,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW())
    ');

    $stmt->execute([
        $email,
        $hashedPassword,
        $firstName,
        $lastName,
        $koreanName,
        $birthDate,
        $nationality,
        $phone,
        $agreeMarketing
    ]);

    $userId = $pdo->lastInsertId();

    // Log registration
    error_log("New user registered: {$email} (ID: {$userId})");

    sendResponse(true, '회원가입이 완료되었습니다.', [
        'userId' => $userId
    ]);

} catch (PDOException $e) {
    error_log("Registration error: " . $e->getMessage());
    sendResponse(false, '회원가입 처리 중 오류가 발생했습니다.');
}
