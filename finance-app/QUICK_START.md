# Quick Start: OAuth2 + File Upload Testing

## 1. Start FastAPI Server

```bash
cd finance-app
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

## 2. Open Swagger UI

```
http://localhost:8000/docs
```

## 3. Test Complete OAuth2 + Upload Flow

### Step 1: Login via Swagger

1. Click the **lock icon** (Authorize button, top-right corner)
2. Enter credentials:
   - **username:** `admin@example.com` or `admin`
   - **password:** `YourPassword123`
3. Click **Authorize** button
4. Verify **lock icon is now CLOSED** (means token stored)
5. Click **"Close"** to dismiss the modal

### Step 2: Test Preview Upload

1. Scroll down to **POST /api/v1/uploads/excel/preview**
2. Click **"Try it out"**
3. Click **"Select File"** and choose an Excel or CSV file
4. Click **"Execute"**

**Expected Response (200 OK):**
```json
{
  "total_rows": 100,
  "valid_rows": 95,
  "duplicate_rows": 0,
  "invalid_rows": 5,
  "detected_columns": ["date", "amount", "description", "category"],
  "validation_errors": [
    {
      "row_number": 5,
      "message": "Invalid date format"
    }
  ]
}
```

### Step 3: Test Actual Upload

1. Scroll down to **POST /api/v1/uploads/excel**
2. Click **"Try it out"**
3. Click **"Select File"** and choose the SAME Excel file
4. Click **"Execute"**

**Expected Response (201 Created):**
```json
{
  "success": true,
  "message": "Excel file imported successfully",
  "total_rows": 100,
  "inserted_rows": 95,
  "duplicate_rows": 0,
  "invalid_rows": 5,
  "created_categories": 3,
  "file_name": "transactions.xlsx"
}
```

## 4. Verify in Database

```bash
psql -U postgres -d finance_app -c "SELECT COUNT(*) FROM transactions;"
```

Should show the number of newly inserted transactions.

## 5. Check Logs

```bash
# In the terminal running uvicorn, you should see:
INFO app.routes.uploads: Excel upload started: filename=transactions.xlsx, user_id=1
INFO app.routes.uploads: Excel upload processing: filename=transactions.xlsx, size=45000 bytes, user_id=1
INFO app.routes.uploads: Excel upload completed: total_rows=100, inserted_rows=95...
```

---

## Troubleshooting

### Problem: 422 Unprocessable Entity on Upload

**Checklist:**
- [ ] Is lock icon CLOSED? (If open, click Authorize first)
- [ ] Is a file selected? (Click "Select File" button)
- [ ] Is file < 25 MB?
- [ ] Is file .xlsx or .csv?

**Debug:**
```bash
# Check server logs for specific error
tail -f logs/app.log | grep 422
```

### Problem: 401 Unauthorized

**Solution:** Click Authorize button again to refresh token

### Problem: 413 Payload Too Large

**Solution:** Select a smaller file (< 25 MB)

### Problem: 415 Unsupported Media Type

**Solution:** Use .xlsx or .csv files only

---

## File Format Examples

### Excel (.xlsx)
**Supported columns:**
- Date: "date", "transaction_date", "posted date", etc.
- Amount: "amount", "value", "total", etc.
- Type: "debit", "credit" OR "amount" column
- Description: "description", "memo", "note", etc.
- Category: "category", "category name", "merchant", etc.

**Example:**
```
date       | amount | description          | category
2024-01-01 | 1500   | Salary deposit       | Income
2024-01-02 | -50    | Coffee shop purchase | Dining
```

### CSV (.csv)
**Same column names as Excel**
**Supported encodings:** UTF-8, Latin-1

**Example:**
```
date,amount,description,category
2024-01-01,1500,Salary deposit,Income
2024-01-02,-50,Coffee shop purchase,Dining
```

---

## Architecture Verification

After testing, verify the OAuth2 implementation:

1. **Token endpoint works:**
   - Request: `POST /api/v1/auth/login` with form data
   - Response: Bearer token in JSON

2. **Bearer token attaches to multipart:**
   - Swagger injects `Authorization: Bearer <token>` header
   - Upload endpoint receives valid JWT

3. **Token validation works:**
   - `OAuth2PasswordBearer` extracts token from header
   - `decode_access_token()` verifies JWT signature
   - `get_current_user()` loads authenticated user from DB

4. **File upload works:**
   - File parameters processed in correct order
   - File validation passes (extension, size, encoding)
   - File data saved to database

---

## Performance Tips

- **Large files:** Use Preview endpoint first to validate before full import
- **Multiple uploads:** Stagger requests (1-2 seconds apart)
- **Batch operations:** Database commits after all transactions inserted

---

## Next: Mobile App Integration

For React Native or web clients:

```javascript
// 1. Login
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: 'username=admin@example.com&password=YourPassword123'
});
const { access_token, token_type, expires_in } = await response.json();

// 2. Upload with token
const formData = new FormData();
formData.append('file', selectedFile);

const uploadResponse = await fetch('http://localhost:8000/api/v1/uploads/excel', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
  },
  body: formData
});
const result = await uploadResponse.json();
console.log(`Inserted ${result.inserted_rows} transactions`);
```

---

## Success Criteria

✅ Login via Swagger Authorize works  
✅ Bearer token displays in response  
✅ Preview upload shows file validation  
✅ Actual upload creates transactions in DB  
✅ Upload logs appear in server console  
✅ No 422 errors on upload  
✅ File size/type validation works  

If all above pass, OAuth2 + authenticated file upload is production-ready!

---

## Documentation

- **Architecture & Design:** `OAUTH2_UPLOAD_GUIDE.md`
- **Refactoring Details:** `REFACTORING_SUMMARY.md`
- **API Docs (Live):** http://localhost:8000/docs
- **ReDoc (Alternative):** http://localhost:8000/redoc

Enjoy! 🚀
