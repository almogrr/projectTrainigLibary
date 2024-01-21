from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(16)
db = SQLAlchemy(app)
login_manager = LoginManager(app)

# Define User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# Define Book model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('books', lazy=True))

# Initialize login manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes for CRUD operations on User and Book
@app.route('/register', methods=['POST','GET'])
def register():
    data = request.get_json()
    new_user = User(name=data['name'], username=data['username'], password=data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'})

@app.route('/login', methods=['POST','GET'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.password == data['password']:
        login_user(user)
        session['user_id'] = user.id  # Save user_id in session
        return jsonify({'message': 'Login successful'})
    else:
        return jsonify({'message': 'Invalid username or password'}), 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'})

@app.route('/users', methods=['GET'])
@login_required
def get_users():
    users = User.query.all()
    users_list = [{'id': user.id, 'name': user.name, 'username': user.username} for user in users]
    return jsonify(users_list)

@app.route('/books', methods=['GET'])
@login_required
def get_books():
    books = current_user.books
    books_list = [{'id': book.id, 'name': book.name} for book in books]
    return jsonify(books_list)

@app.route('/books', methods=['POST'])
@login_required
def add_book():
    data = request.get_json()
    new_book = Book(name=data['name'], user_id=current_user.id)
    db.session.add(new_book)
    db.session.commit()
    return jsonify({'message': 'Book added successfully'})

@app.route('/books/<int:book_id>', methods=['PUT'])
@login_required
def update_book(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'message': 'Book not found'}), 404
    
    if book.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized to update this book'}), 401

    data = request.get_json()
    book.name = data['name']
    
    db.session.commit()
    
    return jsonify({'message': 'Book updated successfully'})

@app.route('/books/<int:book_id>', methods=['DELETE'])
@login_required
def delete_book(book_id):
    book = Book.query.get(book_id)
    if book and book.user_id == current_user.id:
        db.session.delete(book)
        db.session.commit()
        return jsonify({'message': 'Book deleted successfully'})
    else:
        return jsonify({'message': 'Book not found or unauthorized'}), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
