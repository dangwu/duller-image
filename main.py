from flask import Flask, redirect, request, render_template
from sqlite3 import OperationalError
import string
import sqlite3
import settings
import boto
import random
import time

host = 'http://localhost:5000/'
database_name = 'asfih.db'
s3_bucket_name = 'afsim-img'

def current_time():
  return int(time.time())

def db_check():
    create_images_table = """
        CREATE TABLE images (
        _id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        date INTEGER NOT NULL,
        views INTEGER DEFAULT 0
        ); """
    create_images_key_index = """
        CREATE INDEX idx_images_key ON images(key);
    """
    create_images_date_index = """
        CREATE INDEX idx_images_date ON images(date);
    """
    with sqlite3.connect(database_name) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_images_table)
            cursor.execute(create_images_key_index)
            cursor.execute(create_images_date_index)
            print("Database tables and indices created")
        except OperationalError as e:
            print e

# Generate "random" alphanumeric key to use for an image.
def random_key():
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Get file from input form for upload
        uploadfile = request.files['uploadfile']

        # Connect to S3
        s3conn = boto.connect_s3(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        b = s3conn.get_bucket(s3_bucket_name)
        k = b.new_key(b)

        # Generate random key to assign to image
        image_key = random_key()
        k.key = image_key

        # Upload to S3
        k.set_metadata("Content-Type", uploadfile.mimetype)
        k.set_contents_from_string(uploadfile.stream.read())
        k.make_public()

        # Save image to database
        insert_image_to_db(image_key)

        # Redirect to display image to user
        print('Image uploaded - redirecting to i/%s' % image_key)
        return redirect('i/%s' % image_key)

    return render_template('upload.html')

@app.route('/i/<image_key>', methods=['GET'])
def view_image(image_key):
    update_image_view_count(image_key)
    return render_template('image.html', image_url=image_s3_url(image_key))

# Insert image metadata to database
def insert_image_to_db(image_key):
    with sqlite3.connect(database_name) as conn:
        cursor = conn.cursor()
        insert = """INSERT INTO images (key, date, views) VALUES ('%s', %s, %d);""" % (image_key, current_time(), 0)
        cursor.execute(insert)
        return

# Increment view count for image
def update_image_view_count(image_key):
    with sqlite3.connect(database_name) as conn:
        cursor = conn.cursor()
        update = """UPDATE images SET views = views + 1 WHERE key = '%s' """ % image_key
        cursor.execute(update)
        return

# Get S3 url for image
def image_s3_url(image_key):
    return 'http://%s.s3.amazonaws.com/%s' % (s3_bucket_name, image_key)

if __name__ == '__main__':
    # This code checks whether database table is created or not
    db_check()
    app.run(debug=True)