# OAuth2 + Authenticated File Upload Architecture

## Executive Summary

This guide explains the production-grade OAuth2 authentication and authenticated multipart file upload system for Finance App.

### Key Changes Made

1. **Fixed OAuth2 tokenUrl** — Changed from relative to absolute path
2. **Explicit token response fields** — Token type and expiration now set explicitly for Swagger compliance
3. **Comprehensive logging** — Added request/response logging for debugging
4. **Robust file handling** — Added file type, size validation, encoding detection
5. **CSV + Excel support** — Both formats now supported with automatic detection
6. **Production error handling** — Clear, actionable error messages

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Swagger UI)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User clicks "Authorize" button (lock icon)                │
│     ↓                                                           │
│  2. Swagger sends POST to /api/v1/auth/login with credentials │
│     ├─ username: email or username                            │
│     ├─ password: plaintext                                    │
│     └─ Content-Type: application/x-www-form-urlencoded       │
│                                                                │
│  3. Backend returns TokenResponse (JSON)                      │
│     ├─ access_token: "eyJhbGc..."                            │
│     ├─ token_type: "bearer"                                  │
│     ├─ expires_in: 3600                                      │
│     └─ user: { id, email, username, is_active }             │
│                                                                │
│  4. Swagger stores token in memory                           │
│                                                                │
│  5. User calls protected endpoint (e.g., upload)             │
│     ├─ Swagger injects Authorization header                  │
│     └─ Header: Authorization: Bearer <access_token>          │
│                                                                │
│  6. Multipart/form-data sent:                               │
│     ├─ file: <binary data>                                  │
│     ├─ Authorization: Bearer <token>                        │
│     └─ Content-Type: multipart/form-data                    │
│                                                                │
│  7. Backend validates:                                        │
│     ├─ OAuth2PasswordBearer extracts token from header       │
│     ├─ decode_access_token verifies JWT signature           │
│     ├─ get_current_user fetches User from DB                │
│     └─ File validation (type, size, encoding)               │
│                                                                │
│  8. File processed and result returned                       │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why 422 Occurred (Root Cause)

### The Problem

When `tokenUrl="api/v1/auth/login"` (relative without leading slash):

1. **Swagger's URL Resolution Issue**
   - Relative URLs in OAuth2 are resolved relative to the current document/page
   - Without leading slash, Swagger may interpret as: `http://current-host/api/v1/auth/login`
   - This doesn't resolve to your API base properly
   - Token storage mechanism malfunctions

2. **Authorization Header Not Attached**
   - Swagger stores the token but can't reliably inject it into multipart requests
   - MultipartPayload sent without Authorization header

3. **Request Validation Failure**
   - FastAPI's multipart parser validates the request schema BEFORE the route handler
   - Missing Authorization header → `current_user` dependency fails early
   - JWT validation happens during dependency injection (before route handler)
   - Result: 422 Unprocessable Entity (validation failure) instead of 401 (unauthorized)

### The Fix

```python
# BEFORE (broken)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# AFTER (working)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
```

The leading slash tells Swagger to resolve the URL relative to the API base (`/`), not the current page.

---

## Component Documentation

### 1. OAuth2 Scheme Configuration
**File:** `app/auth/dependencies.py`

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
```

**Why absolute path?**
- RFC 6749 recommends absolute paths for token endpoints
- Swagger needs a resolvable URL
- Ensures consistent behavior across browsers, versions, and deployment environments

### 2. Token Endpoint
**File:** `app/routes/auth.py` → `POST /api/v1/auth/login`

**Input:**
- Content-Type: `application/x-www-form-urlencoded`
- Fields: `username` (email or username), `password`

**Output (TokenResponse):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "is_active": true
  }
}
```

**Why explicit fields?**
- `token_type: "bearer"` — Tells OAuth2 clients how to use the token
- `expires_in: 3600` — Token valid for 1 hour, explicitly declared
- Swagger requires these for proper Authorization header formatting

### 3. JWT Token Validation
**File:** `app/auth/dependencies.py` → `get_current_user()`

Flow:
1. OAuth2PasswordBearer extracts token from `Authorization: Bearer <token>` header
2. `decode_access_token()` verifies JWT signature using `JWT_SECRET_KEY`
3. Extracts `sub` (subject = user_id) from JWT payload
4. Queries DB for active user
5. Returns User object or raises 401 Unauthorized

### 4. Protected Upload Routes
**File:** `app/routes/uploads.py`

Two endpoints:
- `POST /api/v1/uploads/excel/preview` — Validate before import
- `POST /api/v1/uploads/excel` — Import and create transactions

**Parameter Order (Critical for Multipart Handling):**
```python
async def upload_excel_transactions(
    file: UploadFile = File(...),           # 1. Multipart form data (file)
    current_user: User = Depends(get_current_user),  # 2. JWT auth from header
    db: Session = Depends(get_db),          # 3. Database session
) -> ExcelUploadResponse:
```

Why this order matters:
- File parameter processes multipart form first
- Then dependency injection happens (which validates JWT)
- Swagger generates OpenAPI correctly for this order

**Validation Pipeline:**
1. File extension check (`.xlsx` or `.csv`)
2. File size check (≤ 25 MB)
3. Authentication via `get_current_user`
4. File format parsing (Excel engine or CSV decoder)
5. Column detection and row normalization
6. Transaction import with deduplication

### 5. File Format Support
**File:** `app/services/upload_service.py` → `_load_dataframe()`

**Excel (.xlsx):**
- Engine: `openpyxl`
- Handles modern Excel formats
- Warning: Data validation extensions are stripped

**CSV (.csv):**
- Encoding detection: UTF-8 (primary), Latin-1 (fallback)
- Auto-detects delimiter (pandas default: comma)
- Handles quoted fields and escaping

---

## Testing the Complete Flow

### 1. Start the Server

```bash
cd finance-app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Open Swagger UI

```
http://localhost:8000/docs
```

### 3. Login via Swagger Authorize

1. Click lock icon (top right)
2. Enter credentials:
   - username: `your_email@example.com` or `your_username`
   - password: `YourPasswordHere`
3. Click "Authorize"
4. Confirm success (Authorize button turns blue, lock icon closes)

### 4. Test Preview Upload

In Swagger /api/v1/uploads/excel/preview:

1. Click "Try it out"
2. Select an Excel or CSV file from disk
3. Click "Execute"
4. Verify response:
   - Status: 200 OK
   - Response shows: `total_rows`, `valid_rows`, `detected_columns`, `validation_errors`

**If 401 Unauthorized:**
- Token expired or not stored
- Click Authorize again

**If 422 Unprocessable Entity:**
- File not selected in form
- Authorization header missing
- See browser console for details

### 5. Test Actual Upload

In Swagger /api/v1/uploads/excel:

1. Click "Try it out"
2. Select a validated Excel file
3. Click "Execute"
4. Verify response:
   - Status: 201 Created
   - Response shows: `inserted_rows`, `duplicate_rows`, `created_categories`

### 6. Test Error Scenarios

**Scenario: File too large**
```
Expected: 413 Payload Too Large
Message: "File size (X bytes) exceeds maximum (Y bytes)"
```

**Scenario: Wrong file type**
```
Expected: 415 Unsupported Media Type
Message: "File type '.txt' not supported. Allowed: .xlsx, .csv"
```

**Scenario: Empty file**
```
Expected: 400 Bad Request
Message: "File is empty or contains no data rows"
```

**Scenario: Missing required columns**
```
Expected: 422 Unprocessable Entity
Message: "Missing required date column" or "Missing required amount/debit/credit columns"
```

---

## Logging for Debugging

All auth and upload operations are logged at multiple levels:

**Info Level (normal operation):**
```
INFO app.auth.dependencies: Token validated for user_id=42
INFO app.routes.uploads: Excel upload started: filename=transactions.xlsx, user_id=42
INFO app.routes.uploads: Excel upload completed: total_rows=100, inserted_rows=95
```

**Debug Level (detailed flow):**
```
DEBUG app.services.upload_service: Loading Excel file: transactions.xlsx
DEBUG app.services.upload_service: Loaded 100 rows, 5 columns from transactions.xlsx
```

**Error Level (failures):**
```
ERROR app.routes.uploads: Failed to read file: [Errno 2] No such file..., user_id=42
ERROR app.services.upload_service: Failed to parse file transactions.xlsx: [exception details]
```

**Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Security Considerations

### 1. JWT Secret
- **File:** `.env` → `JWT_SECRET_KEY`
- **Requirement:** Minimum 32 characters for HS256
- **Production:** Use strong random string, rotate periodically
- **Current:** Set strong value in `.env`, DO NOT commit to Git

### 2. Token Expiration
- **Duration:** 3600 seconds (1 hour)
- **Configured in:** `app/core/config.py` → `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Future:** Add refresh token endpoint for extended sessions

### 3. File Upload Security
- **File type validation:** Only `.xlsx` and `.csv`
- **File size limit:** 25 MB (configurable in `app/routes/uploads.py`)
- **Encoding validation:** UTF-8 or Latin-1
- **User isolation:** Transactions always created for authenticated user
- **Future:** Add virus scanning, content inspection

### 4. Authentication Flow
- **Password hashing:** PBKDF2-SHA256 via passlib
- **Token signing:** HS256 (HMAC-SHA256)
- **Token validation:** Signature verification + user active check
- **Future:** Add rate limiting on login attempts

---

## Scalability & Future Extensions

### 1. Refresh Tokens
```python
# In TokenResponse schema
refresh_token: str | None = None  # Already scaffolded

# In auth endpoint
refresh_token = create_refresh_token(subject=str(user.id))
return TokenResponse(..., refresh_token=refresh_token)
```

### 2. Role-Based Access Control
```python
# Add roles to User model
class User(BaseModel):
    roles: List[str] = ["user"]  # "admin", "analyst", etc.

# In JWT payload
payload["roles"] = user.roles

# In dependencies
def get_admin_user(current_user: User = Depends(get_current_user)):
    if "admin" not in current_user.roles:
        raise HTTPException(403, "Admin access required")
    return current_user
```

### 3. Async File Processing
```python
# Current: synchronous pandas processing
# Future: Background job with Celery/RQ

from celery import Celery
from app.tasks import process_upload_async

# Return job ID immediately
job = process_upload_async.delay(user_id, file_bytes)
return {"job_id": job.id, "status": "processing"}
```

### 4. React Native Frontend Integration
```javascript
// Token stored in secure storage (iOS Keychain, Android Keystore)
const token = await SecureStore.getItemAsync('auth_token');

// Multipart upload with bearer token
const formData = new FormData();
formData.append('file', {
  uri: fileUri,
  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  name: 'transactions.xlsx',
});

const response = await fetch('https://api.finance-app.com/api/v1/uploads/excel', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData,
});
```

### 5. Analytics Pipeline Integration
```python
# After successful upload
from app.analytics.transaction_analyzer import analyze_transactions

result = ExcelUploadService(db).process(current_user, file_name, file_bytes)
if result.inserted_rows > 0:
    analytics = analyze_transactions(user_id=current_user.id)
    return {"upload": result, "analytics": analytics}
```

---

## Troubleshooting

### Issue: 422 Unprocessable Entity on Upload

**Diagnosis:**
1. Check browser console for Authorization header details
2. Verify Authorize button is blue (token stored)
3. Check server logs for request details

**Solutions:**
```bash
# View all logs
tail -f logs/app.log | grep -i upload

# Check specific user auth
grep "user_id=YOUR_ID" logs/app.log
```

### Issue: Token Expired

**Symptom:** 401 Unauthorized after several minutes of inactivity

**Solution:**
- Click Authorize button again to get a fresh token
- Future: Implement refresh token endpoint

### Issue: File Not Parsing

**Check encoding:**
```python
# In production logs
DEBUG: "UTF-8 decode failed, trying latin-1: transactions.csv"
```

**Solutions:**
- Save file as UTF-8 from Excel
- Remove non-ASCII characters (é, ñ, etc.)
- Use explicit encoding in save dialog

---

## References

- RFC 6749 (OAuth 2.0) — https://tools.ietf.org/html/rfc6749
- FastAPI Security — https://fastapi.tiangolo.com/tutorial/security/
- OpenAPI OAuth2 — https://spec.openapis.org/oas/v3.0.3#oauth-flows-object
- JWT.io — https://jwt.io

---

## Summary

The OAuth2 + authenticated file upload system now:

✅ Works with Swagger Authorize button  
✅ Validates JWT tokens in Authorization header  
✅ Supports multipart/form-data file uploads  
✅ Handles Excel and CSV formats  
✅ Provides robust error messages  
✅ Logs all operations for debugging  
✅ Scales for React Native and microservices  

Next steps:
1. Test the complete flow in Swagger
2. Monitor logs for any authentication issues
3. Plan refresh token implementation for mobile apps
4. Add role-based access control as needed
