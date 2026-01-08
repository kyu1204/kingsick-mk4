# Phase 2 인증 시스템 설계

> **작성일**: 2026-01-09
> **상태**: 승인됨
> **담당**: Phase 2 - 모니터링

---

## 개요

KingSick의 사용자 인증 및 API 키 관리 시스템 설계 문서.

### 요구사항 요약

- **사용자 범위**: 소규모 (초대 기반)
- **인증 방식**: 이메일/비밀번호 (이메일 인증 생략)
- **초대 시스템**: 관리자만 초대 링크 생성 가능
- **관리자 지정**: DB에서 is_admin 플래그 직접 설정
- **API 키 관리**: 사용자별 KIS API 키 등록 (AES-256 암호화)

---

## 1. 데이터 모델

### User 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| email | string | unique, 로그인 ID |
| password_hash | string | bcrypt 해시 |
| is_admin | boolean | 관리자 여부 (default: false) |
| is_active | boolean | 활성 상태 (default: true) |
| created_at | datetime | 생성일 |
| updated_at | datetime | 수정일 |

### Invitation 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| code | string | unique, 랜덤 토큰 |
| created_by | UUID | FK → User (관리자) |
| used_by | UUID | FK → User (nullable) |
| expires_at | datetime | 만료일 |
| used_at | datetime | 사용일 (nullable) |
| created_at | datetime | 생성일 |

### UserApiKey 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| user_id | UUID | FK → User |
| kis_app_key_encrypted | string | AES-256 암호화 |
| kis_app_secret_encrypted | string | AES-256 암호화 |
| kis_account_no_encrypted | string | AES-256 암호화 |
| is_paper_trading | boolean | 모의투자 여부 |
| created_at | datetime | 생성일 |
| updated_at | datetime | 수정일 |

### 암호화

- **알고리즘**: AES-256-GCM
- **키 관리**: `ENCRYPTION_KEY` 환경변수 (32 bytes)
- **저장 형식**: `nonce:ciphertext:tag` (base64 인코딩)

---

## 2. API 엔드포인트

### 인증 (Public)

```
POST /api/v1/auth/register
  Body: { email, password, invitation_code }
  Response: { message: "User created successfully" }

POST /api/v1/auth/login
  Body: { email, password }
  Response: { access_token, refresh_token, token_type, user }

POST /api/v1/auth/refresh
  Body: { refresh_token }
  Response: { access_token, refresh_token, token_type }

POST /api/v1/auth/logout
  Header: Authorization: Bearer <token>
  Response: { message: "Logged out successfully" }
```

### 사용자 (인증 필요)

```
GET  /api/v1/users/me
  Response: { id, email, is_admin, is_active, created_at }

PUT  /api/v1/users/me
  Body: { email? }
  Response: { id, email, ... }

PUT  /api/v1/users/me/password
  Body: { current_password, new_password }
  Response: { message: "Password updated" }
```

### 초대 관리 (관리자 전용)

```
POST /api/v1/invitations
  Body: { expires_in_days?: number }  # default: 7
  Response: { id, code, invitation_url, expires_at }

GET  /api/v1/invitations
  Response: { invitations: [...] }

DELETE /api/v1/invitations/:id
  Response: { message: "Invitation deleted" }
```

### API 키 관리 (인증 필요)

```
GET  /api/v1/api-keys
  Response: {
    has_api_key: boolean,
    app_key_masked: "****xxxx",  # 마지막 4자리만 표시
    account_no_masked: "****1234",
    is_paper_trading: boolean
  }

POST /api/v1/api-keys
  Body: { app_key, app_secret, account_no, is_paper_trading }
  Response: { message: "API key saved" }

DELETE /api/v1/api-keys
  Response: { message: "API key deleted" }

POST /api/v1/api-keys/verify
  Response: { valid: boolean, message: string }
```

### JWT 설정

- **Access Token**: 30분
- **Refresh Token**: 7일
- **알고리즘**: HS256
- **시크릿**: `JWT_SECRET` 환경변수

---

## 3. Frontend 화면 및 플로우

### 페이지 구조

```
/login                    # 로그인 페이지
/register?code=<초대코드>  # 회원가입 (초대링크로만 접근)
/settings                 # 설정 페이지
  ├── API Keys 탭         # KIS API 키 등록/수정
  └── Account 탭          # 비밀번호 변경
/admin/invitations        # 초대 관리 (관리자 전용)
```

### 인증 플로우

```
1. 관리자가 /admin/invitations에서 초대 링크 생성
   → https://kingsick.app/register?code=abc123

2. 초대받은 사용자가 링크 클릭 → 회원가입 폼
   → 이메일/비밀번호 입력 → 가입 완료 → 로그인 페이지

3. 로그인 → JWT 발급 → localStorage 저장
   → 보호된 페이지 접근 가능

4. 첫 로그인 시 /settings로 리다이렉트
   → KIS API 키 등록 유도
```

### 보호된 라우트

| 상태 | 접근 가능 |
|------|----------|
| 미인증 | /login, /register만 |
| 인증됨 | 모든 페이지, API 키 없으면 거래 기능 제한 |
| 관리자 | /admin/* 추가 접근 |

### 상태 관리

- **AuthContext**: 로그인 상태, 사용자 정보
- **저장소**: localStorage (JWT 토큰)
- **토큰 갱신**: Access Token 만료 5분 전 자동 갱신

---

## 4. 구현 Task

### Backend Tasks

| # | Task | 설명 | 우선순위 |
|---|------|------|----------|
| 2-1 | 모델 생성 | User, Invitation, UserApiKey + 마이그레이션 | P1 |
| 2-2 | 암호화 유틸리티 | AES-256-GCM encrypt/decrypt | P1 |
| 2-3 | 인증 서비스 | JWT 발급/검증, 비밀번호 해싱 | P1 |
| 2-4 | Auth API 라우터 | register, login, refresh, logout | P1 |
| 2-5 | 기타 라우터 | users, invitations, api-keys | P1 |

### Frontend Tasks

| # | Task | 설명 | 우선순위 |
|---|------|------|----------|
| 2-6 | AuthContext | 로그인 상태 관리, useAuth 훅 | P1 |
| 2-7 | 로그인/회원가입 | 페이지 API 연동 | P1 |
| 2-8 | ProtectedRoute | 미인증 시 리다이렉트 | P1 |
| 2-9 | Settings - API 키 | KIS API 키 관리 UI | P1 |
| 2-10 | Admin 초대 관리 | 초대 링크 생성/관리 페이지 | P1 |

---

## 5. 테스트 전략

### 테스트 범위

| 유형 | 대상 | Coverage 목표 |
|------|------|---------------|
| Unit | 암호화, JWT, 비밀번호 해싱 | 100% |
| Integration | 인증 플로우 전체 | 95% |
| E2E | 브라우저 테스트 | 주요 시나리오 |

### 주요 테스트 케이스

**Unit Tests**
- 암호화/복호화 정상 동작
- 잘못된 키로 복호화 실패
- JWT 생성/검증
- 비밀번호 해싱/검증

**Integration Tests**
- 회원가입 → 로그인 → 토큰 갱신 플로우
- 잘못된 초대 코드로 가입 실패
- 만료된 토큰으로 접근 실패
- 관리자 아닌 사용자의 초대 생성 실패

**E2E Tests**
- 초대 링크 → 가입 → 로그인 → API 키 등록

---

## 6. 환경 변수

```bash
# 기존
DATABASE_URL=postgresql://...

# 추가 필요
JWT_SECRET=<random-32-bytes>
ENCRYPTION_KEY=<random-32-bytes>
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-01-09 | 초기 설계 문서 작성 |
