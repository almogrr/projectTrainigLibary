from flask import Flask, g, request, jsonify, send_from_directory, current_app
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os

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
VALID_BOOK_TYPES = {1, 2, 3}  # Define the valid book types

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    is_librarian = db.Column(db.Boolean, default=False) # admin
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
    new_user = User(name=data['name'], city=data['city'], age=data['age'], username=data['username'], password=hashed_password)
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
        return jsonify({'token': token})
    return jsonify({'message': 'Invalid credentials'}), 401


@app.route('/books', methods=['GET'])
def get_books():
    books = Book.query.all()
    book_list = []
    for book in books:
        book_info = {
            'id': book.id,
            'name': book.name,
            'author': book.author,
            'year_published': book.year_published,
            'book_type': book.book_type,
            'customer_id': book.customer_id,
            'image': book.image_path
        }
        book_list.append(book_info)
    return jsonify({'books': book_list})


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get(book_id)
    if book:
        book_info = {
            'id': book.id,
            'name': book.name,
            'author': book.author,
            'year_published': book.year_published,
            'book_type': book.book_type,
            'customer_id': book.customer_id,
            'image': book.image_path
        }
        return jsonify(book_info)
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

        # Get the customer ID from the logged-in user
        customer_id = g.user.id

        # Create a new Book record in the database with the customer ID
        new_book = Book(name=book_name, author=author, year_published=year_published, book_type=book_type, image_path=file_path, customer_id=customer_id)
        db.session.add(new_book)
        db.session.commit()

        return jsonify({'message': 'Book added successfully'})
    else:
        return jsonify({'message': 'Invalid file or file format'}), 400



@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    book = Book.query.get(book_id)
    if book:
        book.name = data['name']
        book.author = data['author']
        book.year_published = data['year_published']
        book.book_type = data['book_type']
        book.image_path = data.get('image_path', book.image_path)
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

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(current_app.config['UPLOAD_FOLDER']):
            os.makedirs(current_app.config['UPLOAD_FOLDER'])
        
        db.create_all()
        app.run(debug=True)