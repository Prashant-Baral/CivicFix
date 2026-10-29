# CivicFix: Civic Issue Reporting System

**CSE494 MongoDB Mini-Project** · Python · FastAPI · PyMongo · MongoDB · Swagger UI  
**Sustainable Development Goal:** SDG 11 (Sustainable Cities and Communities)

CivicFix is a civic complaint tracking system where citizens report local problems (potholes, garbage, broken streetlights, water supply issues, drainage blockages) and municipal officials update their status through `submitted → in_progress → resolved` while retaining an immutable, timestamped status history. Aggregation pipelines provide real-time analytical summaries and query profiling.

---

## Project Structure

```text
civicfix/
├── app/
│   ├── main.py          # FastAPI application entry & startup lifecycle
│   ├── config.py        # Application configuration & .env loader
│   ├── database.py      # MongoDB connection, $jsonSchema validator & 6 indexes
│   ├── models.py        # Pydantic validation models & enum definitions
│   ├── routes/
│   │   ├── issues.py    # REST endpoints for issues CRUD & lifecycle (/issues)
│   │   └── analytics.py # REST endpoints for aggregation reports (/analytics)
│   └── services/
│       ├── crud.py      # PyMongo CRUD queries & atomic status transitions
│       └── analytics.py # PyMongo aggregation pipelines & explain() profiling
├── .env.example         # Template for environment variables
├── .gitignore           # Git ignore rules (.venv, .env, private notes)
├── requirements.txt     # Core Python dependencies
└── README.md            # Project documentation & viva guide
```

---

## Quick Start (macOS)

### 1. Set Up Environment & Install Dependencies
```bash
cd ~/projects/mongodb_new/civicfix
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # edit only if MongoDB is not on localhost:27017
```

### 2. Start the Server
```bash
uvicorn app.main:app --reload
```
> **Automatic Setup:** On startup, the application connects to MongoDB, automatically creates the `issues` collection, registers the server-side `$jsonSchema` validator, and builds all 6 compound and text indexes.

Open **http://127.0.0.1:8000/docs** in your browser to access the interactive Swagger UI.

---

## Exploring with `mongosh`

The database comes pre-seeded with **58 realistic civic complaints** across 7 cities in Punjab (Phagwara, Jalandhar, Ludhiana, Amritsar, Patiala, Kapurthala, Hoshiarpur).

In your terminal, connect directly with:
```bash
mongosh "mongodb://localhost:27017/civicfix"
```

Useful commands inside `mongosh`:
```javascript
// Check document count (58 issues)
db.issues.countDocuments()

// Inspect one document
db.issues.findOne()

// View all 6 collection indexes
db.issues.getIndexes()

// Test server-side validation (fails with Document failed validation, error 121)
db.issues.insertOne({ title: "Incomplete doc" })

// Run aggregation to count issues by category
db.issues.aggregate([
  { $group: { _id: "$category", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])

// Count issues by city
db.issues.aggregate([
  { $group: { _id: "$location.city", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/issues` | Report a new civic issue |
| GET | `/issues` | List issues with filters (`category`, `status`, `priority`, `city`, `q` for full-text search, `sort`, `page`, `page_size`) |
| GET | `/issues/{id}` | Retrieve one issue by its MongoDB ID |
| PATCH | `/issues/{id}` | Update issue details (title, description, priority, category, location) |
| PATCH | `/issues/{id}/status` | Move status forward (`submitted` → `in_progress` → `resolved`) with note |
| DELETE | `/issues/{id}` | Delete an issue |
| GET | `/analytics/summary` | Complete dashboard breakdown by category, status, priority, and city (`$facet`) |
| GET | `/analytics/by-category` | Issue counts grouped by category |
| GET | `/analytics/by-status` | Issue counts grouped by status |
| GET | `/analytics/by-priority` | Issue counts grouped by priority |
| GET | `/analytics/resolution-time` | Average hours taken to resolve issues per category |
| GET | `/analytics/explain` | Query plan execution stats (`force_collection_scan=true` to compare `IXSCAN` vs `COLLSCAN`) |
| GET | `/health` | API and MongoDB connectivity check |

---

## Document Schema

```json
{
  "_id": "ObjectId",
  "title": "Large pothole near main road",
  "category": "pothole",
  "description": "A deep pothole is creating a hazard for vehicles.",
  "priority": "high",
  "status": "submitted",
  "location": {
    "area": "Model Town",
    "city": "Phagwara",
    "latitude": 31.224,
    "longitude": 75.77
  },
  "status_history": [
    {
      "status": "submitted",
      "changed_at": "ISODate",
      "note": "Report created"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

- **Allowed Categories:** `pothole`, `garbage`, `streetlight`, `water_supply`, `drainage`, `public_facility`, `other`
- **Allowed Priorities:** `low`, `medium`, `high`, `urgent`
- **Allowed Statuses:** `submitted`, `in_progress`, `resolved`

---

## Where Each MongoDB Concept Lives

| Concept | Location in Code | Details |
|---|---|---|
| **CRUD Operations** | `app/services/crud.py` | `insert_one`, `find`, `find_one_and_update`, `delete_one` |
| **BSON Types** | Throughout models and database | `ObjectId`, `Date`, `String`, `Double`, nested `Object`, `Array` |
| **Data Modelling** | `app/models.py`, `app/database.py` | Embedded `location` object and `status_history` array |
| **Validation** | `app/database.py` & `app/models.py` | `$jsonSchema` validator enforced by MongoDB server + Pydantic models in API |
| **Indexing** | `app/database.py` (`ensure_indexes`) | 5 compound indexes + 1 text index (`title`, `description`) |
| **Aggregation Pipelines** | `app/services/analytics.py` | `$facet`, `$group`, `$sort`, `$match`, `$project`, `$avg`, `$last` |
| **Query Optimisation** | `app/services/analytics.py` | `explain_query()` returning execution stages, keys, and docs examined |
| **Native Driver** | `app/database.py` | PyMongo client connecting directly without ORM/ODM abstraction |

---

## Demo Walkthrough for Viva

1. **Server Health:** Visit `http://127.0.0.1:8000/health` → shows `{"status":"ok","database":"connected"}`.
2. **Create Issue:** In Swagger UI (`/docs`), execute `POST /issues` → returns `201 Created` with generated ObjectId and initial `status_history`.
3. **Database Validation:**
   - In Swagger UI, try invalid category `alien` → returns `422 Unprocessable Entity`.
   - In `mongosh`, execute: `db.issues.insertOne({ title: "bad" })` → rejected directly by MongoDB `$jsonSchema` validator (`error 121`).
4. **Status Lifecycle:**
   - Update an issue's status to `in_progress` → success.
   - Try skipping directly from `submitted` to `resolved` → returns `409 Conflict`.
   - Update from `in_progress` to `resolved` → success; status history now records all 3 stages.
   - Try moving backward from `resolved` to `submitted` → rejected (`409 Conflict`).
5. **Analytics:**
   - Execute `GET /analytics/summary` → returns instant breakdown across all 58 issues.
   - Execute `GET /analytics/resolution-time` → shows average hours to fix issues by category.
6. **Query Plan Inspection (`explain`):**
   - Execute `GET /analytics/explain?city=Phagwara` → plan stages show `IXSCAN` using `city_created_at` index.
   - Execute `GET /analytics/explain?city=Phagwara&force_collection_scan=true` → plan stages show `COLLSCAN` scanning all 58 documents.

---

## Design Decisions

- **One Collection with Embedded History:** A civic complaint and its status history are always accessed together. Because the lifecycle is short (3 transitions maximum), embedding keeps all data in a single document and allows atomic updates without multi-document joins.
- **Atomic State Transitions:** In `change_status()`, MongoDB's `find_one_and_update` filters by `_id` and checks whether the current status is an allowed predecessor in one atomic step. This prevents race conditions and invalid transitions.
- **Compound Indexes `(field, created_at)`:** Every listing query sorts newest first. A single-field index on `city` forces an in-memory sort or is bypassed. The compound index `(location.city, created_at)` satisfies both the filter and the sort order in one scan.
- **Two-Layer Validation:** Pydantic provides user-friendly HTTP validation error messages; MongoDB's `$jsonSchema` validator protects data integrity against direct manual inserts.
