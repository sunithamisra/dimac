from flask import Flask, render_template, url_for, Response
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug import generate_password_hash, check_password_hash

#app = Flask(__name__)
#db_login = SQLAlchemy(app)
 
db_login = SQLAlchemy()
 
class User(db_login.Model):
  __tablename__ = 'users'
  uid = db_login.Column(db_login.Integer, primary_key = True)
  firstname = db_login.Column(db_login.String(100))
  lastname = db_login.Column(db_login.String(100))
  email = db_login.Column(db_login.String(120), unique=True)
  pwdhash = db_login.Column(db_login.String(54))
   
  def __init__(self, firstname, lastname, email, password):
    self.firstname = firstname.title()
    self.lastname = lastname.title()
    self.email = email.lower()
    self.set_password(password)
     
  def set_password(self, password):
    print "SSSSSSSPPPPPPPPPPP"
    self.pwdhash = generate_password_hash(password)
   
  def check_password(self, password):
    return check_password_hash(self.pwdhash, password)

def dbinit(): 
   print(">>> Creating tables ")
   #db_login.drop_all()
   #db_login.create_all()
