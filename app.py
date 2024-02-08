from flask import Flask, g, request, jsonify, send_from_directory, current_app, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from functools import wraps




app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.static_folder = 'uploads'
app.static_url_path = '/uploads'
db = SQLAlchemy(app)
api = Api(app)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    books = db.relationship('Book', backref='user', lazy=True)  # Change backref name to 'customer'
    loans = db.relationship('Loan', backref='user', lazy=True)


    def generate_token(self):
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': self.id
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=True)
    loan_date = db.Column(db.DateTime, nullable=True)
    return_date = db.Column(db.DateTime, nullable=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year_published = db.Column(db.Integer, nullable=False)
    book_type = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(100), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Change foreign key name to 'customer_id'
    loans = db.relationship('Loan', backref='book', lazy=True)  # Define relationship backref



def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization', '').split()

        if not token or token[0] != 'Bearer':
            return jsonify({'message': 'Authorization header is missing or invalid'}), 401

        try:
            payload = jwt.decode(token[1], current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user = User.query.get(payload['sub'])
            return func(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

    return wrapper



@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256', salt_length=8)
    is_admin = data.get('is_admin', False)  # Default to False if not provided
    new_user = User(name=data['name'], city=data['city'], age=data['age'], username=data['username'], password=hashed_password, is_admin=is_admin)
    db.session.add(new_user)
    db.session.commit()
    token = new_user.generate_token()
    return jsonify({'token': token})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    if user and check_password_hash(user.password, data['password']):
        token = user.generate_token()
        response_data = {'token': token, 'is_admin': user.is_admin}  # Include is_admin field in the response
        return jsonify(response_data)
    return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/books', methods=['GET'])
@login_required
def get_books():
    books = Book.query.all()
    book_list = [{'id': book.id, 'name': book.name, 'author': book.author, 'year_published': book.year_published, 'book_type': book.book_type, 'customer_id': book.customer_id if book.customer_id is not None else "None", 'image': book.image_path} for book in books]
    return jsonify({'books': book_list})

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    user_info = []
    for user in users:
        user_info.append({
            'id': user.id,
            'name': user.name,
            'city': user.city,
            'age': user.age,
            'username': user.username
        })
    return jsonify({'users': user_info})

# Define route to delete a user
@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        # Query the user by ID
        user = User.query.get(user_id)
        if user:
            # Delete the user
            db.session.delete(user)
            db.session.commit()
            return jsonify({'message': 'User deleted successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/books/<int:book_id>', methods=['GET'])
@login_required
def get_book(book_id):
    book = Book.query.get(book_id)
    if book:
        return jsonify({'id': book.id, 'name': book.name, 'author': book.author, 'year_published': book.year_published, 'book_type': book.book_type, 'customer_id': book.customer_id if book.customer_id is not None else "None", 'image': book.image_path})
    return jsonify({'message': 'Book not found'}), 404


@app.route('/books', methods=['POST'])
@login_required
def add_book():
    data = request.form
    book_name = data['name']
    author = data['author']
    year_published = data['year_published']
    book_type = data['book_type']
    book_image = request.files.get('image')

    # Validate file extension
    if book_image and allowed_file(book_image.filename):
        # Save the uploaded image
        filename = secure_filename(book_image.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        book_image.save(file_path)

        customer_id = None

        # Create a new Book record in the database
        new_book = Book(name=book_name, author=author, year_published=year_published, book_type=book_type, image_path=file_path, customer_id=None)
        db.session.add(new_book)
        db.session.commit()
        
        return jsonify({'message': 'Book added successfully'})
    else:
        return jsonify({'message': 'Invalid file or file format'}), 400

@app.route('/books/<int:book_id>', methods=['PUT'])
@login_required
def update_book(book_id):
    data = request.form
    book = Book.query.get(book_id)
    if book:

        book.name = data.get('name', book.name)
        book.author = data.get('author', book.author)
        book.year_published = data.get('year_published', book.year_published)
        book.book_type = data.get('book_type', book.book_type)
        
        # Update the image if provided
        if 'image' in request.files:
            book_image = request.files['image']
            if book_image and allowed_file(book_image.filename):
                filename = secure_filename(book_image.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                book_image.save(file_path)
                book.image_path = file_path
            else:
                return jsonify({'message': 'Invalid file or file format for image'}), 400
        
        
        db.session.commit()
        return jsonify({'message': 'Book updated successfully'})
    return jsonify({'message': 'Book not found'}), 404



@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get(book_id)
    if book:
        db.session.delete(book)
        db.session.commit()
        return jsonify({'message': 'Book deleted successfully'})
    return jsonify({'message': 'Book not found'}), 404


@app.route('/users/find', methods=['GET'])
def find_user_by_name():
    try:
        user_name = request.args.get('name')
        if not user_name:
            return jsonify({'error': 'User name parameter is missing'}), 400
            
        # Query the database to find the user by name
        user = User.query.filter_by(name=user_name).first()

        if user:
            # User found, return their details
            user_data = {
                'id': user.id,
                'name': user.name,
                'city': user.city,
                'age': user.age,
                'username': user.username
            }
            return jsonify(user_data), 200
        else:
            # User not found
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/books/find', methods=['GET'])
def find_book_by_name():
    try:
        # Get the book name from the query parameters
        book_name = request.args.get('name')
        
        if not book_name:
            return jsonify({'error': 'Book name parameter is missing'}), 400
            
        # Query the database to find the book by name
        book = Book.query.filter_by(name=book_name).first()

        if book:
            # Book found, return its details
            book_data = {
                'id': book.id,
                'name': book.name,
                'author': book.author,
                'year_published': book.year_published,
                'book_type': book.book_type,
                'image_path': book.image_path  # Corrected key to match JavaScript code
            }
            return jsonify(book_data), 200
        else:
            # Book not found
            return jsonify({'error': 'Book not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
from datetime import timedelta

@app.route('/loans', methods=['GET'])
def get_loans():
    try:
        loans = Loan.query.all()
        loan_info = []

        for loan in loans:
            book = Book.query.get(loan.book_id)

            if not book:
                continue

            # Get the maximum loan time based on book type
            max_loan_time = {
                1: timedelta(days=10),  
                2: timedelta(days=5),   
                3: timedelta(days=2)    
            }

            # Calculate the expected return date
            expected_return_date = loan.loan_date + max_loan_time.get(book.book_type, timedelta(days=0))

            loan_info.append({
                'id': loan.id,
                'customer_id': loan.customer_id,
                'book_id': loan.book_id,
                'loan_date': loan.loan_date.strftime('%d-%m-%Y %H:%M:%S') if loan.loan_date else None,
                'return_date': loan.return_date.strftime('%d-%m-%Y %H:%M:%S') if loan.return_date else None,
                'expected_return_date': expected_return_date.strftime('%d-%m-%Y %H:%M:%S') if expected_return_date else None
            })

        return jsonify({'loans': loan_info}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/books/<int:book_id>/loan', methods=['POST'])
@login_required 
def loan_book(book_id):
    book = Book.query.get(book_id)

    if not book:
        return jsonify({'message': 'Book not found'}), 404

    if book.customer_id is not None:
        return jsonify({'message': 'Book is already loaned'}), 400

    book.customer_id = g.user.id 
    loan_date = datetime.utcnow()
    loan = Loan(book_id=book_id, customer_id=g.user.id, loan_date=loan_date)
    db.session.add(loan)
    db.session.commit()

    return jsonify({'message': 'Book loaned successfully'})






@app.route('/books/<int:book_id>/return', methods=['POST'])
@login_required 
def return_book(book_id):
    book = Book.query.get(book_id)

    if not book:
        return jsonify({'message': 'Book not found'}), 404

    if book.customer_id != g.user.id:
        return jsonify({'message': 'You are not authorized to return this book'}), 403

    loan = Loan.query.filter_by(book_id=book_id, customer_id=g.user.id, return_date=None).first()

    if not loan:
        return jsonify({'message': 'Loan record not found for this book'}), 404

    loan.return_date = datetime.utcnow()
    db.session.commit()

    book.customer_id = None
    db.session.commit()

    # Get the maximum loan time based on book type
    max_loan_time = {
            1: timedelta(days=10),  
            2: timedelta(days=5),   
            3: timedelta(days=2) 
    }

    # Calculate the expected return date based on the maximum loan time
    expected_return_date = loan.loan_date + max_loan_time.get(book.book_type, timedelta(days=0))

    # Check if the return is late
    if datetime.utcnow() > expected_return_date:
        return jsonify({'message': 'Book returned successfully, but it is late!'}), 200

    return jsonify({'message': 'Book returned successfully'}), 200


@app.route('/books/return', methods=['GET'])
def display_late_returns():
    late_returns = []

    # Get all loans that are not returned yet
    loans = Loan.query.filter_by(return_date=None).all()

    for loan in loans:
        book = Book.query.get(loan.book_id)

        if not book:
            continue

        # Get the maximum loan time based on book type in seconds
        max_loan_time = {
                1: timedelta(days=10),  
                2: timedelta(days=5),   
                3: timedelta(days=2)        
        }

        # Calculate the expected return date based on the loan date and the maximum loan time
        expected_return_date = loan.loan_date + max_loan_time.get(book.book_type, timedelta(days=0))

        # Check if the return is late
        if datetime.utcnow() > expected_return_date:
            late_returns.append({
                'id': loan.id,
                'book_name': book.name,
                'loan_date': loan.loan_date.strftime('%Y-%m-%d %H:%M:%S'),
                'expected_return_date': expected_return_date.strftime('%Y-%m-%d %H:%M:%S'),
                'customer_id': loan.customer_id
            })

    return jsonify({'late_returns': late_returns}), 200



@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
            os.makedirs(current_app.config['UPLOAD_FOLDER'])
        
        db.create_all()
        app.run(debug=True)