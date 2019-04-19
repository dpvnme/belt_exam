from flask import Flask, render_template, session, redirect, request, flash
from mysqlconnection import connectToMySQL
from flask_bcrypt import Bcrypt
import random
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Top Secret'
bcrypt = Bcrypt(app)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+[a-zA-Z]+$')
NAME_REGEX =  re.compile(r'^[a-zA-Z]+$')
SCHEMA = "belt_exam"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/registration', methods=['POST'])
def registration():
    errors = []
    #First Name - letters only, at least 2 characters and that it was submitted
    if len(request.form['first_name']) < 3:
        errors.append('First name must be at least two letters')
    if not NAME_REGEX.match(request.form['first_name']):
        errors.append('First name must be letter only')
    
    #Last Name - letters only, at least 2 characters and that it was submitted
    if len(request.form['last_name']) < 3:
        errors.append('Last name must be at least two letters')
    if not NAME_REGEX.match(request.form['last_name']):
        errors.append('Last name must be letter only')

    #Email - valid Email format, does not already exist in the database, and that it was submitted
    if not EMAIL_REGEX.match(request.form['email']):
        errors.append("Email must be in correct format")
    db = connectToMySQL(SCHEMA)
    query = "SELECT * FROM users WHERE email=%(em)s;"
    data = {
        "em": request.form['email']
    }
    matching_user = db.query_db(query, data)
    if matching_user:
        errors.append("Email already in use")
    
    #Password - at least 8 characters, and that it was submitted
    if len(request.form['password']) < 8:
        errors.append("Password must be at least 8 characters long")
    
    #Password Confirmation - matches password
    if request.form['password'] != request.form['password_confirmation']:
        errors.append("Password must match")
    
    if errors:
        for error in errors:
            flash(error)
        return redirect('/')

    #Add user to the database and hash the password and create session for user
    password_hash = bcrypt.generate_password_hash(request.form['password'])
    db = connectToMySQL(SCHEMA)
    query = "INSERT INTO users (first_name, last_name, email, password_hash) VALUES(%(f)s, %(l)s, %(e)s, %(p)s)"
    data = {
        "f": request.form['first_name'],
        "l": request.form['last_name'],
        "e": request.form['email'],
        "p": password_hash
    }
    user_id = db.query_db(query, data)
    session['user_id'] = user_id
    session['first_name'] = request.form['first_name']
    session['last_name'] = request.form['last_name']
    session['email'] = request.form['email']
    return redirect('/quotes')

@app.route('/login', methods=['POST'])
def login():
    #Check whether the email provided is associated with a user in the database
    db = connectToMySQL(SCHEMA)
    query = "SELECT * FROM users WHERE email=%(em)s;"
    data = {
        "em": request.form['email']
    }
    matching_users = db.query_db(query, data)
    if matching_users:
        user = matching_users[0]
        if bcrypt.check_password_hash(user['password_hash'], request.form['password']):
            session['user_id'] = user['id']
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session['email'] = request.form['email']
            return redirect('/quotes')
    flash("Email or password invalid")
    return redirect('/')

@app.route('/quotes')
def quotes():
    if "user_id" not in session:
        return redirect('/')
    else:
        mysql = connectToMySQL(SCHEMA)
        all_quotes = mysql.query_db("SELECT users.first_name, users.last_name, quotes.id AS quote_id, quotes.author, quotes.content, quotes.user_id FROM users JOIN quotes ON users.id = quotes.user_id;")
        mysql = connectToMySQL(SCHEMA)

        return render_template('quotes.html', quotes=all_quotes)

@app.route('/add_quote', methods=['POST'])
def add_quote():
    if "user_id" not in session:
        return redirect('/')
    else:
        errors = []
        if len(request.form['author']) < 3:
            errors.append('Name must be at least three characters')
        if len(request.form['content']) < 10:
            errors.append('Quote must be at least ten characters')
        if errors:
            for error in errors:
                flash(error)
            return redirect('/quotes')

        db = connectToMySQL(SCHEMA)
        query = "INSERT INTO quotes (author, content, user_id) VALUES(%(a)s, %(c)s, %(uid)s)"
        data = {
            "a": request.form['author'],
            "c": request.form['content'],
            "uid": session['user_id']
        }
        db.query_db(query, data)
        return redirect('/quotes')

@app.route('/my_account/<id>')
def my_account(id):
    if "user_id" not in session:
        return redirect('/')
    else:
        return render_template('my_account.html')

@app.route('/update/<id>', methods=['POST'])
def update(id):
    if "user_id" not in session:
        return redirect('/')
    else:
        errors = []
        if len(request.form['first_name']) < 3:
            errors.append('First name must be at least two letters')
        if not NAME_REGEX.match(request.form['first_name']):
            errors.append('First name must be letter only')
        if len(request.form['last_name']) < 3:
            errors.append('Last name must be at least two letters')
        if not NAME_REGEX.match(request.form['last_name']):
            errors.append('Last name must be letter only')
        if not EMAIL_REGEX.match(request.form['email']):
            errors.append("Email must be in correct format")
        db = connectToMySQL(SCHEMA)
        query = "SELECT * FROM users WHERE email=%(em)s;"
        data = {
            "em": request.form['email']
        }
        matching_users = db.query_db(query, data)
       
        if matching_users:
            matching_user = matching_users[0]
            if matching_user['email'] == request.form['email']:
                errors.append("Email already in use")

        # User can't change their email?

        if errors:
            for error in errors:
                flash(error)
            return redirect(request.referrer)

        db = connectToMySQL(SCHEMA)
        query = "UPDATE users SET first_name = %(f)s, last_name = %(l)s, email = %(e)s WHERE id = %(id)s"
        data = {
        "f": request.form['first_name'],
        "l": request.form['last_name'],
        "e": request.form['email'],
        'id': int(id)
        }
        db.query_db(query,data)
        return redirect('/quotes')

@app.route('/delete/<id>')
def delete(id):
    if "user_id" not in session:
        return redirect('/')
    else:
        db = connectToMySQL(SCHEMA)
        query = "DELETE FROM quotes WHERE quotes.id = %(qid)s"
        data = {
            'qid': int(id)
        }
        db.query_db(query,data)
        return redirect('/quotes')

@app.route('/user/<id>')
def user(id):
    if "user_id" not in session:
        return redirect('/')
    else: 
        db = connectToMySQL(SCHEMA)
        query = "SELECT * FROM users JOIN quotes ON users.id = quotes.user_id WHERE users.id = %(uid)s;"
        data = {
            'uid': int(id)
        }
        user_quotes = db.query_db(query, data)
        user = user_quotes[0]
        return render_template('user.html', quotes = user_quotes, user=user)

@app.route('/like/<id>')
def like(id):
    if "user_id" not in session:
        return redirect('/')
    else:
        if "quote{{id}}" not in session:
            # Add like to likes table
            db = connectToMySQL(SCHEMA)
            query = "INSERT INTO likes (user_id, quote_id) VALUES(%(uid)s, %(qid)s);"
            data = {
                'uid': session['user_id'],
                'qid': int(id)
            }
            db.query_db(query,data) 

            # Add the quote user liked to the session
            session['quote{{id}}'] = int(id)
            print(session['quote{{id}}'])
            return redirect('/quotes')
        else:
            print(session['quote{{id}}'])
            if session['quote{{id}}'] == True:
                flash("You already liked this quote")
                return redirect('/quotes')
            return redirect('/quotes')
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__=='__main__':
    app.run(debug=True)