from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import mysql.connector
from datetime import datetime
import secrets
import base64
from flask import request, jsonify
from jinja2 import Template

app = Flask(__name__, static_folder='static')

app.secret_key = 'troll'

# MySQL database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
)

cursor = db.cursor()
# create the database if it does not exist
cursor.execute("CREATE DATABASE IF NOT EXISTS social_media")
cursor.execute("USE social_media")

@app.route('/')
def run():
    # create a cursor object
    cursor = db.cursor()

    # execute the CREATE TABLE queries
    queries = [
    "CREATE TABLE IF NOT EXISTS `comments` (comment_id char(8) NOT NULL,user_id int NOT NULL,post_id char(8),content text,date_created datetime DEFAULT CURRENT_TIMESTAMP,date_modified datetime DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `communities` (community_id char(10) NOT NULL, name varchar(30), description varchar(500), PRIMARY KEY (community_id), INDEX (community_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `dislikes` (dislike_id int NOT NULL,user_id int NOT NULL,post_id char(10),date_created datetime DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `followers` (follower_id int NOT NULL,user_id int NOT NULL,follower_user_id int NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `likes` (like_id int NOT NULL,user_id int NOT NULL,post_id char(8),date_created datetime DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `notifications` (notification_id int NOT NULL,user_id int NOT NULL,type varchar(50),content text,date_created datetime DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `posts` (post_id char(8) NOT NULL,user_id int NOT NULL,content text,image longblob,date_created datetime DEFAULT CURRENT_TIMESTAMP,post_type varchar(255) NOT NULL,title varchar(255) NOT NULL,post_date datetime NOT NULL,community_id char(10),FOREIGN KEY (community_id) REFERENCES communities (community_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `shares` (share_id int NOT NULL,user_id int NOT NULL,post_id char(8),shared_to_user_id int NOT NULL,date_created datetime DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `users` (user_id int PRIMARY KEY NOT NULL,username varchar(50) NOT NULL,email varchar(50) NOT NULL,password varchar(255) NOT NULL,first_name varchar(50),last_name varchar(50),bio text,profile_pic longblob,background_pic longblob) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    "CREATE TABLE IF NOT EXISTS `subscriptions` (user_id int,community_id char(10), FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE, FOREIGN KEY (community_id) REFERENCES communities (community_id) ON DELETE CASCADE ON UPDATE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;",
    ]

    for query in queries:
        cursor.execute(query)
        cursor.close()
        cursor = db.cursor()


    # commit changes and close the connection
    db.commit()

    logged_in = session.get('logged_in', False)
    return render_template('home.html', logged_in=logged_in)


@app.route("/home")
def home():
    logged_in = session.get('logged_in', False)
    return render_template('home.html', logged_in=logged_in)

@app.route("/base")
def base():
    return render_template("base.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        bio = request.form['bio']

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
            val = (1, username, email, password, first_name, last_name, bio, profile_pic_data, background_pic_data)
        else:
            # If users exist, insert a new user without providing the user_id
            sql = "INSERT INTO Users (username, email, password, first_name, last_name, bio, profile_pic, background_pic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            val = (username, email, password, first_name, last_name, bio, profile_pic_data, background_pic_data)
        (username, email, password, first_name, last_name, bio, profile_pic_data, background_pic_data)

        cursor.execute(sql, val)
        db.commit()

        return render_template("feed.html")


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
                    SELECT posts.title, posts.content, posts.date_created, users.username, posts.post_id, posts.post_type, posts.image,
                        COALESCE(SUM(CASE WHEN likes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_likes,
                        COALESCE(SUM(CASE WHEN dislikes.post_id = posts.post_id THEN 1 ELSE 0 END), 0) AS num_dislikes
                    FROM posts
                    JOIN users ON posts.user_id = users.user_id
                    LEFT JOIN likes ON likes.post_id = posts.post_id
                    LEFT JOIN dislikes ON dislikes.post_id = posts.post_id
                    GROUP BY posts.title, posts.content, posts.date_created, users.username, posts.post_id, posts.post_type, posts.image

    """)

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

    # Get data from form submission
    text_title = request.form['text-title']
    image_title = request.form['image-title']
    post_type = request.form['post_type']
    posting_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    post_date = datetime.now().strftime('%Y-%m-%d')
    user_id = session['user_id']
    
    if post_type == 'Text':
        content = request.form['content']
        # Insert post into database
        cursor = db.cursor()
        sql = "INSERT INTO posts (post_id, title, post_type, content, date_created, user_id, post_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (secrets.token_hex(4), text_title, post_type, content, posting_time, user_id, post_date)
        cursor.execute(sql, val)
        db.commit()

    elif post_type == 'Image':
        image_file = request.files['image-video-file']
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

@app.route('/validatelogin', methods=['GET', 'POST'])
def validatelogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = db.cursor()
        sql = "SELECT * FROM users WHERE username=%s AND password=%s"
        val = (username, password)
        cursor.execute(sql, val)
        user = cursor.fetchone()
        cursor.execute("SELECT user_id FROM users WHERE username=%s AND password=%s", (username, password))
        result = cursor.fetchone()

        if result is not None:
            user_id = result[0]
        else:
            return "Invalid credentials"


        if user:
            # User exists and credentials are correct
            # You can set a session variable or cookie to keep the user logged in
            # Redirect the user to the home page or another protected page
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user_id
            return redirect(url_for('home'))
        else:
            # User does not exist or credentials are incorrect
            # Redirect the user to the login page with an error message
            return "Invalid credentials"
    return render_template('login.html')

