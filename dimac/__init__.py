#!/usr/bin/python
# coding=UTF-8
#
# DIMAC (Disk Image Access for the Web)
# Copyright (C) 2014
# All rights reserved.
#
# This code is distributed under the terms of the GNU General Public
# License, Version 3. See the text file "COPYING" for further details
# about the terms of this license.
#
# This is a python __init__ script to create the app and import the
# main package contents

from flask import Flask
app = Flask(__name__)
import dimac.image_browse

# Config file:

# Adding the following line will allow the econfigurations  to be
# defined in the specified file - dimac_default_settings.py. Doing so
# will add the corresponding elements to the dectionary app.config
# and populate them with the given values. 
# app.config['element_name']

app.config.from_object('dimac_default_settings')

# NOTE: The following line should be uncommented when the env variable
# DIMAC_SETTINGS is set to a file with configs which override the default
# settings specified by dimac_default_settings.py file.
###app.config.from_envvar('DIMAC_SETTINGS')

# FIXME:  The following added from http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-v-user-logins 
import os
from flask.ext.login import LoginManager
from flask.ext.openid import OpenID
from config import basedir

lm = LoginManager()
lm.init_app(app)
oid = OpenID(app, os.path.join(basedir, 'tmp'))

# NOTE: From another site: http://code.tutsplus.com/tutorials/intro-to-flask-signing-in-and-out--net-29982
# FIXME: Config info in app.confic dictionary could be moved to the 
# default config file.
app.secret_key = 'development key'
 
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = 'contact@example.com'
app.config["MAIL_PASSWORD"] = 'your-password'
 
from image_browse import mail
mail.init_app(app)

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://dimac_bcadmin:dimac_bcadmin@localhost/userlogin_db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bcadmin:bcadmin@localhost/userlogin_db'
 
from dimac_userlogin_db import db_login
db_login.init_app(app)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://bcadmin:bcadmin@localhost/userlogin_db'
#dimac_userlogin_db.dbinit()
#db_login.session.commit()
 
#import dimac.routes
import dimac.image_browse
