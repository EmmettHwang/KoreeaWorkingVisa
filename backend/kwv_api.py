# -*- coding: utf-8 -*-
"""
KoreaWorkingVisa API 모듈
- 관리자/비자신청자 인증 및 관리
- Google OAuth 연동
- JWT 토큰 기반 인증
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import json
import hashlib
import secrets

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

# ==================== Router ====================
router = APIRouter(prefix="/api/kwv", tags=["KoreaWorkingVisa"])

# ==================== Pydantic Models ====================
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    phone: Optional[str] = None
    language: Optional[str] = "en"
    user_type: Optional[str] = "applicant"  # applicant 또는 admin
    organization: Optional[str] = None  # 관리자 신청 시 소속 기관

class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 토큰 생성"""
    if not JWT_AVAILABLE:
        token_data = json.dumps({**data, "exp": (datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)).isoformat()})
        return hashlib.sha256(token_data.encode()).hexdigest()

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    """JWT 토큰 디코딩"""
    if not JWT_AVAILABLE:
        return None
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

def require_admin_level(user: dict, max_level: int) -> dict:
    """특정 등급 이상의 관리자 권한 확인"""
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")
    if user.get("admin_level", 999) > max_level:
        raise HTTPException(status_code=403, detail=f"등급 {max_level} 이상의 관리자 권한이 필요합니다")
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
    load_dotenv(dotenv_path=env_path)

    try:
        return pymysql.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            passwd=os.getenv('DB_PASSWORD', ''),
            db=os.getenv('DB_NAME', 'minilms'),
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
    - applicant (일반 사용자): 비자 신청자
    - admin (관리자): 정부 기관 담당자
    """
    global MOCK_USER_ID_COUNTER

    if user_data.user_type not in ["applicant", "admin"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 사용자 유형입니다")

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
            "password_hash": hash_password(user_data.password),
            "name": user_data.name,
            "user_type": user_data.user_type,
            "admin_level": 2 if is_admin else None,
            "language": user_data.language,
            "is_active": True,
            "is_approved": True,
            "organization": user_data.organization,
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

        import secrets
        password_salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((user_data.password + password_salt).encode()).hexdigest()

        # name을 first_name/last_name으로 분리
        name_parts = (user_data.name or '').strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        user_type = user_data.user_type or 'applicant'

        cursor.execute("""
            INSERT INTO kwv_users (email, password_hash, password_salt, first_name, last_name, birth_date, nationality, phone, status, user_type, admin_level, language, organization)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_data.email,
            password_hash,
            password_salt,
            first_name,
            last_name,
            '2000-01-01',
            'XX',
            user_data.phone or '',
            'active',
            user_type,
            0,
            user_data.language or 'en',
            user_data.organization
        ))

        user_id = cursor.lastrowid
        conn.commit()

        token_data = {
            "sub": str(user_id),
            "email": user_data.email,
            "name": user_data.name,
            "user_type": user_type,
            "admin_level": 3 if user_type == 'admin' else 0
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
                "user_type": user_type,
                "admin_level": 3 if user_type == 'admin' else 0,
                "language": user_data.language
            }
        }
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
            SELECT id, email, password_hash, password_salt, first_name, last_name, status, user_type, admin_level, language
            FROM kwv_users WHERE email = %s
        """, (credentials.email,))

        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

        user_id, email, password_hash, password_salt, first_name, last_name, status, user_type, admin_level, language = user
        name = (first_name + ' ' + last_name).strip() if first_name else email
        user_type = user_type or 'applicant'
        admin_level = admin_level or 0
        language = language or 'ko'

        if status != 'active':
            raise HTTPException(status_code=403, detail="비활성화된 계정입니다")

        check_hash = hashlib.sha256((credentials.password + password_salt).encode()).hexdigest()
        if check_hash != password_hash:
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다")

        cursor.execute("UPDATE kwv_users SET last_login = NOW() WHERE id = %s", (user_id,))
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
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    """신청자 목록 조회 (관리자용)"""
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

        cursor.execute(f"""
            SELECT COUNT(*) FROM kwv_users u
            LEFT JOIN kwv_visa_applicants a ON u.id = a.user_id
            {where_clause}
        """, params)
        total = cursor.fetchone()[0]

        offset = (page - 1) * limit
        cursor.execute(f"""
            SELECT u.id, u.email, u.name, u.phone, u.created_at,
                   a.visa_type, a.nationality, a.application_status
            FROM kwv_users u
            LEFT JOIN kwv_visa_applicants a ON u.id = a.user_id
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
                "status": row[7] or "pending"
            })

        return {
            "applicants": applicants,
            "total": total,
            "page": page,
            "limit": limit
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

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="신청자를 찾을 수 없습니다")

        conn.commit()
        return {"message": "상태가 변경되었습니다", "status": status_update.status}
    finally:
        conn.close()

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

# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    return {
        "status": "ok",
        "service": "KoreaWorkingVisa API",
        "version": "1.0.0",
        "mock_mode": MOCK_MODE,
        "jwt_available": JWT_AVAILABLE,
        "bcrypt_available": BCRYPT_AVAILABLE,
        "google_oauth_configured": bool(GOOGLE_CLIENT_ID)
    }
