# -*- coding: utf-8 -*-
"""
KoreaWorkingVisa API 모듈
- 관리자/비자신청자 인증 및 관리
- Google OAuth 연동
- JWT 토큰 기반 인증
"""

from fastapi import APIRouter, HTTPException, Depends, Header, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import json
import hashlib
import secrets
import uuid
import base64
import httpx

# JWT 관련 (python-jose)
try:
    from jose import JWTError, jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("⚠️ python-jose not installed. JWT features will be limited.")

# bcrypt 관련
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("⚠️ bcrypt not installed. Using simple hash fallback.")

# ==================== 설정 ====================
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "kwv-secret-key-change-in-production-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# 파일 업로드 경로
LOCAL_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "file_uploads")
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)

# 기본 비밀번호
DEFAULT_PASSWORD = "kwv2026"

# ==================== Router ====================
router = APIRouter(prefix="/api/kwv", tags=["KoreaWorkingVisa"])

# ==================== Pydantic Models ====================
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    language: Optional[str] = "en"
    user_type: Optional[str] = "applicant"  # applicant 또는 admin
    organization: Optional[str] = None  # 관리자: 소속 지역
    profile_photo: Optional[str] = None  # Base64 또는 URL
    passport_copy_url: Optional[str] = None
    visa_copy_url: Optional[str] = None
    id_card_url: Optional[str] = None
    insurance_cert_url: Optional[str] = None
    # Phase 2 추가
    nationality: Optional[str] = None  # 국적
    visa_type: Optional[str] = None  # 비자 유형 (E-8, E-9 등)
    birth_date: Optional[str] = None  # 생년월일
    gender: Optional[str] = None  # 성별
    target_local_government_id: Optional[int] = None  # 신청 대상 지자체

class GoogleLoginRequest(BaseModel):
    credential: Optional[str] = None  # Google ID token (legacy)
    email: Optional[str] = None
    name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class ApplicantCreate(BaseModel):
    nationality: str
    passport_number: str
    birth_date: str
    gender: str
    visa_type: str
    employer_name: Optional[str] = None
    job_category: Optional[str] = None

class ApplicantStatusUpdate(BaseModel):
    status: str  # pending, processing, approved, rejected
    rejection_reason: Optional[str] = None

# ==================== 유틸리티 함수 ====================

def hash_password(password: str) -> str:
    """비밀번호 해시"""
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """비밀번호 검증"""
    if BCRYPT_AVAILABLE:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except:
            return False
    else:
        return hashlib.sha256(password.encode()).hexdigest() == hashed

# DB 세션 토큰 저장소 (JWT 불가 시 사용)
_token_store = {}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 토큰 생성 (JWT 불가 시 DB 세션 토큰)"""
    if not JWT_AVAILABLE:
        import secrets
        token = secrets.token_hex(32)
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        _token_store[token] = {**data, "exp": expire.isoformat()}
        return token

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """JWT 토큰 디코딩"""
    if not JWT_AVAILABLE:
        stored = _token_store.get(token)
        if not stored:
            return None
        if datetime.fromisoformat(stored["exp"]) < datetime.utcnow():
            del _token_store[token]
            return None
        return {k: v for k, v in stored.items() if k != "exp"}
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """현재 로그인한 사용자 정보 가져오기"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증이 필요합니다")

    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다")

    return payload

def require_admin(user: dict) -> dict:
    """관리자 권한 확인"""
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    return user

def require_admin_level(user: dict, min_level: int) -> dict:
    """특정 등급 이상의 관리자 권한 확인 (숫자가 클수록 높은 권한, 9=super admin)"""
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    if user.get("admin_level", 0) < min_level:
        raise HTTPException(status_code=403, detail=f"등급 {min_level} 이상의 관리자 권한이 필요합니다")
    return user

# ==================== 데이터베이스 연결 ====================
MOCK_MODE = os.getenv('KWV_MOCK_MODE', 'false').lower() == 'true'

# Mock 데이터 (MOCK_MODE=true일 때만 사용)
MOCK_USERS = {}
MOCK_USER_ID_COUNTER = 1
MOCK_APPLICATIONS = []

def get_kwv_db_connection():
    """KWV 데이터베이스 연결"""
    if MOCK_MODE:
        return None

    import pymysql
    from pathlib import Path
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path, override=True)

    try:
        return pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            passwd=os.getenv('DB_PASSWORD', ''),
            db=os.getenv('DB_NAME', 'koreaworkingvisa'),
            charset='utf8mb4',
            port=int(os.getenv('DB_PORT', '3306'))
        )
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")
        return None

# ==================== 인증 API ====================

@router.post("/auth/register")
async def register(user_data: UserRegister):
    """
    회원가입
    - applicant (일반 사용자): 비자 신청자 (여권+비자 첨부)
    - admin (관리자): 지역별 담당자 (신분증+4대보험 첨부)
    - 비밀번호는 입력받지 않고 기본값 'kwv2026' 사용
    """
    global MOCK_USER_ID_COUNTER

    if user_data.user_type not in ["applicant", "admin"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 사용자 유형입니다")

    # 프로필 사진 Base64 → 파일 저장
    profile_photo_url = None
    if user_data.profile_photo and user_data.profile_photo.startswith('data:'):
        profile_photo_url = save_base64_file(user_data.profile_photo, "profile")
    elif user_data.profile_photo:
        profile_photo_url = user_data.profile_photo

    # Mock mode 처리
    if MOCK_MODE:
        for u in MOCK_USERS.values():
            if u["email"] == user_data.email:
                raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")

        user_id = MOCK_USER_ID_COUNTER
        MOCK_USER_ID_COUNTER += 1

        is_admin = user_data.user_type == "admin"
        new_user = {
            "id": user_id,
            "email": user_data.email,
            "password_hash": hash_password(DEFAULT_PASSWORD),
            "name": user_data.name,
            "phone": user_data.phone,
            "address": user_data.address,
            "user_type": user_data.user_type,
            "admin_level": 2 if is_admin else None,
            "language": user_data.language,
            "is_active": True,
            "is_approved": True,
            "organization": user_data.organization,
            "profile_photo": profile_photo_url,
            "created_at": datetime.utcnow().isoformat()
        }
        MOCK_USERS[user_id] = new_user

        token_data = {
            "sub": str(user_id),
            "email": user_data.email,
            "name": user_data.name,
            "user_type": user_data.user_type,
            "admin_level": 2 if is_admin else None
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_HOURS * 3600,
            "user": {
                "id": user_id,
                "email": user_data.email,
                "name": user_data.name,
                "user_type": user_data.user_type,
                "admin_level": 2 if is_admin else None,
                "language": user_data.language
            }
        }

    # 실제 DB 모드
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM kwv_users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다")

        # 기본 비밀번호 kwv2026 해시
        password_salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((DEFAULT_PASSWORD + password_salt).encode()).hexdigest()

        user_type = user_data.user_type or 'applicant'

        # 승인 모드 확인
        approval_mode = 'manual'
        try:
            cursor.execute("SELECT setting_value FROM kwv_system_settings WHERE setting_key = 'approval_mode'")
            row = cursor.fetchone()
            if row:
                approval_mode = row[0]
        except:
            pass

        # applicant는 일단 미승인으로 생성, 자동 승인은 필수항목 검증 후 결정
        is_approved = True if user_type == 'admin' else False

        cursor.execute("""
            INSERT INTO kwv_users (email, password_hash, password_salt, name, phone, address,
                user_type, admin_level, language, organization, region, profile_photo,
                target_local_government_id, is_approved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data.email,
            password_hash,
            password_salt,
            user_data.name,
            user_data.phone or '',
            user_data.address or '',
            user_type,
            2 if user_type == 'admin' else 0,
            user_data.language or 'en',
            user_data.organization if user_type == 'admin' else None,
            user_data.organization if user_type == 'admin' else None,
            profile_photo_url,
            user_data.target_local_government_id if user_type == 'applicant' else None,
            is_approved
        ))

        user_id = cursor.lastrowid

        # 첨부 파일 정보 저장
        file_entries = []
        if user_data.passport_copy_url:
            file_entries.append((user_id, 'passport_copy', 'passport', user_data.passport_copy_url))
        if user_data.visa_copy_url:
            file_entries.append((user_id, 'visa_copy', 'visa', user_data.visa_copy_url))
        if user_data.id_card_url:
            file_entries.append((user_id, 'id_card', 'id_card', user_data.id_card_url))
        if user_data.insurance_cert_url:
            file_entries.append((user_id, 'insurance_cert', 'insurance', user_data.insurance_cert_url))

        for uid, category, fname, fpath in file_entries:
            cursor.execute("""
                INSERT INTO kwv_file_uploads (user_id, file_category, file_name, file_path)
                VALUES (%s, %s, %s, %s)
            """, (uid, category, fname, fpath))

        # applicant인 경우 비자 신청 정보 저장
        if user_type == 'applicant':
            cursor.execute("""
                INSERT INTO kwv_visa_applicants (user_id, visa_type, nationality, birth_date, gender)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user_id,
                user_data.visa_type,
                user_data.nationality,
                user_data.birth_date or None,
                user_data.gender or None
            ))

        # 자동 승인 모드일 때 필수 항목 검증
        auto_approved = False
        if approval_mode == 'auto' and user_type == 'applicant':
            check = check_auto_approval(user_id, conn)
            if check["passed"]:
                cursor.execute("""
                    UPDATE kwv_users SET is_approved = TRUE, approved_at = NOW() WHERE id = %s
                """, (user_id,))
                cursor.execute("""
                    UPDATE kwv_visa_applicants SET application_status = 'approved' WHERE user_id = %s
                """, (user_id,))
                auto_approved = True

        conn.commit()

        token_data = {
            "sub": str(user_id),
            "email": user_data.email,
            "name": user_data.name,
            "user_type": user_type,
            "admin_level": 2 if user_type == 'admin' else 0
        }
        access_token = create_access_token(token_data)

        response = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_HOURS * 3600,
            "user": {
                "id": user_id,
                "email": user_data.email,
                "name": user_data.name,
                "user_type": user_type,
                "admin_level": 2 if user_type == 'admin' else 0,
                "language": user_data.language,
                "is_approved": auto_approved if user_type == 'applicant' else True
            }
        }
        # 자동 승인 실패 시 누락 항목 알려주기
        if approval_mode == 'auto' and user_type == 'applicant' and not auto_approved:
            check = check_auto_approval(user_id, conn)
            response["approval_status"] = "pending"
            response["missing_items"] = check.get("missing", [])
        elif auto_approved:
            response["approval_status"] = "approved"

        return response
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"회원가입 실패: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """일반 로그인 (이메일 + 비밀번호)"""

    if MOCK_MODE:
        user = None
        for u in MOCK_USERS.values():
            if u["email"] == credentials.email:
                user = u
                break

        if not user:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="비활성화된 계정입니다")

        if not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "user_type": user["user_type"],
            "admin_level": user["admin_level"]
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_HOURS * 3600,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "user_type": user["user_type"],
                "admin_level": user["admin_level"],
                "language": user.get("language", "en")
            }
        }

    # 실제 DB 모드
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, password_hash, password_salt, name, user_type, admin_level, language, is_active
            FROM kwv_users WHERE email = %s
        """, (credentials.email,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

        user_id, email, password_hash, password_salt, name, user_type, admin_level, language, is_active = user
        name = name or email
        status = 'active' if is_active else 'inactive'
        user_type = user_type or 'applicant'
        admin_level = admin_level or 0
        language = language or 'ko'

        if status != 'active':
            raise HTTPException(status_code=403, detail="비활성화된 계정입니다")

        check_hash = hashlib.sha256((credentials.password + password_salt).encode()).hexdigest()
        if check_hash != password_hash:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

        cursor.execute("UPDATE kwv_users SET last_login_at = NOW() WHERE id = %s", (user_id,))
        conn.commit()

        token_data = {
            "sub": str(user_id),
            "email": email,
            "name": name,
            "user_type": user_type,
            "admin_level": admin_level
        }
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_HOURS * 3600,
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "user_type": user_type,
                "admin_level": admin_level,
                "language": language
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 실패: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/auth/google")
async def google_login(request: GoogleLoginRequest):
    """Google OAuth 로그인/가입"""

    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth가 설정되지 않았습니다")

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests

        idinfo = id_token.verify_oauth2_token(
            request.credential,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )

        email = idinfo.get('email')
        name = idinfo.get('name', email.split('@')[0])
        google_id = idinfo.get('sub')

        conn = get_kwv_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Database connection failed")

        try:
            cursor = conn.cursor()

            cursor.execute("SELECT id, name, user_type, admin_level, language FROM kwv_users WHERE email = %s", (email,))
            existing = cursor.fetchone()

            if existing:
                user_id, name, user_type, admin_level, language = existing
                cursor.execute("UPDATE kwv_users SET last_login_at = NOW(), oauth_provider = 'google', oauth_id = %s WHERE id = %s",
                             (google_id, user_id))
            else:
                cursor.execute("""
                    INSERT INTO kwv_users (email, name, user_type, oauth_provider, oauth_id, language, is_approved)
                    VALUES (%s, %s, 'applicant', 'google', %s, 'en', TRUE)
                """, (email, name, google_id))
                user_id = cursor.lastrowid
                user_type = 'applicant'
                admin_level = None
                language = 'en'

            conn.commit()

            token_data = {
                "sub": str(user_id),
                "email": email,
                "name": name,
                "user_type": user_type,
                "admin_level": admin_level
            }
            access_token = create_access_token(token_data)

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": JWT_EXPIRATION_HOURS * 3600,
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": name,
                    "user_type": user_type,
                    "admin_level": admin_level,
                    "language": language
                }
            }
        finally:
            conn.close()

    except ImportError:
        raise HTTPException(status_code=503, detail="Google Auth 라이브러리가 설치되지 않았습니다")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google 인증 실패: {str(e)}")

@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """현재 로그인한 사용자 정보"""
    return {
        "id": user.get("sub"),
        "email": user.get("email"),
        "name": user.get("name"),
        "user_type": user.get("user_type"),
        "admin_level": user.get("admin_level")
    }

@router.post("/auth/logout")
async def logout():
    """로그아웃 (클라이언트에서 토큰 삭제)"""
    return {"message": "로그아웃 성공"}

# ==================== 관리자 API ====================

@router.get("/admin/applicants")
async def get_applicants(
    status: Optional[str] = None,
    nationality: Optional[str] = None,
    visa_type: Optional[str] = None,
    lg_id: Optional[int] = None,
    is_approved: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """신청자 목록 조회 (관리자용) - 필터 강화"""
    require_admin(user)

    conn = get_kwv_db_connection()
    if not conn:
        return {"applicants": [], "total": 0, "page": page, "limit": limit}

    try:
        cursor = conn.cursor()

        where_clause = "WHERE u.user_type = 'applicant'"
        params = []

        if status:
            where_clause += " AND a.application_status = %s"
            params.append(status)
        if nationality:
            where_clause += " AND a.nationality = %s"
            params.append(nationality)
        if visa_type:
            where_clause += " AND a.visa_type = %s"
            params.append(visa_type)
        if lg_id:
            where_clause += " AND u.target_local_government_id = %s"
            params.append(lg_id)
        if is_approved == 'true':
            where_clause += " AND u.is_approved = TRUE"
        elif is_approved == 'false':
            where_clause += " AND u.is_approved = FALSE"
        if search:
            where_clause += " AND (u.name LIKE %s OR u.email LIKE %s OR u.phone LIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        cursor.execute(f"""
            SELECT COUNT(*) FROM kwv_users u
            LEFT JOIN kwv_visa_applicants a ON u.id = a.user_id
            {where_clause}
        """, params)
        total = cursor.fetchone()[0]

        offset = (page - 1) * limit
        cursor.execute(f"""
            SELECT u.id, u.email, u.name, u.phone, u.created_at,
                   a.visa_type, a.nationality, a.application_status,
                   u.is_approved, u.approved_at, u.target_local_government_id,
                   u.local_government_id, u.profile_photo, u.language,
                   lg.name as lg_name, tlg.name as target_lg_name,
                   a.birth_date, a.gender
            FROM kwv_users u
            LEFT JOIN kwv_visa_applicants a ON u.id = a.user_id
            LEFT JOIN kwv_local_governments lg ON u.local_government_id = lg.id
            LEFT JOIN kwv_local_governments tlg ON u.target_local_government_id = tlg.id
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        applicants = []
        for row in cursor.fetchall():
            applicants.append({
                "id": row[0],
                "email": row[1],
                "name": row[2],
                "phone": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "visa_type": row[5],
                "nationality": row[6],
                "status": row[7] or "pending",
                "is_approved": bool(row[8]),
                "approved_at": row[9].isoformat() if row[9] else None,
                "target_local_government_id": row[10],
                "local_government_id": row[11],
                "profile_photo": row[12],
                "language": row[13],
                "lg_name": row[14],
                "target_lg_name": row[15],
                "birth_date": row[16].isoformat() if row[16] else None,
                "gender": row[17]
            })

        # 필터용 메타데이터
        cursor.execute("SELECT DISTINCT nationality FROM kwv_visa_applicants WHERE nationality IS NOT NULL ORDER BY nationality")
        nationalities = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT DISTINCT visa_type FROM kwv_visa_applicants WHERE visa_type IS NOT NULL ORDER BY visa_type")
        visa_types = [r[0] for r in cursor.fetchall()]

        return {
            "applicants": applicants,
            "total": total,
            "page": page,
            "limit": limit,
            "filters": {
                "nationalities": nationalities,
                "visa_types": visa_types
            }
        }
    finally:
        conn.close()

@router.get("/admin/statistics")
async def get_statistics(user: dict = Depends(get_current_user)):
    """대시보드 통계 (관리자용)"""
    require_admin(user)

    conn = get_kwv_db_connection()
    if not conn:
        return {
            "total_applicants": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "processing": 0
        }

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM kwv_users WHERE user_type = 'applicant'")
        total = cursor.fetchone()[0]

        stats = {"total_applicants": total, "pending": 0, "approved": 0, "rejected": 0, "processing": 0}

        cursor.execute("""
            SELECT application_status, COUNT(*) FROM kwv_visa_applicants
            GROUP BY application_status
        """)
        for row in cursor.fetchall():
            if row[0] in stats:
                stats[row[0]] = row[1]

        return stats
    finally:
        conn.close()

@router.put("/admin/applicants/{applicant_id}/status")
async def update_applicant_status(
    applicant_id: int,
    status_update: ApplicantStatusUpdate,
    user: dict = Depends(get_current_user)
):
    """신청자 상태 변경 (관리자용)"""
    require_admin_level(user, 2)

    valid_statuses = ["pending", "processing", "approved", "rejected"]
    if status_update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="유효하지 않은 상태입니다")

    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")

    try:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE kwv_visa_applicants
            SET application_status = %s, rejection_reason = %s, updated_at = NOW()
            WHERE user_id = %s
        """, (status_update.status, status_update.rejection_reason, applicant_id))

        # kwv_users의 승인 상태도 동기화
        if status_update.status == 'approved':
            cursor.execute("""
                UPDATE kwv_users SET is_approved = TRUE, approved_at = NOW(),
                approved_by = %s, rejection_reason = NULL WHERE id = %s
            """, (user.get('sub'), applicant_id))
        elif status_update.status == 'rejected':
            cursor.execute("""
                UPDATE kwv_users SET is_approved = FALSE,
                rejection_reason = %s WHERE id = %s
            """, (status_update.rejection_reason, applicant_id))

        conn.commit()
        return {"message": "상태가 변경되었습니다", "status": status_update.status}
    finally:
        conn.close()

@router.put("/admin/applicants/{applicant_id}/assign-lg")
async def assign_local_government(applicant_id: int, request: Request, user: dict = Depends(get_current_user)):
    """근로자를 지자체에 배정"""
    require_admin_level(user, 2)
    body = await request.json()
    lg_id = body.get("local_government_id")
    if not lg_id:
        raise HTTPException(status_code=400, detail="지자체 ID가 필요합니다")

    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        # 지자체 TO 확인
        cursor.execute("SELECT allocated_quota, used_quota, name FROM kwv_local_governments WHERE id = %s AND is_active = TRUE", (lg_id,))
        lg = cursor.fetchone()
        if not lg:
            raise HTTPException(status_code=404, detail="지자체를 찾을 수 없습니다")
        if lg[0] > 0 and lg[1] >= lg[0]:
            raise HTTPException(status_code=400, detail=f"'{lg[2]}' 지자체의 TO가 부족합니다 ({lg[1]}/{lg[0]})")

        # 배정
        cursor.execute("UPDATE kwv_users SET local_government_id = %s WHERE id = %s AND user_type = 'applicant'", (lg_id, applicant_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="신청자를 찾을 수 없습니다")

        # used_quota 증가
        cursor.execute("UPDATE kwv_local_governments SET used_quota = used_quota + 1 WHERE id = %s", (lg_id,))
        conn.commit()
        return {"message": f"'{lg[2]}' 지자체에 배정되었습니다"}
    finally:
        conn.close()

def check_auto_approval(user_id: int, conn) -> dict:
    """자동 승인 필수 항목 검증 - 모든 항목이 충족되어야 자동 승인"""
    cursor = conn.cursor()
    missing = []

    # 1. 기본 정보 확인
    cursor.execute("""
        SELECT name, phone, profile_photo, target_local_government_id
        FROM kwv_users WHERE id = %s
    """, (user_id,))
    user_row = cursor.fetchone()
    if not user_row:
        return {"passed": False, "missing": ["사용자 정보 없음"]}

    name, phone, profile_photo, target_lg = user_row
    if not name: missing.append("이름")
    if not phone: missing.append("전화번호")
    if not profile_photo: missing.append("프로필 사진")
    if not target_lg: missing.append("신청 대상 지자체")

    # 2. 비자 정보 확인
    cursor.execute("""
        SELECT nationality, visa_type, passport_number, birth_date, gender
        FROM kwv_visa_applicants WHERE user_id = %s
    """, (user_id,))
    visa_row = cursor.fetchone()
    if not visa_row:
        missing.extend(["국적", "비자유형", "여권번호", "생년월일", "성별"])
    else:
        nat, vtype, passport, bdate, gender = visa_row
        if not nat: missing.append("국적")
        if not vtype: missing.append("비자유형")
        if not passport: missing.append("여권번호")
        if not bdate: missing.append("생년월일")
        if not gender: missing.append("성별")

    # 3. 필수 서류 확인 (여권 사본, 비자 사본)
    cursor.execute("""
        SELECT file_category FROM kwv_file_uploads WHERE user_id = %s
        AND file_category IN ('passport_copy', 'visa_copy')
    """, (user_id,))
    uploaded = {r[0] for r in cursor.fetchall()}
    if 'passport_copy' not in uploaded: missing.append("여권 사본")
    if 'visa_copy' not in uploaded: missing.append("비자 사본")

    return {"passed": len(missing) == 0, "missing": missing}

# ==================== 신청자 API ====================

@router.get("/my/profile")
async def get_my_profile(user: dict = Depends(get_current_user)):
    """내 프로필 조회"""
    conn = get_kwv_db_connection()
    if not conn:
        return {"id": user.get("sub"), "email": user.get("email"), "name": user.get("name")}

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, name, phone, language, profile_photo, created_at
            FROM kwv_users WHERE id = %s
        """, (user.get("sub"),))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

        return {
            "id": row[0],
            "email": row[1],
            "name": row[2],
            "phone": row[3],
            "language": row[4],
            "profile_photo": row[5],
            "created_at": row[6].isoformat() if row[6] else None
        }
    finally:
        conn.close()

@router.get("/my/application")
async def get_my_application(user: dict = Depends(get_current_user)):
    """내 비자 신청 현황"""
    conn = get_kwv_db_connection()
    if not conn:
        return {"application": None}

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.visa_type, a.nationality, a.passport_number,
                   a.application_status, a.created_at, a.updated_at
            FROM kwv_visa_applicants a
            WHERE a.user_id = %s
            ORDER BY a.created_at DESC LIMIT 1
        """, (user.get("sub"),))

        row = cursor.fetchone()
        if not row:
            return {"application": None}

        return {
            "application": {
                "id": row[0],
                "visa_type": row[1],
                "nationality": row[2],
                "passport_number": row[3],
                "status": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "updated_at": row[6].isoformat() if row[6] else None
            }
        }
    finally:
        conn.close()

@router.post("/my/application")
async def create_application(
    application: ApplicantCreate,
    user: dict = Depends(get_current_user)
):
    """비자 신청"""
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")

    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM kwv_visa_applicants WHERE user_id = %s", (user.get("sub"),))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="이미 신청서가 존재합니다")

        cursor.execute("""
            INSERT INTO kwv_visa_applicants
            (user_id, visa_type, nationality, passport_number, birth_date, gender, employer_name, job_category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user.get("sub"),
            application.visa_type,
            application.nationality,
            application.passport_number,
            application.birth_date,
            application.gender,
            application.employer_name,
            application.job_category
        ))

        conn.commit()
        return {"message": "신청이 완료되었습니다", "application_id": cursor.lastrowid}
    finally:
        conn.close()

# ==================== 파일 업로드 API ====================

def upload_to_local(file_data: bytes, filename: str, category: str) -> str:
    """파일을 로컬에 저장하고 URL 반환"""
    cat_dir = os.path.join(LOCAL_UPLOAD_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)
    file_path = os.path.join(cat_dir, filename)
    with open(file_path, 'wb') as f:
        f.write(file_data)
    return f"/api/kwv/uploads/{category}/{filename}"

def save_base64_file(base64_data: str, category: str) -> str:
    """Base64 데이터를 파일로 저장"""
    if ',' in base64_data:
        base64_data = base64_data.split(',', 1)[1]
    file_data = base64.b64decode(base64_data)
    ext = 'jpg'
    filename = f"{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}.{ext}"
    return upload_to_local(file_data, filename, category)

@router.get("/uploads/{category}/{filename}")
async def serve_upload(category: str, filename: str):
    """업로드된 파일 서빙"""
    file_path = os.path.join(LOCAL_UPLOAD_DIR, category, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

@router.post("/auth/upload-temp")
async def upload_temp_file(file: UploadFile = File(...), category: str = Form("temp")):
    """가입 전 임시 파일 업로드"""
    allowed = {'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf'}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다")

    file_data = await file.read()
    if len(file_data) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과합니다")

    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'bin'
    filename = f"{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:8]}.{ext}"
    url = upload_to_local(file_data, filename, category)
    return {"url": url, "filename": filename}

# ==================== Google OAuth 서버 플로우 ====================

@router.get("/auth/google/start")
async def google_auth_start(request: Request, mode: str = "register"):
    """Google OAuth 시작 - Google 로그인 페이지로 리다이렉트"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth가 설정되지 않았습니다")

    # 콜백 URL 구성
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.hostname)
    redirect_uri = f"{scheme}://{host}/kwv-google-callback.html"

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid+profile+email"
        "&access_type=online"
        "&prompt=select_account"
        f"&state={mode}"
    )
    return RedirectResponse(url=google_auth_url)

@router.get("/auth/google/exchange")
async def google_auth_exchange(request: Request, code: str = None):
    """Google OAuth code를 사용자 정보로 교환"""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code가 필요합니다")

    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.hostname)
    redirect_uri = f"{scheme}://{host}/kwv-google-callback.html"

    try:
        async with httpx.AsyncClient() as client:
            # code → access_token 교환
            token_resp = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            })
            token_data = token_resp.json()

            if "error" in token_data:
                raise HTTPException(status_code=400, detail=token_data.get("error_description", "Token exchange failed"))

            # access_token으로 사용자 정보 가져오기
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            userinfo = userinfo_resp.json()

            return {
                "name": userinfo.get("name", ""),
                "email": userinfo.get("email", ""),
                "picture": userinfo.get("picture", "")
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google 인증 처리 실패: {str(e)}")

@router.post("/auth/google-login")
async def google_login_by_email(request_data: GoogleLoginRequest):
    """Google 이메일로 기존 사용자 찾아 로그인"""
    email = request_data.email
    if not email:
        raise HTTPException(status_code=400, detail="이메일이 필요합니다")

    if MOCK_MODE:
        user = None
        for u in MOCK_USERS.values():
            if u["email"] == email:
                user = u
                break
        if not user:
            raise HTTPException(status_code=404, detail="등록되지 않은 사용자입니다. 먼저 회원가입을 해주세요.")

        token_data = {
            "sub": str(user["id"]),
            "email": user["email"],
            "name": user["name"],
            "user_type": user["user_type"],
            "admin_level": user["admin_level"]
        }
        access_token = create_access_token(token_data)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_HOURS * 3600,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "user_type": user["user_type"],
                "admin_level": user["admin_level"],
                "language": user.get("language", "en")
            }
        }

    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, name, user_type, admin_level, language
            FROM kwv_users WHERE email = %s AND is_active = TRUE
        """, (email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="등록되지 않은 사용자입니다. 먼저 회원가입을 해주세요.")

        user_id, email, name, user_type, admin_level, language = user
        user_type = user_type or 'applicant'
        admin_level = admin_level or 0

        cursor.execute("UPDATE kwv_users SET last_login_at = NOW(), oauth_provider = 'google' WHERE id = %s", (user_id,))
        conn.commit()

        token_data = {
            "sub": str(user_id),
            "email": email,
            "name": name,
            "user_type": user_type,
            "admin_level": admin_level
        }
        access_token = create_access_token(token_data)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_HOURS * 3600,
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "user_type": user_type,
                "admin_level": admin_level,
                "language": language or "en"
            }
        }
    finally:
        conn.close()

# ==================== 시스템 설정 API ====================

def ensure_system_settings_table():
    """시스템 설정 테이블 확인 및 생성"""
    conn = get_kwv_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kwv_system_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                setting_type ENUM('string','number','boolean','json') DEFAULT 'string',
                description VARCHAR(500),
                updated_by INT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_key (setting_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        conn.commit()
    except:
        pass
    finally:
        conn.close()

@router.get("/settings")
async def get_system_settings():
    """시스템 설정 조회 (공개)"""
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT setting_key, setting_value, setting_type FROM kwv_system_settings")
        rows = cursor.fetchall()
        settings = {}
        for key, value, stype in rows:
            if stype == 'boolean':
                settings[key] = value == 'true'
            elif stype == 'number':
                try:
                    settings[key] = int(value) if value else 0
                except:
                    settings[key] = float(value) if value else 0
            elif stype == 'json':
                try:
                    settings[key] = json.loads(value) if value else {}
                except:
                    settings[key] = value
            else:
                settings[key] = value or ''
        return settings
    finally:
        conn.close()

@router.post("/settings")
async def update_system_settings(request: Request, user: dict = Depends(get_current_user)):
    """시스템 설정 수정 (super admin 전용)"""
    require_admin_level(user, 9)
    body = await request.json()

    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        updated = 0
        for key, value in body.items():
            if isinstance(value, bool):
                str_value = 'true' if value else 'false'
            elif isinstance(value, (dict, list)):
                str_value = json.dumps(value)
            else:
                str_value = str(value)
            cursor.execute("""
                INSERT INTO kwv_system_settings (setting_key, setting_value, updated_by)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value), updated_by = VALUES(updated_by)
            """, (key, str_value, user.get('sub')))
            updated += 1
        conn.commit()
        return {"message": f"{updated}개 설정이 저장되었습니다", "updated": updated}
    finally:
        conn.close()

# ==================== 지자체 API ====================

class LocalGovernmentCreate(BaseModel):
    name: str
    name_en: Optional[str] = None
    region: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website_url: Optional[str] = None
    representative_name: Optional[str] = None
    representative_phone: Optional[str] = None
    representative_email: Optional[str] = None
    allocated_quota: Optional[int] = 0
    quota_year: Optional[int] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    description_en: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@router.get("/local-governments")
async def list_local_governments(region: Optional[str] = None, active_only: bool = True):
    """지자체 목록 조회 (공개)"""
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        query = """
            SELECT id, name, name_en, region, address, phone, email, website_url,
                   representative_name, representative_phone, representative_email,
                   allocated_quota, used_quota, quota_year,
                   logo_url, description, description_en, latitude, longitude,
                   is_active, created_at
            FROM kwv_local_governments
        """
        conditions = []
        params = []
        if active_only:
            conditions.append("is_active = TRUE")
        if region:
            conditions.append("region = %s")
            params.append(region)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY region, name"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = []
        for row in rows:
            item = dict(zip(columns, row))
            # datetime/decimal 변환
            for k, v in item.items():
                if isinstance(v, datetime):
                    item[k] = v.isoformat()
                elif hasattr(v, '__float__'):
                    item[k] = float(v)
            result.append(item)
        return result
    finally:
        conn.close()

@router.get("/local-governments/{lg_id}")
async def get_local_government(lg_id: int):
    """지자체 상세 조회"""
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, name_en, region, address, phone, email, website_url,
                   representative_name, representative_phone, representative_email,
                   allocated_quota, used_quota, quota_year,
                   logo_url, description, description_en, latitude, longitude,
                   is_active, created_at, updated_at
            FROM kwv_local_governments WHERE id = %s
        """, (lg_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="지자체를 찾을 수 없습니다")
        columns = [desc[0] for desc in cursor.description]
        item = dict(zip(columns, row))
        for k, v in item.items():
            if isinstance(v, datetime):
                item[k] = v.isoformat()
            elif hasattr(v, '__float__'):
                item[k] = float(v)
        # 배정된 근로자 수 조회
        cursor.execute("SELECT COUNT(*) FROM kwv_users WHERE local_government_id = %s AND is_active = TRUE", (lg_id,))
        item['worker_count'] = cursor.fetchone()[0]
        return item
    finally:
        conn.close()

@router.post("/local-governments")
async def create_local_government(data: LocalGovernmentCreate, user: dict = Depends(get_current_user)):
    """지자체 등록 (admin)"""
    require_admin(user)
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        from datetime import date
        cursor.execute("""
            INSERT INTO kwv_local_governments
            (name, name_en, region, address, phone, email, website_url,
             representative_name, representative_phone, representative_email,
             allocated_quota, quota_year, logo_url, description, description_en,
             latitude, longitude)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (data.name, data.name_en, data.region, data.address, data.phone,
              data.email, data.website_url, data.representative_name,
              data.representative_phone, data.representative_email,
              data.allocated_quota, data.quota_year or date.today().year,
              data.logo_url, data.description, data.description_en,
              data.latitude, data.longitude))
        conn.commit()
        return {"id": cursor.lastrowid, "message": f"지자체 '{data.name}' 등록 완료"}
    finally:
        conn.close()

@router.put("/local-governments/{lg_id}")
async def update_local_government(lg_id: int, request: Request, user: dict = Depends(get_current_user)):
    """지자체 수정"""
    require_admin(user)
    body = await request.json()
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        allowed_fields = [
            'name', 'name_en', 'region', 'address', 'phone', 'email', 'website_url',
            'representative_name', 'representative_phone', 'representative_email',
            'allocated_quota', 'used_quota', 'quota_year', 'logo_url',
            'description', 'description_en', 'latitude', 'longitude', 'is_active'
        ]
        updates = []
        params = []
        for field in allowed_fields:
            if field in body:
                updates.append(f"{field} = %s")
                params.append(body[field])
        if not updates:
            raise HTTPException(status_code=400, detail="수정할 항목이 없습니다")
        params.append(lg_id)
        cursor.execute(f"UPDATE kwv_local_governments SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="지자체를 찾을 수 없습니다")
        return {"message": "지자체 정보가 수정되었습니다"}
    finally:
        conn.close()

@router.delete("/local-governments/{lg_id}")
async def delete_local_government(lg_id: int, user: dict = Depends(get_current_user)):
    """지자체 삭제 (super admin)"""
    require_admin_level(user, 9)
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE kwv_local_governments SET is_active = FALSE WHERE id = %s", (lg_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="지자체를 찾을 수 없습니다")
        return {"message": "지자체가 비활성화되었습니다"}
    finally:
        conn.close()

@router.put("/local-governments/{lg_id}/quota")
async def update_quota(lg_id: int, request: Request, user: dict = Depends(get_current_user)):
    """지자체 TO 배정 관리 (super admin)"""
    require_admin_level(user, 9)
    body = await request.json()
    conn = get_kwv_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database connection failed")
    try:
        cursor = conn.cursor()
        allocated = body.get('allocated_quota')
        year = body.get('quota_year')
        if allocated is not None:
            cursor.execute("""
                UPDATE kwv_local_governments
                SET allocated_quota = %s, quota_year = COALESCE(%s, quota_year)
                WHERE id = %s
            """, (allocated, year, lg_id))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="지자체를 찾을 수 없습니다")
        return {"message": "TO 배정이 업데이트되었습니다"}
    finally:
        conn.close()

# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "ok",
        "service": "KoreaWorkingVisa API",
        "version": "1.1.20260213",
        "mock_mode": MOCK_MODE,
        "jwt_available": JWT_AVAILABLE,
        "bcrypt_available": BCRYPT_AVAILABLE,
        "google_oauth_configured": bool(GOOGLE_CLIENT_ID)
    }
