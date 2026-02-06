<?php
/**
 * Database Configuration
 * Korea Working Visa Application Platform
 */

// Database settings - 실제 값으로 변경하세요
define('DB_HOST', 'localhost');
define('DB_NAME', 'koreaworkingvisa');
define('DB_USER', 'your_username');
define('DB_PASS', 'your_password');
define('DB_CHARSET', 'utf8mb4');

// Security settings
define('HASH_COST', 12); // bcrypt cost factor
define('SESSION_LIFETIME', 86400 * 7); // 7 days

// Create database connection
function getDBConnection() {
    try {
        $dsn = "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=" . DB_CHARSET;
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ];
        return new PDO($dsn, DB_USER, DB_PASS, $options);
    } catch (PDOException $e) {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Database connection failed']);
        exit;
    }
}

// CORS headers for API
function setCORSHeaders() {
    header('Content-Type: application/json; charset=utf-8');
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');

    if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
        exit(0);
    }
}

// Get JSON input
function getJSONInput() {
    $input = file_get_contents('php://input');
    return json_decode($input, true) ?? [];
}

// Validate email format
function isValidEmail($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
}

// Validate password strength
function isValidPassword($password) {
    // Minimum 8 characters
    if (strlen($password) < 8) return false;
    // At least one letter
    if (!preg_match('/[a-zA-Z]/', $password)) return false;
    // At least one number
    if (!preg_match('/\d/', $password)) return false;
    return true;
}

// Sanitize input
function sanitize($input) {
    return htmlspecialchars(trim($input), ENT_QUOTES, 'UTF-8');
}

// Response helper
function sendResponse($success, $message = '', $data = []) {
    echo json_encode(array_merge(
        ['success' => $success, 'message' => $message],
        $data
    ));
    exit;
}
