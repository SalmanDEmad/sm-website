from flask import Flask, render_template, make_response, request, session, redirect, url_for, jsonify, flash
from flask_socketio import join_room, leave_room, send, SocketIO, emit

import json
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

socketio = SocketIO(app)

app.config['SESSION_TYPE'] = 'filesystem'  # You can choose a different session type as needed
Session(app)

app.secret_key = 'troll'

# Retrieve database configuration from environment variables
db_host = os.getenv('DB_HOST', 'localhost')
db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASSWORD', 'root')
db_name = os.getenv('DB_NAME', 'onzugesu_social')


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
        print(user)

def get_latest_update():

    # Fetch the latest update from the updates table
    query = "SELECT update_date, update_time, update_title, update_contents FROM updates ORDER BY update_date DESC, update_time DESC LIMIT 1"
    cursor.execute(query)
    latest_update = cursor.fetchone()

    return latest_update

def update_cookie_and_database():

    # Fetch the latest update from the database
    latest_update = get_latest_update()

    # Convert the date object to a string
    latest_update_date_str = latest_update[0].strftime('%Y-%m-%d')

    # Update the 'update_date' and 'update_time' cookies
    response = make_response(render_template('home.html', updated_cookie='false', latest_update=latest_update))
    response.set_cookie('update_date', latest_update_date_str)
    response.set_cookie('update_time', latest_update[1])

    # Set 'updated_cookie' to 'false'
    response.set_cookie('updated_cookie', 'false')

    return response

def user_identifier(user_id):
    try:
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            return result[0]  # Assuming 'username' is at index 0 in the result tuple
        else:
            return None
    finally:
        cursor.close()

@app.route("/notif")
def notif():
    cursor.execute("select * from notifications")
    notifications = cursor.fetchall()
    receiver = session.get()
    for notification in notifications:
        if notification:
            sender_name = user_identifier(notification[0])
            return render_template("notif.html", notifications = notifications, sender_name = sender_name)
    return render_template("notif.html")

@app.route("/")
def home():
    session_print()
    # Check if cookies exist
    updated_cookie = request.cookies.get('updated_cookie', 'false')
    update_date_cookie = request.cookies.get('update_date')
    
    # Get the latest update from the database
    latest_update = get_latest_update()
    print(latest_update)

    # Convert the date object to a string
    latest_update_date_str = latest_update[0].strftime('%Y-%m-%d')

    user = session
    print(session)

    user_id_cookie = request.cookies.get('user_id')
    user_name_cookie = request.cookies.get('username')

    user_id = session.get('user_id')
    username = session.get('username')
    user_data = [user_id, username]

    page = "home"

    if user_id_cookie is None:
        if user_name_cookie is not None:
            response = cookie_check(user_data)
            return response
        else:
            flash('Log in to see update!', 'Danger')

    # Check if the 'update_date' cookie exists and if its value is less than the latest update
    if (updated_cookie == 'false' and
            update_date_cookie and
            update_date_cookie < latest_update_date_str):
        # Update the cookies and set 'updated_cookie' to 'false'
        return update_cookie_and_database()
    else:
        # Cookies are up-to-date, set 'updated_cookie' to 'false'
        return render_template('home.html', page=page, updated_cookie='false', latest_update=latest_update)

def is_admin(username):
    # Check if the user has the 'admin' role in the database
    # Execute the SQL query
    query = "SELECT role FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()

    # Check if the role is 'admin'
    return result and result[0] == 'admin'


def cookie_check(user):
    # Check if cookies already exist
    user_id_cookie = request.cookies.get('user_id')
    username_cookie = request.cookies.get('username')
    updates_cookie = request.cookies.get('updates')

    if updates_cookie is None:
        response = make_response(redirect(url_for('home')))

        response.set_cookie('username', str(user[1]))

        response.set_cookie('user_id', str(user[0]))
        
        # Set 'update_cookie' cookie
        response.set_cookie('updated_cookie', 'false')
        
        # Set 'update_date' cookie
        response.set_cookie('update_date', "None")

        # Set 'update_time' cookie
        response.set_cookie('update_time', "None")

    return response

@app.route('/add_update', methods=['POST'])
def add_update():
    # Get data from the form
    update_title = request.form['update_title']
    update_contents = request.form['update_contents']

    # Generate current date in dd/mm/yyyy, hh:mm format
    update_date = datetime.now().strftime('%Y-%m-%d')
    update_time = datetime.now().strftime('%H:%M')

    # Insert data into the updates table
    query = "INSERT INTO updates (update_title, update_contents, update_date, update_time) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (update_title, update_contents, update_date, update_time))

    # Commit changes and close the connection
    db.commit()

    return render_template('dashboard.html')

@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Check if the user has the 'admin' role in the database
    if is_admin(session['username']):
        # Render the dashboard template
        return render_template('dashboard.html')
    else:
        # Return an error message or redirect to a different page
        return "Error: Access denied. You are not an admin."

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and sha256_crypt.verify(password, user[3]):  # Verify the hashed password
            response = cookie_check(user)
            session['user_id'] = user[0]
            session['username'] = user[1]  # Assuming user[1] contains the username
            session.permanent = True
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')

            session_print()

            return response
        else:
            flash('Login failed. Please check your credentials.', 'danger')

    return render_template('login.html')

@app.route("/suggestions")
def suggestions():
    return render_template('suggestions.html')

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
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            # If no users exist, insert the first user with user_id set to 1
            sql = "INSERT INTO users (user_id, username, email, password, first_name, last_name, bio, profile_pic, background_pic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            val = (1, username, email, hashed_password, first_name, last_name, bio, profile_pic_data, background_pic_data)
        else:
            # If users exist, insert a new user without providing the user_id
            sql = "INSERT INTO users (username, email, password, first_name, last_name, bio, profile_pic, background_pic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            val = (username, email, hashed_password, first_name, last_name, bio, profile_pic_data, background_pic_data)

        cursor.execute(sql, val)
        db.commit()

        return render_template("feed.html")
    else: 
        return render_template("signup.html")


@app.route('/c/<community_name>')
def community(community_name):
    cursor = db.cursor()
    query = """
                SELECT
                    posts.title,
                    MAX(posts.content) as content,
                    MAX(posts.date_created) as date_created,
                    MAX(users.username) as username,
                    posts.post_id,
                    MAX(posts.post_type) as post_type,
                    MAX(posts.image) as image,
                    COALESCE(SUM(CASE WHEN likes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_likes,
                    COALESCE(SUM(CASE WHEN dislikes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_dislikes
                FROM posts
                JOIN users ON posts.user_id = users.user_id
                LEFT JOIN likes ON likes.post_id = posts.post_id
                LEFT JOIN dislikes ON dislikes.post_id = posts.post_id
                WHERE posts.community_name = %s
                GROUP BY posts.post_id, posts.title;
    """
    cursor.execute(query, (community_name,))

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
            JOIN users u ON p.user_id = u.user_id
            LEFT JOIN likes l ON l.post_id = p.post_id
            LEFT JOIN dislikes d ON d.post_id = p.post_id
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
            num_dislikes  # Assuming you have a get_comments_for_post function
        )
        for title, content, date_created, username, post_id, post_type, image, num_likes, num_dislikes in cursor.fetchall()
    ]

    cursor.execute("select * from comments")
    comments = cursor.fetchall()

    for i, comment in enumerate(comments):
        user_id = comment[1]

        # Fetch the username from the 'users' table
        cursor.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()

        # Check if a matching user is found
        if user_data:
            username = user_data[0]
            # Update the second element of the tuple with the username
            comments[i] = (comment[0], username, *comment[2:])

    return render_template('feed.html', posts=posts, logged_in=logged_in, username=username, comments = comments)


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
    print("test")
    # Extract the fields from the form data
    user_id = session['user_id']
    content = request.form['content']
    comment_type = "parent"

    # Check if content is empty
    if not content:
        return "You have not entered any text"

    # Generate the comment ID
    comment_id = secrets.token_hex(4)

    # Create a cursor object to execute the SQL query
    cursor = db.cursor()

    # Execute the SQL query to insert the comment into the comments table
    sql = "INSERT INTO comments (comment_id, user_id, post_id, content, comment_type) VALUES (%s, %s, %s, %s, %s)"
    values = (comment_id, user_id, post_id, content, comment_type)
    cursor.execute(sql, values)

    # Commit the changes to the database
    db.commit()

    # Return a response indicating success
    return redirect('/feed')

@app.route('/reply/<comment_id>', methods=['POST'])
def create_reply(comment_id):

    print('rape')
    # Extract the fields from the form data
    user_id = session['user_id']
    content = request.form['content']
    post_id = request.form['post_id']
    print(post_id)

    comment_type = "reply"

    # Check if content is empty
    if not content:
        return "You have not entered any text"

    # Generate the comment ID
    reply_id = secrets.token_hex(4)

    # Execute the SQL query to get the parent comment's comment_id and comment_type
    sql_get_parent_comment = "SELECT comment_id, comment_type FROM comments WHERE comment_id = %s"
    cursor.execute(sql_get_parent_comment, (comment_id,))
    parent_comment_data = cursor.fetchone()

    # Check if the parent comment exists
    if not parent_comment_data:
        return "Parent comment not found"

    parent_comment_id, parent_comment_type = parent_comment_data

    # Determine the parent_comment based on the comment_type
    if parent_comment_type == "parent":
        parent_comment = comment_id
    else:
        parent_comment = parent_comment_id

    # Execute the SQL query to insert the reply into the comments table
    sql = "INSERT INTO comments (comment_id, user_id, post_id, content, comment_type, replied_comment, parent_comment) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    values = (reply_id, user_id, post_id, content, comment_type, comment_id, parent_comment)
    cursor.execute(sql, values)

    # Commit the changes to the database
    db.commit()

    # Return a response indicating success
    return redirect('/feed')

def check_friend_request_status(session_user_id, other_user_id):
    # Check if the session user sent a friend request to the other user
    cursor.execute("SELECT * FROM communication WHERE requestor_id = %s AND receiver_id = %s", (session_user_id, other_user_id))
    sent_request = cursor.fetchone()
    print("Sent Request:", sent_request)

    # Check if the session user received a friend request from the other user
    cursor.execute("SELECT * FROM communication WHERE requestor_id = %s AND receiver_id = %s", (other_user_id, session_user_id))
    received_request = cursor.fetchone()
    print("Received Request:", received_request)

    if sent_request:
        if sent_request[3]:  # Assuming 'request_status' is at index 3
            sent_status = "Accepted"
        else:
            sent_status = "Pending"
        print("Sent Status:", sent_status)
        return sent_status
    else:
        if received_request:
            if received_request[3]:  # Assuming 'request_status' is at index 3
                received_status = "Accepted"
            else:
                received_status = "Accept it"
            print("Received Status:", received_status)
            return received_status

@app.route('/u/<username>')
def profile(username):
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

        if session.get('logged_in'):
            session['logged_in'] = True
            if username != session.get(username):
                request_status = check_friend_request_status(session.get('user_id'), user[0])
                print(request)

        return render_template('profile.html', request_status=request_status, user_id=user[0], username=user[1].capitalize(), first_name=user[4], last_name=user[5], bio=user[6], profile_pic=profile_data_base64, background_pic=background_data_base64, posts=posts)
    else:
        return "User not found"


def list_of_communities():
    cursor.execute("select name from communities")
    community_name = cursor.fetchone()[0]

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

def send_to_notifs(sender, receiver, notification_type, notif_content, datetime):
    # Add to notifications in database
    cursor.execute("INSERT INTO notifications (sender_id, receiver_id, notification_type, notification_content, created_at) VALUES (%s,%s,%s,%s,%s)", (sender, receiver, notification_type, notif_content, datetime))
    db.commit()

@app.route('/send_request', methods=['POST'])
def friendRequest():
    sender_id = session.get('user_id')
    receiver_id = request.form['recipient']
    current_datetime = datetime.now()
    cursor.execute("INSERT INTO communication (requestor_id, receiver_id, request_datetime, request_status, room_number) VALUES (%s, %s, %s, %s, %s)", (sender_id, receiver_id, current_datetime, False, 0))
    db.commit()
    notif_type = "Friend Request"
    notif_content = " wants to be friends with you."
    send_to_notifs(sender_id, receiver_id, notif_type, notif_content, current_datetime)
    return "based"

@app.route('/message')
def message():
    return  render_template("message.html")

@socketio.on('my event')
def handle_my_event(data):
    print('Data from client:', data)

@socketio.on('message')
def handle_message(data):
    user=session.get('username')
    if user is not None:
        content = data['content']
        print(user)
        # Emit the message back to the client
        socketio.send({'content': content, 'user': user})
    else:
        # Emit an error message back to the client
        emit('error', {'message': 'Please log in'})

if __name__ == '__main__':
    socketio.run(app, debug=True)