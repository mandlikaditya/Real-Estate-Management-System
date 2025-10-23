# Real Estate Management System

A Flask-based web application for managing real estate properties, bookings, and user interactions.

## Features

- User authentication (Agents and Renters)
- Property management
- Booking system
- Address and credit card management
- Reward points system
- Neighborhood management
- Search functionality

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following variables:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DB_HOST=localhost
DB_PORT=5433
DB_NAME=realestate_db
DB_USER=postgres
DB_PASSWORD=your-password
```

5. Set up the database:
- Create a PostgreSQL database named `realestate_db`
- Update the database credentials in the `.env` file

## Running the Application

1. Activate the virtual environment (if not already activated):
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Run the Flask application:
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Project Structure

```
.
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── .gitignore         # Git ignore file
└── static/            # Static files (CSS, JS, images)
    └── style.css      # CSS styles
```

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 