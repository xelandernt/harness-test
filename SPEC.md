# EurExpense Approval API — Specification

This document is the authoritative contract for the task. The test suite in
`tests/` is the executable form of this document. Where this document and the
tests appear to disagree, treat the discrepancy as a defect in the repository,
not as licence to change either one.

## 1. Environment and contract

- Python **3.12+**, managed with **uv**. Dependencies are declared in
  `pyproject.toml` and pinned in `uv.lock`.
- The only supported commands are:

  ```bash
  uv sync
  uv run pytest
  ```

- The test suite imports exactly one symbol from your code:

  ```python
  from app.main import create_app
  ```

  `create_app()` must return a `fastapi.FastAPI` instance. Each call must
  produce an application with **fresh, isolated state**: two applications
  created in the same process must not share users, expenses, tokens, or
  identifiers.
- Storage is **in memory**. No database, no files, no network access.
- Only files under `app/` may be created or modified. Do not add dependencies:
  the environment has no network access.
- The repository ships `ruff` (lint + format) and `pyrefly` (type checking)
  configurations. Keep `uv run ruff check`, `uv run ruff format --check`, and
  `uv run pyrefly check` clean.
- `GET /health` is implemented in the skeleton. Every other route is yours to
  build.

## 2. Test suite rules

`tests/` is the specification made executable and is strictly **read-only**.

- Do not modify, delete, rename, or add any file under `tests/`, including
  `conftest.py`.
- Do not add `skip`/`xfail` markers, weaken assertions, or change test
  configuration (`pytest.ini`, `addopts`, discovery paths, plugins).
- Do not special-case test inputs, detect the test client, or branch on
  environment variables to produce different behaviour under test.
- A run that violates any of these rules is invalid, regardless of how many
  tests pass.

The suite drives the application over HTTP only. It never imports your models,
services, routers, or storage, so the internal structure is entirely yours.

## 3. Domain model

### Users

| Field        | Type            | Notes                                              |
| ------------ | --------------- | -------------------------------------------------- |
| `id`         | string          | Opaque, non-empty, unique within an app instance    |
| `email`      | string          | Valid address, stored lowercase, unique             |
| `full_name`  | string          | Trimmed, 1–100 characters                           |
| `role`       | enum            | `employee`, `manager`, or `admin`                   |
| `manager_id` | string or null  | See reporting-line rules below                      |

Passwords are never returned by any endpoint. Password hashing and token
expiry are out of scope: compare and store passwords as provided.

### Expenses

| Field              | Type            | Notes                                                        |
| ------------------ | --------------- | ------------------------------------------------------------ |
| `id`               | string          | Opaque, non-empty, unique within an app instance              |
| `owner_id`         | string          | The user who created the expense                              |
| `amount`           | string          | Money, exactly two decimal places, e.g. `"12.50"`             |
| `currency`         | string          | Always `"EUR"`                                                |
| `category`         | enum            | `travel`, `meals`, `equipment`, `training`, `other`           |
| `description`      | string          | Trimmed, 1–500 characters                                     |
| `status`           | enum            | `draft`, `submitted`, `approved`, `rejected`                  |
| `created_at`       | string          | RFC 3339 UTC timestamp, always present                        |
| `submitted_at`     | string or null  | Set when the expense is submitted                             |
| `decided_at`       | string or null  | Set when the expense is approved or rejected                  |
| `decided_by`       | string or null  | User id of the approver or rejector                           |
| `rejection_reason` | string or null  | Trimmed reason when rejected, otherwise `null`                |

A response representing an expense always contains every field above.

### Reporting lines

- An `admin` has `manager_id: null`.
- A `manager` may have a `manager_id` that references an **admin**.
- An `employee` **must** have a `manager_id` that references a **manager** or an
  **admin**.

Only **direct** reporting lines matter: a manager's manager does not see or act
on the manager's reports' expenses.

### Seeded data

`create_app()` must seed exactly one user:

| email               | password    | full_name       | role  | manager_id |
| ------------------- | ----------- | --------------- | ----- | ---------- |
| `admin@example.com` | `admin1234` | Bootstrap Admin | admin | `null`     |

Its `id` is opaque and must be discoverable through `GET /users`. Every other
user is created through the API.

## 4. Conventions

### Money

- Monetary values are JSON **strings** with exactly two decimal places.
  `"10.5"` is invalid; `"10.50"` is valid. JSON numbers are invalid.
- Requests are validated, never rounded: a value with more than two decimal
  places is a validation error.
- `amount` must be greater than `0.00` and at most `100000.00`.
- `currency` is always `"EUR"`. It may be omitted (defaults to `"EUR"`) and is
  accepted case-insensitively (`"eur"`, `"Eur"`), but it is always serialized as
  `"EUR"`. Any other value is a validation error.

### Categories

Category input is trimmed and case-insensitive (`"TRAVEL"`, `" travel "`).
Responses always contain the lowercase canonical value.

### Identifiers

Identifiers are opaque non-empty strings. The suite never assumes a prefix or
format, only uniqueness and stability.

### Timestamps

Timestamps are RFC 3339 strings in UTC, with a `Z` or `+00:00` offset, e.g.
`2026-01-31T09:15:00Z`. They must be parseable as timezone-aware datetimes.
The suite never asserts exact values, only presence, nullability, and relative
ordering.

### Strings

`full_name`, `description`, and `rejection_reason` are trimmed before storage.
A value that is empty after trimming is a validation error. Length limits apply
after trimming.

### Unknown fields

Every request body rejects unknown fields with `422`.

### Errors

Error responses contain a JSON object with a `detail` key. For domain errors,
`detail` is a non-empty string. For request-validation errors, `detail` follows
FastAPI's standard shape (a list). Exact message wording is **not** part of the
contract; only the status code and the presence of `detail`.

### Error precedence

When several conditions could apply, resolve them in this order:
`401` → `404` → `403` → `409` → `422`.
The suite only exercises requests for which this order is unambiguous.

## 5. Authentication

### `POST /auth/token`

Request body:

```json
{ "email": "admin@example.com", "password": "admin1234" }
```

- `200` — `{ "access_token": "<string>", "token_type": "bearer" }`
- `401` — unknown email or wrong password
- `422` — malformed body

Email matching is case-insensitive. Tokens are opaque, at least 16 characters
long, unique per login, and never expire. Several tokens for one user may be
valid at the same time.

### Authenticated requests

Every endpoint except `POST /auth/token` and `GET /health` requires:

```
Authorization: Bearer <access_token>
```

A missing, malformed, or unknown token yields `401`.

## 6. Users

### `POST /users` — admin only

Request body:

```json
{
  "email": "ada@example.com",
  "full_name": "Ada Lovelace",
  "password": "correct-horse-1",
  "role": "employee",
  "manager_id": "<manager user id>"
}
```

- `201` — `{ "id", "email", "full_name", "role", "manager_id" }`; never the
  password
- `409` — email already exists (case-insensitive)
- `422` — invalid email, password shorter than 8 or longer than 128 characters,
  invalid role, blank or over-long `full_name`, missing/invalid `manager_id`
  per the reporting-line rules, or an admin supplying a `manager_id`
- `403` — caller is not an admin
- `401` — missing/invalid token

`email` is stored lowercase. `full_name` is trimmed.

### `GET /users` — admin only

- `200` — JSON array of all users, sorted by `email` ascending
- `403` — caller is not an admin

### `GET /users/{id}`

- `200` — the user object, when the caller is an admin or the user themself
- `403` — caller is authenticated but is neither
- `404` — unknown user id

## 7. Expenses

Any authenticated user may create and own expenses, regardless of role.

### `POST /expenses`

Request body:

```json
{
  "amount": "12.50",
  "category": "travel",
  "description": "Client visit",
  "currency": "EUR"
}
```

`currency` is optional. `amount`, `category`, and `description` are required.

- `201` — the created expense, with `status: "draft"` and `submitted_at`,
  `decided_at`, `decided_by`, and `rejection_reason` all `null`
- `422` — any request that violates §4
- Policy limits (§9) are **not** checked at creation.

An optional `Idempotency-Key` header changes the semantics; see §11.

### `GET /expenses/{id}`

- `200` — the expense, when the caller is the owner, the owner's direct manager,
  or an admin
- `403` — caller is authenticated but not permitted to see it
- `404` — unknown expense id

### `PATCH /expenses/{id}`

Request body: any subset of `amount`, `category`, `description`, with at least
one present. Omitted fields are unchanged.

- `200` — the updated expense
- `403` — caller is not the owner
- `409` — the expense is not a `draft`
- `404` — unknown expense id
- `422` — empty body, unknown field (including `status` or `currency`), or any
  value violating §4

### `DELETE /expenses/{id}`

- `204` — deleted, empty body; the owner may delete only a `draft`
- `403` — caller is not the owner
- `409` — the expense is not a `draft`
- `404` — unknown expense id

### `POST /expenses/{id}/submit`

No request body.

- `200` — the expense, now `submitted`, with `submitted_at` set
- `403` — caller is not the owner
- `409` — the expense is not a `draft`
- `404` — unknown expense id
- `422` — the expense exceeds the category policy limit (§9); the expense
  remains a `draft` and `submitted_at` stays `null`

### `POST /expenses/{id}/approve`

No request body.

- `200` — the expense, now `approved`, with `decided_at` set, `decided_by` set
  to the caller's id, and `rejection_reason: null`
- `403` — the caller is the owner (self-approval is forbidden, **including for
  admins**), or the caller is neither the owner's direct manager nor an admin
- `409` — the expense is not `submitted`
- `404` — unknown expense id

### `POST /expenses/{id}/reject`

Request body:

```json
{ "reason": "Missing receipt" }
```

- `200` — the expense, now `rejected`, with `decided_at`, `decided_by`, and
  `rejection_reason` set to the trimmed reason
- `422` — `reason` missing, blank after trimming, or longer than 500 characters
- `403` — the caller is the owner (self-rejection is forbidden, including for
  admins), or the caller is neither the owner's direct manager nor an admin
- `409` — the expense is not `submitted`
- `404` — unknown expense id

## 8. State machine

```
draft ──submit──▶ submitted ──approve──▶ approved
                        └────reject───▶ rejected
```

- Only the owner may submit.
- Only the owner's direct manager or an admin may approve or reject, and never
  the owner.
- `draft` expenses may be edited or deleted.
- `submitted`, `approved`, and `rejected` expenses are immutable apart from the
  transitions above.
- `approved` and `rejected` are terminal.
- Any transition not shown above returns `409` (`403` still takes precedence
  when the caller is not permitted to act on the expense at all).

An admin owns expenses like anyone else. Because self-approval is forbidden, an
admin's own expense can only be decided by a different admin.

## 9. Policy limits

Checked **only** at submit time, against the `amount` and `category` at that
moment:

| Category  | Limit      |
| --------- | ---------- |
| travel    | `1000.00`  |
| meals     | `75.00`    |
| equipment | `2500.00`  |
| training  | `800.00`   |
| other     | `500.00`   |

An amount exactly equal to the limit is allowed. One cent over is rejected with
`422`. A draft that exceeds its limit may exist; it simply cannot be submitted
until the amount is reduced or the category changes.

## 10. Listing expenses

### `GET /expenses`

Query parameters, all optional:

| Name        | Type    | Default | Rules                                   |
| ----------- | ------- | ------- | --------------------------------------- |
| `status`    | enum    | —       | `draft`, `submitted`, `approved`, `rejected` |
| `category`  | enum    | —       | Canonical category                      |
| `owner_id`  | string  | —       | Filter by owner                          |
| `page`      | integer | `1`     | `>= 1`                                  |
| `page_size` | integer | `20`    | `1..100`                                |

Visibility:

- `employee` sees their own expenses only.
- `manager` sees their own expenses plus those of their **direct** reports.
- `admin` sees every expense.

All supplied filters are combined with AND. `owner_id` cannot widen visibility:
filtering by an owner the caller cannot see yields an empty page with
`total: 0`.

Ordering is oldest first, in the order the expenses were created.

Response:

```json
{
  "items": [ /* expense objects */ ],
  "page": 1,
  "page_size": 20,
  "total": 42
}
```

`total` is the number of matching, visible expenses before pagination. A page
past the end returns `items: []` and the correct `total`; it is **not** a `404`.

Invalid enum values, `page < 1`, or `page_size` outside `1..100` return `422`.

## 11. Idempotency

`POST /expenses` accepts an optional `Idempotency-Key` header:

- If present, it must be 8–64 characters, otherwise `422`.
- Keys are scoped per owner. Two owners may use the same key independently.
- Replaying the **same request payload** (same owner, same key, same normalized
  amount, category, description, and currency) must not create a second
  expense. The replay returns `200` with the **current** representation of the
  original expense. The initial request still returns `201`.
- Reusing a key with a **different** payload returns `409`.
- Without the header, every request creates a new expense.

## 12. Status code summary

| Code | Meaning in this API                                                  |
| ---- | -------------------------------------------------------------------- |
| 200  | Successful read, update, transition, or idempotent replay            |
| 201  | Resource created                                                      |
| 204  | Resource deleted, empty body                                          |
| 401  | Missing, malformed, or unknown token                                  |
| 403  | Authenticated but not permitted                                       |
| 404  | Unknown user or expense id                                            |
| 409  | State conflict, duplicate email, or idempotency-key payload mismatch  |
| 422  | Request validation or policy-limit violation                          |

## 13. Out of scope

- Persistence of any kind between `create_app()` calls
- Password hashing, password reset, token expiry, refresh tokens
- Currencies other than EUR
- Partial approval, attachments, comments, audit history
- Sorting options, full-text search, user pagination
- Rate limiting, CORS, middleware, OpenAPI documentation polish
