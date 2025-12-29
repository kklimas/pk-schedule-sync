# API Reference 📡

The PK Schedule Sync backend provides several endpoints to manage synchronization jobs and retrieve schedule data.

## 🔑 Base URL
`http://localhost:8000/api/v1`

## 🛣️ Endpoints

### 🛠️ Jobs
- `POST /jobs/`: Trigger a new synchronization job manually.
- `GET /jobs/`: Retrieve a paginated history of all sync jobs.

### 📅 Lectures
- `GET /lectures/`: Fetch upcoming lectures.
  - **Parameters**: `page`, `page_size`, `sort_by`, etc.
  - Returns enriched data including subject info, teacher, and room details.

## 📖 Swagger Documentation
Interactive API documentation is available at the root URL:
- [Swagger UI](http://localhost:8000/docs)
- [ReDoc](http://localhost:8000/redoc)
