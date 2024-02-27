from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
import mysql.connector
from datetime import datetime
import secrets
import base64
from flask import request, jsonify
from jinja2 import Template
from passlib.hash import sha256_crypt
import os

from flask_session import Session

app = Flask(__name__, static_folder='static')

app.config['SESSION_TYPE'] = 'filesystem'  # You can choose a different session type as needed
Session(app)

app.secret_key = 'troll'

# Retrieve database configuration from environment variables
db_host = os.environ.get('DB_HOST', 'localhost')
db_user = os.environ.get('DB_USER', 'root')
db_password = os.environ.get('DB_PASSWORD', 'root')
db_name = os.environ.get('DB_NAME', 'social_media')


# MySQL database connection
db = mysql.connector.connect(
    host = db_host,
    user = db_user,
    password = db_password,
    database = db_name,
    auth_plugin='mysql_native_password'
)

cursor = db.cursor()

def session_print():
    for user in session:
        print("here is list of users " + user)

@app.route("/")
def home():
    session_print()
    logged_in = session.get('logged_in', False)
    return render_template('home.html', logged_in=logged_in)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and sha256_crypt.verify(password, user[3]):  # Verify the hashed password
            session['user_id'] = user[0]
            session['username'] = user[1]  # Assuming user[1] contains the username
            session.permanent = True
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')

            session_print()

            return redirect(url_for('home'))
        else:
            flash('Login failed. Please check your credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        raw_password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        bio = request.form['bio']

        # Hash the password using sha256_crypt from passlib
        hashed_password = sha256_crypt.using(rounds=1000).hash(raw_password)

        # Read the binary data from the profile_pic.png file
        with open('profile_pic.png', 'rb') as f:
            profile_pic_data = f.read()

        # Read the binary data from the background_pic.png file
        with open('background_pic.png', 'rb') as f:
            background_pic_data = f.read()

        cursor = db.cursor()

        # Check if there are any existing users in the table
        cursor.execute("SELECT COUNT(*) FROM Users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            # If no users exist, insert the first user with user_id set to 1
            sql = "INSERT INTO Users (user_id, username, email, password, first_name, last_name, bio, profile_pic, background_pic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = (1, username, email, hashed_password, first_name, last_name, bio, profile_pic_data, background_pic_data)
        else:
            # If users exist, insert a new user without providing the user_id
            sql = "INSERT INTO Users (username, email, password, first_name, last_name, bio, profile_pic, background_pic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            val = (username, email, hashed_password, first_name, last_name, bio, profile_pic_data, background_pic_data)

        cursor.execute(sql, val)
        db.commit()

        return render_template("feed.html")
    else: 
        return render_template("signup.html")


@app.route('/c/<community_name>')
def community(community_name):
    cursor = db.cursor()
    query = "SELECT community_id FROM communities WHERE name = %s"
    cursor.execute(query, (community_name,))
    community_id = cursor.fetchone()[0]
    query = """
        SELECT posts.title, posts.content, posts.date_created, users.username, posts.post_id, posts.post_type, 
            posts.image, COALESCE(SUM(CASE WHEN likes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_likes,
            COALESCE(SUM(CASE WHEN dislikes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_dislikes
        FROM posts
        JOIN users ON posts.user_id = users.user_id
        LEFT JOIN likes ON likes.post_id = posts.post_id
        LEFT JOIN dislikes ON dislikes.post_id = posts.post_id
        WHERE posts.community_id = %s
        GROUP BY posts.post_id
    """
    cursor.execute(query, (community_id,))

    posts = [
        (
            title, 
            content, 
            date_created, 
            username, 
            post_id, 
            post_type, 
            base64.b64encode(image).decode('utf-8') if image is not None else None, 
            num_likes, 
            num_dislikes
        )
        for title, content, date_created, username, post_id, post_type, image, num_likes, num_dislikes in cursor.fetchall()
    ]

    cursor.execute("SELECT c.comment_id, c.post_id, c.user_id, c.content, c.date_created, c.date_modified, u.username FROM comments c JOIN users u ON c.user_id = u.user_id")

    comments = [(comment_id, post_id, user_id, content, date_created, date_modified, username) for (comment_id, post_id, user_id, content, date_created, date_modified, username) in cursor.fetchall()]

    cursor.close()
    return render_template('community.html', posts=posts, comments=comments)



@app.route('/feed')
def feed():
    username = session.get('username', None)
    logged_in = session.get('logged_in', False)
    cursor = db.cursor()
    cursor.execute("""
                    SELECT
    p.title, p.content, p.date_created, u.username, p.post_id, p.post_type, p.image,
    COALESCE(SUM(l.post_id IS NOT NULL), 0) AS num_likes,
    COALESCE(SUM(d.post_id IS NOT NULL), 0) AS num_dislikes
FROM
    posts p
        JOIN
    users u ON p.user_id = u.user_id
        LEFT JOIN
    likes l ON l.post_id = p.post_id
        LEFT JOIN
    dislikes d ON d.post_id = p.post_id
GROUP BY
    1, 2, 3, 4, 5, 6, 7
ORDER BY
    p.date_created DESC;""")

    posts = [
        (
            title, 
            content, 
            date_created, 
            username, 
            post_id, 
            post_type, 
            base64.b64encode(image).decode('utf-8') if image is not None else None, 
            num_likes, 
            num_dislikes
        )
        for title, content, date_created, username, post_id, post_type, image, num_likes, num_dislikes in cursor.fetchall()
    ]

    cursor.execute("SELECT c.comment_id, c.post_id, c.user_id, c.content, c.date_created, c.date_modified, u.username FROM comments c JOIN users u ON c.user_id = u.user_id")

    comments = [(comment_id, post_id, user_id, content, date_created, date_modified, username) for (comment_id, post_id, user_id, content, date_created, date_modified, username) in cursor.fetchall()]

    return render_template('feed.html', posts=posts, comments=comments, logged_in=logged_in, username=username)

# This route handles the POST request for deleting a post
@app.route('/delete-post', methods=['POST'])
def delete_post():
    # Get the post ID from the request body
    post_id = request.json.get('post_id')

    # Delete data from the likes table
    cursor.execute('DELETE FROM likes WHERE post_id = %s', (post_id,))

    # Delete data from the dislikes table
    cursor.execute('DELETE FROM dislikes WHERE post_id = %s', (post_id,))

    # Delete data from the shares table
    cursor.execute('DELETE FROM shares WHERE post_id = %s', (post_id,))

    # Delete the post from the posts table
    cursor.execute('DELETE FROM posts WHERE post_id = %s', (post_id,))

    # Commit the changes to the database
    db.commit()

    # Return a JSON response to indicate success
    return jsonify({'success': True})

@app.route('/like', methods=['POST'])
def like():
    # check if user is logged in
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'You must be logged in to like a post'})

    # get post_id from request form data
    post_id = request.get_json().get('post_id')

    # check if user has already liked the post
    cursor = db.cursor()
    cursor.execute("SELECT like_id FROM likes WHERE user_id = %s AND post_id = %s", (session['user_id'], post_id))
    like_id = cursor.fetchone()

    if like_id:
        # user has already liked the post, so remove the row
        cursor.execute("DELETE FROM likes WHERE like_id = %s", (like_id[0],))
        db.commit()
        return jsonify({'success': True, 'message': 'Post unliked successfully'})


    # check if user has disliked the post
    cursor.execute("SELECT dislike_id FROM dislikes WHERE user_id = %s AND post_id = %s", (session['user_id'], post_id))
    dislike_id = cursor.fetchone()

    if dislike_id:
        # user has disliked the post, so remove the row from the dislike table
        cursor.execute("DELETE FROM dislikes WHERE dislike_id = %s", (dislike_id[0],))

    # insert like record in database
    cursor.execute("INSERT INTO likes (user_id, post_id, date_created) VALUES (%s, %s, %s)",
                   (session['user_id'], post_id, datetime.now()))
    db.commit()

    # fetch sum of likes and dislikes
    cursor.execute("SELECT SUM(CASE WHEN likes.post_id = %s THEN 1 ELSE 0 END) AS likes, SUM(CASE WHEN dislikes.post_id = %s THEN 1 ELSE 0 END) AS dislikes FROM likes LEFT JOIN dislikes ON likes.post_id = dislikes.post_id WHERE likes.post_id = %s",
                (post_id, post_id, post_id))
    result = cursor.fetchone()

    # add likes and dislikes to JSON response
    return jsonify({'success': True, 'message': 'Post liked successfully', 'likes': result[0], 'dislikes': result[1]})

@app.route('/dislike', methods=['POST'])
def dislike():
    # check if user is logged in
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': 'You must be logged in to dislike a post'})

    # get post_id from request form data
    post_id = request.get_json().get('post_id')

    # check if user has already disliked the post
    cursor = db.cursor()
    cursor.execute("SELECT dislike_id FROM dislikes WHERE user_id=%s AND post_id=%s", (session['user_id'], post_id))
    dislike_id = cursor.fetchone()

    if dislike_id:
        # user has already disliked the post, so remove the row
        cursor.execute("DELETE FROM dislikes WHERE dislike_id = %s", (dislike_id[0],))
        db.commit()
    else:
        # check if user has already liked the post
        cursor.execute("SELECT like_id FROM likes WHERE user_id=%s AND post_id=%s", (session['user_id'], post_id))
        like_id = cursor.fetchone()

        if like_id:
            # user has liked the post, so remove the row from the like table
            cursor.execute("DELETE FROM likes WHERE like_id=%s", (like_id[0],))
        # insert dislike record in database
        cursor.execute("INSERT INTO dislikes (user_id, post_id, date_created) VALUES (%s, %s, %s)",
                       (session['user_id'], post_id, datetime.now()))
        db.commit()

    # fetch sum of likes and dislikes
    cursor.execute("SELECT SUM(CASE WHEN likes.post_id = %s THEN 1 ELSE 0 END) AS likes, SUM(CASE WHEN dislikes.post_id = %s THEN 1 ELSE 0 END) AS dislikes FROM likes LEFT JOIN dislikes ON likes.post_id = dislikes.post_id WHERE likes.post_id = %s",
                (post_id, post_id, post_id))
    result = cursor.fetchone()

    # add likes and dislikes to JSON response
    return jsonify({'success': True, 'message': 'Post liked successfully', 'likes': result[0], 'dislikes': result[1]})

@app.route('/createpost', methods=['POST'])
def create_post():
    username = session.get('username', None)
    if username is None:
        return redirect('/login')

    post_type = request.form['post_type']  # Access the value of the hidden input 'post_type'
    
    posting_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    post_date = datetime.now().strftime('%Y-%m-%d')
    user_id = session['user_id']
    
    if post_type == 'Text':
        text_title = request.form['text-title']
        content = request.form['content']
        # Insert post into database
        cursor = db.cursor()
        sql = "INSERT INTO posts (post_id, title, post_type, content, date_created, user_id, post_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (secrets.token_hex(4), text_title, post_type, content, posting_time, user_id, post_date)
        cursor.execute(sql, val)
        db.commit()

    elif post_type == 'Media':
        image_title = request.form['image-title']
        image_file = request.files['image-video-file']
        print(image_file)
        image_file_data = image_file.read()
        # Insert post into database
        cursor = db.cursor()
        sql = "INSERT INTO posts (post_id, title, post_type, image, date_created, user_id, post_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (secrets.token_hex(4), image_title, post_type, image_file_data, posting_time, user_id, post_date)
        cursor.execute(sql, val)
        db.commit()


    return redirect('/feed')

@app.route('/comment/<post_id>', methods=['POST'])
def create_comment(post_id):
    # Extract the fields from the form data
    user_id = session['user_id']
    content = request.form['content']

    # Check if content is empty
    if not content:
        return "You have not entered any text"

    # Generate the comment ID
    comment_id = secrets.token_hex(4)

    # Create a cursor object to execute the SQL query
    cursor = db.cursor()

    # Execute the SQL query to insert the comment into the comments table
    sql = "INSERT INTO comments (comment_id, user_id, post_id, content) VALUES (%s, %s, %s, %s)"
    values = (comment_id, user_id, post_id, content)
    cursor.execute(sql, values)

    # Commit the changes to the database
    db.commit()

    # Return a response indicating success
    return redirect('/feed')


@app.route('/u/<username>')
def profile(username):
    if session.get('logged_in'):
        session['logged_in'] = True
        print("okbubbyretarb")

    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        profile_data = user[7]
        profile_data_base64 = base64.b64encode(profile_data).decode('utf-8') if profile_data else None

        background_data = user[8]
        background_data_base64 = base64.b64encode(background_data).decode('utf-8') if background_data else None

        cursor.execute("""
            SELECT posts.title, posts.content, posts.date_created, users.username, posts.post_id, posts.post_type, posts.image,
                COALESCE(SUM(CASE WHEN likes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_likes,
                COALESCE(SUM(CASE WHEN dislikes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_dislikes
            FROM posts
            JOIN users ON posts.user_id = users.user_id
            LEFT JOIN likes ON likes.post_id = posts.post_id
            LEFT JOIN dislikes ON dislikes.post_id = posts.post_id
            WHERE posts.user_id = (SELECT user_id FROM users WHERE username = %s)
            GROUP BY posts.title, posts.content, posts.date_created, users.username, posts.post_id, posts.post_type, posts.image
            ORDER BY posts.date_created DESC
        """, (username,))
        posts = [
            (
                title, 
                content, 
                date_created, 
                username, 
                post_id, 
                post_type, 
                base64.b64encode(image).decode('utf-8') if image is not None else None, 
                num_likes, 
                num_dislikes
            )
            for title, content, date_created, username, post_id, post_type, image, num_likes, num_dislikes in cursor.fetchall()
        ]

        return render_template('profile.html', username=user[1].capitalize(), first_name=user[4], last_name=user[5], bio=user[6], profile_pic=profile_data_base64, background_pic=background_data_base64, posts=posts)
    else:
        return "User not found"


@app.route('/c/<community_name>')
def community_filtered(community_name):
    cursor = db.cursor()
    query = "SELECT community_id FROM communities WHERE name = %s"
    cursor.execute(query, (community_name,))
    community_id = cursor.fetchone()[0]
    query = "SELECT * FROM posts WHERE community_id = %s"
    cursor.execute(query, (community_id,))
    posts = cursor.fetchall()
    cursor.close()
    return render_template('community.html', posts=posts)


@app.route('/create_community', methods=['GET', 'POST'])
def create_community():
    if request.method == 'POST':
        community_name = request.form['community_name']
        description = request.form['description']
        mycursor = db.cursor()
        sql = "INSERT INTO communities (community_id, name, description) VALUES (%s, %s, %s)"
        val = (secrets.token_hex(4), community_name, description)
        mycursor.execute(sql, val)
        db.commit()
        return redirect(url_for('community', community_name=community_name))
    return redirect(url_for('community', community_name=community_name))

if __name__ == '__main__':
    app.run(debug=True)