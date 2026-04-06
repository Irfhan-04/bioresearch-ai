# 📚 Biotech Lead Generator API Documentation

Complete API reference for the Biotech Lead Generator platform.

---

## 🔗 Interactive Documentation

The API includes interactive documentation powered by OpenAPI/Swagger:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

---

## 🚀 Quick Start

### Base URL

```
Development: http://localhost:8000
Production: https://api.yourdomain.com
```

### Authentication

All authenticated endpoints require a JWT token in the Authorization header:

```bash
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Or API Key in header:

```bash
X-API-Key: YOUR_API_KEY
```

---

## 📖 Table of Contents

1. [Authentication](#authentication)
2. [Users](#users)
3. [Leads](#leads)
4. [Search](#search)
5. [Export](#export)
6. [Enrichment](#enrichment)
7. [Pipelines](#pipelines)
8. [Webhooks](#webhooks)
9. [Error Handling](#error-handling)
10. [Rate Limiting](#rate-limiting)

---

## 🔐 Authentication

### Register New User

**POST** `/api/v1/auth/register`

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}
```

### Login

**POST** `/api/v1/auth/login`

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Refresh Token

**POST** `/api/v1/auth/refresh`

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### Get Current User

**GET** `/api/v1/auth/me`

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 👤 Users

### Get User Profile

**GET** `/api/v1/users/me`

```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update User Profile

**PUT** `/api/v1/users/me`

```bash
curl -X PUT http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Doe"
  }'
```

### Create API Key

**POST** `/api/v1/users/me/api-keys`

```bash
curl -X POST http://localhost:8000/api/v1/users/me/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key"
  }'
```

**Response:**
```json
{
  "id": "key-123",
  "name": "Production API Key",
  "key": "btlg_abc123...",
  "prefix": "btlg_abc1",
  "created_at": "2024-01-15T12:00:00Z"
}
```

⚠️ **Important**: API key is shown only once!

---

## 📊 Leads

### List Leads

**GET** `/api/v1/leads`

Query Parameters:
- `page` (int): Page number (default: 1)
- `size` (int): Items per page (default: 50, max: 100)
- `sort_by` (string): Field to sort by (default: created_at)
- `sort_order` (string): asc or desc (default: desc)
- `search` (string): Search in name/company
- `min_score` (int): Minimum propensity score
- `max_score` (int): Maximum propensity score
- `priority_tier` (string): HIGH, MEDIUM, LOW
- `has_email` (boolean): Filter by email presence

```bash
curl -X GET "http://localhost:8000/api/v1/leads?page=1&size=10&min_score=70" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Dr. Sarah Mitchell",
      "title": "Director of Toxicology",
      "company": "Moderna",
      "email": "sarah@modernatx.com",
      "propensity_score": 95,
      "priority_tier": "HIGH",
      "created_at": "2024-01-15T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 250,
    "pages": 25
  }
}
```

### Create Lead

**POST** `/api/v1/leads`

```bash
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Jane Smith",
    "title": "Research Scientist",
    "company": "BioTech Corp",
    "email": "jane@biotech.com",
    "location": "Cambridge, MA",
    "tags": ["high-priority", "researcher"]
  }'
```

### Get Lead Details

**GET** `/api/v1/leads/{lead_id}`

```bash
curl -X GET http://localhost:8000/api/v1/leads/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Update Lead

**PUT** `/api/v1/leads/{lead_id}`

```bash
curl -X PUT http://localhost:8000/api/v1/leads/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "CONTACTED",
    "notes": "Initial contact made"
  }'
```

### Delete Lead

**DELETE** `/api/v1/leads/{lead_id}`

```bash
curl -X DELETE http://localhost:8000/api/v1/leads/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Bulk Create Leads

**POST** `/api/v1/leads/bulk/create`

```bash
curl -X POST http://localhost:8000/api/v1/leads/bulk/create \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "leads": [
      {
        "name": "Lead 1",
        "title": "Scientist",
        "email": "lead1@example.com"
      },
      {
        "name": "Lead 2",
        "title": "Researcher",
        "email": "lead2@example.com"
      }
    ],
    "skip_duplicates": true
  }'
```

---

## 🔍 Search

### Execute Search

**POST** `/api/v1/search`

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "drug-induced liver injury 3D models",
    "search_type": "pubmed",
    "filters": {
      "years_back": 3
    },
    "save_search": true,
    "saved_name": "DILI Research 2024"
  }'
```

**Response:**
```json
{
  "search_id": "search-123",
  "query": "drug-induced liver injury 3D models",
  "results_count": 45,
  "leads_created": 38,
  "execution_time_ms": 1250,
  "message": "Search completed. Found 45 results, created 38 leads."
}
```

### Get Search History

**GET** `/api/v1/search/history`

```bash
curl -X GET "http://localhost:8000/api/v1/search/history?page=1&saved_only=false" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Re-run Search

**POST** `/api/v1/search/{search_id}/rerun`

```bash
curl -X POST http://localhost:8000/api/v1/search/search-123/rerun \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📦 Export

### Create Export

**POST** `/api/v1/export`

```bash
curl -X POST http://localhost:8000/api/v1/export \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "excel",
    "filters": {
      "min_score": 70
    },
    "columns": ["name", "email", "company", "propensity_score"]
  }'
```

### List Exports

**GET** `/api/v1/export`

```bash
curl -X GET http://localhost:8000/api/v1/export \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Download Export

**GET** `/api/v1/export/{export_id}/download`

```bash
curl -X GET http://localhost:8000/api/v1/export/export-123/download \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "download_url": "https://storage.example.com/exports/file.xlsx",
  "file_name": "leads_export_20240115.xlsx",
  "file_size_mb": 2.5,
  "expires_in": 604800
}
```

---

## ✨ Enrichment

### Enrich Single Lead

**POST** `/api/v1/enrich/leads/{lead_id}`

```bash
curl -X POST http://localhost:8000/api/v1/enrich/leads/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "services": ["email", "company"]
  }'
```

### Enrich Multiple Leads

**POST** `/api/v1/enrich/leads/batch`

```bash
curl -X POST http://localhost:8000/api/v1/enrich/leads/batch \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_ids": [
      "123e4567-e89b-12d3-a456-426614174000",
      "123e4567-e89b-12d3-a456-426614174001"
    ],
    "services": ["email", "linkedin"]
  }'
```

### Get Available Services

**GET** `/api/v1/enrich/services`

```bash
curl -X GET http://localhost:8000/api/v1/enrich/services \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## ⚙️ Pipelines

### Create Pipeline

**POST** `/api/v1/pipelines`

```bash
curl -X POST http://localhost:8000/api/v1/pipelines \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily PubMed Scan",
    "description": "Search PubMed for DILI research daily",
    "schedule": "daily",
    "config": {
      "search_queries": [
        {
          "source": "pubmed",
          "query": "drug-induced liver injury 3D models"
        }
      ],
      "filters": {
        "min_score": 70
      },
      "enrichment": {
        "find_email": true
      }
    }
  }'
```

### List Pipelines

**GET** `/api/v1/pipelines`

```bash
curl -X GET http://localhost:8000/api/v1/pipelines \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Run Pipeline Manually

**POST** `/api/v1/pipelines/{pipeline_id}/run`

```bash
curl -X POST http://localhost:8000/api/v1/pipelines/pipeline-123/run \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Activate Pipeline

**POST** `/api/v1/pipelines/{pipeline_id}/activate`

```bash
curl -X POST http://localhost:8000/api/v1/pipelines/pipeline-123/activate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Pause Pipeline

**POST** `/api/v1/pipelines/{pipeline_id}/pause`

```bash
curl -X POST http://localhost:8000/api/v1/pipelines/pipeline-123/pause \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 🔔 Webhooks

### Create Webhook

**POST** `/api/v1/webhooks`

```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pipeline Notifications",
    "url": "https://your-app.com/webhooks/pipeline",
    "events": ["pipeline.completed", "pipeline.failed"]
  }'
```

### List Webhooks

**GET** `/api/v1/webhooks`

```bash
curl -X GET http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Test Webhook

**POST** `/api/v1/webhooks/{webhook_id}/test`

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/webhook-123/test \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Stripe Webhook Events

Stripe events are handled by the dedicated webhook endpoint:

**POST** `/api/v1/webhooks/stripe`

For local development, use the Stripe CLI to forward events to that route.

---

## ⚠️ Error Handling

### Error Response Format

```json
{
  "success": false,
  "message": "Validation error",
  "error_code": "VALIDATION_ERROR",
  "details": {
    "email": ["Invalid email format"]
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

---

## ⏱️ Rate Limiting

Default rate limits per user:
- **60 requests per minute**
- **1000 requests per hour**

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642262400
```

When rate limited:
```json
{
  "success": false,
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED"
}
```

---

## 📌 Best Practices

### 1. Use Pagination

Always paginate large result sets:
```bash
GET /api/v1/leads?page=1&size=50
```

### 2. Filter Results

Use filters to reduce data transfer:
```bash
GET /api/v1/leads?min_score=70&has_email=true
```

### 3. Cache Responses

Cache GET requests on client side when appropriate.

### 4. Handle Errors Gracefully

Always check HTTP status codes and handle errors:
```javascript
if (response.status === 429) {
  // Wait and retry
} else if (response.status >= 500) {
  // Server error, retry with backoff
}
```

### 5. Use Webhooks for Async Operations

For long-running operations (exports, pipelines), use webhooks instead of polling.

---

## 🔧 SDK & Libraries

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@example.com", "password": "SecurePass123!"}
)
token = response.json()["access_token"]

# List leads
headers = {"Authorization": f"Bearer {token}"}
leads = requests.get(
    "http://localhost:8000/api/v1/leads",
    headers=headers
).json()
```

### JavaScript/TypeScript

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!'
  })
});
const { access_token } = await loginResponse.json();

// List leads
const leadsResponse = await fetch('http://localhost:8000/api/v1/leads', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
const leads = await leadsResponse.json();
```

---

## 📞 Support

- 📧 Email: support@yourdomain.com
- 💬 GitHub Issues: [github.com/yourrepo/issues](https://github.com/yourrepo/issues)
- 📚 Full Docs: [docs.yourdomain.com](https://docs.yourdomain.com)

---

**Last Updated**: January 2024
**API Version**: 2.0.0
