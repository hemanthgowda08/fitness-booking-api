# FOR·MA Fitness Booking API

FOR·MA is a fitness class booking application built with FastAPI and SQLite. It includes a web frontend built with HTML, CSS, and JavaScript.

Users can create accounts, browse upcoming classes, book available slots, and view their bookings. Hosts can create and cancel their own classes, while administrators can manage classes across the application.

## Features

- User registration and login with JWT authentication
- Role-based access for members, hosts, and administrators
- Create and cancel fitness classes
- Book classes and view personal booking history
- Prevent duplicate bookings and bookings when no slots remain
- Preserve booking history when a class is cancelled
- Handle class times using Indian Standard Time (IST)
- SQLite database migrations that preserve existing records
- Automated tests for authentication, bookings, permissions, and migrations

## Requirements

- Python 3.9 or later
- pip

## Setup

Clone the repository and move into the project directory:

```bash
git clone https://github.com/hemanthgowda08/fitness-booking-api.git
cd fitness-booking-api
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `.env`:

```env
SECRET_KEY=replace_with_your_generated_secret
```

Replace the example value with your generated secret. Keep `.env` private and never commit it to GitHub.

## Running the application

### Start the API

From the project root, run:

```bash
uvicorn main:app --reload
```

The API will be available at:

- API: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs

### Start the frontend

Open a second terminal and run:

```bash
cd fitness-booking-api/frontend
python3 -m http.server 5500
```

If you are already in the project root, `cd frontend` is sufficient.

Open http://127.0.0.1:5500 in your browser. Keep both servers running while using the application.

The local API configuration allows frontend requests from `localhost:5500` and `127.0.0.1:5500`.

## Roles and permissions

| Role | Permissions |
| --- | --- |
| Member | Browse classes, book classes, and view personal bookings |
| Host | Member permissions, plus create and cancel classes they own |
| Admin | Member permissions, plus create classes and cancel any class |

New accounts receive the `member` role by default. Users cannot assign themselves a host or admin role through the public signup endpoint.

### Promoting an account to host

First, register the account through the application. Then run this command on the trusted machine that has access to the database:

```bash
python manage_roles.py promote-host instructor@example.com --confirm
```

Replace `instructor@example.com` with the email address of the existing account.

### Setting up an administrator

Register the intended administrator account first, then run:

```bash
python manage_roles.py promote-admin owner@example.com --confirm
```

Replace `owner@example.com` with the existing account's email address.

These are local administrative commands. There is no public endpoint for promoting users to host or admin. Access to the machine and database should be restricted to trusted administrators.

## API endpoints

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| GET | `/` | Public | Check API status |
| POST | `/signup` | Public | Register a member account |
| POST | `/login` | Public | Log in and receive a JWT |
| GET | `/me` | Authenticated | Get the current user's account and role |
| GET | `/classes` | Public | List upcoming, non-cancelled classes |
| POST | `/classes` | Host/Admin | Create a class |
| POST | `/book` | Authenticated | Book an available class |
| GET | `/bookings` | Authenticated | View personal bookings |
| PATCH | `/classes/{class_id}/cancel` | Owner Host/Admin | Cancel an authorized class |

Protected endpoints require the following header:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Replace `YOUR_ACCESS_TOKEN` with the token returned by the login endpoint.

## API usage examples

The following examples assume the API is running locally.

### 1. Register a user

```bash
curl -X POST http://127.0.0.1:8000/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Member",
    "email": "member@example.com",
    "password": "ChangeMe123!"
  }'
```

This creates a member account. Use an email address that has not already been registered.

### 2. Log in

```bash
curl -X POST http://127.0.0.1:8000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "member@example.com",
    "password": "ChangeMe123!"
  }'
```

The response contains an `access_token`. Copy it and use it in subsequent authenticated requests.

### 3. List available classes

```bash
curl http://127.0.0.1:8000/classes
```

This returns upcoming classes that have not been cancelled.

### 4. Create a class

Class creation requires a host or admin account.

```bash
curl -X POST http://127.0.0.1:8000/classes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "name": "Evening Yoga",
    "instructor": "Maya",
    "date_time": "2030-03-15T18:30:00+05:30",
    "total_slots": 12
  }'
```

Use a valid host or admin token and a future date and time. The date above is only an example.

### 5. Book a class

Replace `1` with the ID of an existing class.

```bash
curl -X POST http://127.0.0.1:8000/book \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"class_id": 1}'
```

The booking is associated with the authenticated user. The API prevents duplicate bookings and rejects bookings when no slots remain.

### 6. View your bookings

```bash
curl http://127.0.0.1:8000/bookings \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

The response contains the authenticated user's booking history, including bookings associated with cancelled classes.

### 7. Cancel a class

A host can cancel a class they created. An admin can cancel any class.

```bash
curl -X PATCH http://127.0.0.1:8000/classes/1/cancel \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Replace `1` with the class ID and use an authorized token.

A cancelled class no longer appears in the upcoming class list and cannot receive new bookings. Existing booking records are preserved. Repeated cancellation requests return a conflict response.

## Time handling and booking rules

Class creation requires an ISO 8601 date and time with an explicit timezone offset. For example:

```text
2030-03-15T18:30:00+05:30
```

The application handles class times in `Asia/Kolkata` (IST).

Booking safeguards include:

- Authentication for booking and viewing personal bookings
- Duplicate-booking prevention
- Slot availability checks
- Database constraints and transactional updates
- Protection against booking a cancelled class
- Preservation of booking history after cancellation

## Database migrations

The application uses SQLite. Its migration logic adds the role and cancellation fields required by the application while preserving existing users, classes, and bookings.

Existing users receive the default member role. Existing classes without a recorded creator remain without an assigned owner, so only an administrator can cancel those legacy classes.

Back up your database before upgrading an existing installation.

## Running tests

Activate your virtual environment and run the following command from the project root:

```bash
pytest -q
```

The tests use a separate temporary SQLite database. They cover authentication, role permissions, class cancellation, booking rules, and migration of existing records.

## Project structure

```text
fitness-booking-api/
├── main.py
├── database.py
├── models.py
├── schemas.py
├── security.py
├── time_utils.py
├── migrations.py
├── manage_roles.py
├── requirements.txt
├── .env.example
├── frontend/
└── tests/
```

## Security notes

- Do not commit `.env`, access tokens, or other secrets.
- Keep `.env.example` free of real credentials.
- Do not expose local administrative scripts as public API endpoints.
- Restrict access to the machine and database used for administrative role changes.
