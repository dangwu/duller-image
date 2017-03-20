from flask import Flask, request, render_template
from sqlite3 import OperationalError
import string
import sqlite3
import settings
import boto
import random
import time

host = 'http://localhost:5000/'

def current_time():
  return int(time.time())

#Assuming main.db is in your app root folder
def db_check():
    create_image_keys_table = """
        CREATE TABLE image_keys (
        _id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL,
        date INTEGER NOT NULL
        ); """
    with sqlite3.connect('main.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_image_keys_table)
            print("Database tables created")
        except OperationalError as e:
            print e

def random_key():
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))

app = Flask(__name__)

@app.route('/', methods=['GET'])
def upload_file():
    if request.method == 'POST':
        uploadfile = request.files['uploadfile']
        print uploadfile
        s3conn = boto.connect_s3(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
        b = s3conn.get_bucket('dgwu-images')
        k = b.new_key(b)
        image_key = random_key()
        k.key = image_key
        print("Upload file S3 key: " + image_key)
        k.set_metadata("Content-Type", uploadfile.mimetype)
        k.set_contents_from_string(uploadfile.stream.read())
        k.make_public()
        insert_image_to_db(image_key)
    return render_template('upload.html')

@app.route('/images/<image_key>', methods=['GET'])
def view_image(image_key):
    image_url = 'https://s3-us-west-2.amazonaws.com/dgwu-images/' + image_key
    return render_template('image.html', image_url=image_url)

def insert_image_to_db(key):
    with sqlite3.connect('main.db') as conn:
        cursor = conn.cursor()
        insert = """INSERT INTO image_keys (key, date) VALUES ('%s', %s);""" % (key, current_time())
        cursor.execute(insert)
        return

if __name__ == '__main__':
    # This code checks whether database table is created or not
    db_check()
    app.run(debug=True)