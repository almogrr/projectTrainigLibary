# Book Management System

## Overview
The Book Management System is a Flask-based web application designed to manage books, users, and loans in a library setting. It provides functionality for users to register, log in, add, update, and delete books, as well as loan and return books. The application utilizes JWT tokens for authentication and authorization.

## Features
- User Registration: Allows users to register with the system by providing their name, city, age, username, and password.
- User Authentication: Utilizes JWT tokens for user authentication, ensuring secure access to protected endpoints.
- Book Management: Provides CRUD (Create, Read, Update, Delete) operations for managing books, including adding, updating, and deleting books.
- Loan Management: Allows users to loan and return books, with proper validation and handling of loan periods.
- Image Upload: Supports uploading images for book covers, ensuring a visually appealing interface.
- Admin Functionality: Admin users have additional privileges, such as viewing all users and deleting users from the system.

## Installation
1. Clone the repository

2. Install dependencies:
pip install -r requirements.txt


## Usage
1. Set up the database by running:
python:
from app import db
db.create_all()
exit()

2. Run the Flask application:
cd backend
python app.py

3. Access the application in your web browser at `http://localhost:5000`.

## API Endpoints
- **POST /register**: Register a new user.
- **POST /login**: Log in with username and password to obtain JWT token.
- **GET /books**: Get all books.
- **POST /books**: Add a new book.
- **GET /books/:id**: Get details of a specific book.
- **PUT /books/:id**: Update details of a specific book.
- **DELETE /books/:id**: Delete a specific book.
- **POST /books/:id/loan**: Loan a book to a user.
- **POST /books/:id/return**: Return a book.
- **GET /users**: Get all users (admin only).
- **DELETE /users/:id**: Delete a user by ID (admin only).
- **GET /loans**: Get all loan records.
- **GET /books/find**: Find a book by name.
- **GET /users/find**: Find a user by name.

## Contributing
Contributions are welcome! Feel free to open issues or submit pull requests.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
