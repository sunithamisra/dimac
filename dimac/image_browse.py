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
# This file contains the main DIMAC application.
#

from flask import Flask, render_template, url_for, Response, stream_with_context, request, flash, session, redirect
from forms import ContactForm, SignupForm, SigninForm

#from flask.ext.mail import Message, Mail
from flask_mail import Mail, Message
 
import pytsk3
import os, sys, string, time, re
from mimetypes import MimeTypes
from datetime import date
from dimac_utils import dimac

from dimac import app
import dimac_db
from sqlalchemy import *
from dimac_userlogin_db import db_login, User, dbinit
'''
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relation, sessionmaker
'''


mail = Mail()
image_list = []
file_list_root = []

#FIXME: The following line should be called in __init__.py once.
# Since that is not being recognized here, app.config.from_object is
# added here. This needs to be fixed.
app.config.from_object('dimac_default_settings')
image_dir = app.config['IMAGEDIR']
num_images = 0
image_db = []

@app.route("/")

def dimacBrowseImages():
    global image_dir
    image_index = 0

    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]
    global image_db
    del image_db [:]

    # Create the DB. FIXME: This needs to be called from runserver.py 
    # before calling run. That seems to have some issues. So calling from
    # here for now. Need to fix it.
    session = dimac_db.dimacdb()

    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            print img
            global image_list
            image_list.append(img)

            dm = dimac()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.dimacGetPartInfoForImage(image_path, image_index)
            idb = dimac_db.DimacImages.query.filter_by(image_name=img).first()
            image_db.append(idb)
            ## print("D: IDB: image_index:{}, image_name:{}, acq_date:{}, md5: {}".format(image_index, idb.image_name, idb.acq_date, idb.md5)) 
            image_index +=1
        else:
            continue
  
    # Render the template for main page.
    print 'D: Image_list: ', image_list
    global num_images
    num_images = len(image_list)

    return render_template('fl_temp_ext.html', image_list=image_list, np=dm.num_partitions, image_db=image_db)

def dimacGetImageIndex(image, is_path):
    global image_list
    if (is_path == True):
        image_name = os.path.basename(image_path)
    else:
        image_name = image
    global image_list
    for i in range(0, len(image_list)):
        if image_list[i] == image_name:
            return i
        continue
    else:
        print("Image not found in the list: ", image_name)

#
# Template rendering for Image Listing
#
@app.route('/image/<image_name>')
def image(image_name):
    print("Partitions: Rendering Template with partitions for img: ", image_name)
    num_partitions = dimac.num_partitions_ofimg[str(image_name)]
    part_desc = []
    image_index =  dimacGetImageIndex(image_name, is_path=False)
    for i in range(0, num_partitions):
        ## print("D: part_disk[i={}]={}".format(i, dimac.partDictList[image_index][i]))
        part_desc.append(dimac.partDictList[image_index][i]['desc'])

    return render_template('fl_img_temp_ext.html',
                            image_name=str(image_name),
                            num_partitions=num_partitions,
                            part_desc=part_desc)

@app.route('/image/metadata/<image_name>')
def image_psql(image_name):
    ## print("D: Rendering DB template for image: ", image_name)

    image_index =  dimacGetImageIndex(image_name, is_path=False)

    return render_template("db_image_template.html", 
                           image_name = image_name,
                           image=image_db[image_index])

#
# Template rendering for Directory Listing per partition
#
@app.route('/image/<image_name>/<image_partition>')
def root_directory_list(image_name, image_partition):
    print("Files: Rendering Template with files for partition: ",
                            image_name, image_partition)
    image_index = dimacGetImageIndex(str(image_name), False)
    dm = dimac()
    image_path = image_dir+'/'+image_name
    file_list_root, fs = dm.dimacGenFileList(image_path, image_index,
                                             int(image_partition), '/')
    return render_template('fl_part_temp_ext.html',
                           image_name=str(image_name),
                           partition_num=image_partition,
                           file_list=file_list_root)

# FIXME: Retained for possible later use
def stream_template(template_name, **context):
    print("In stream_template(): ", template_name)
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv

#
# Template rendering when a File is clicked
#
@app.route('/image/<image_name>/<image_partition>', defaults={'path': ''})
@app.route('/image/<image_name>/<image_partition>/<path:path>')

def file_clicked(image_name, image_partition, path):
    print("Files: Rendering Template for subdirectory or contents of a file: ",
          image_name, image_partition, path)
    
    image_index = dimacGetImageIndex(str(image_name), False)
    image_path = image_dir+'/'+image_name

    file_name_list = path.split('/')
    file_name = file_name_list[len(file_name_list)-1]

    print "D: File_path after manipulation = ", path

    # To verify that the file_name exsits, we need the directory where
    # the file sits. That is if tje file name is $Extend/$RmData, we have
    # to look for the file $RmData under the directory $Extend. So we
    # will call the TSK API fs.open_dir with the parent directory
    # ($Extend in this example)
    temp_list = path.split("/")
    temp_list = file_name_list[0:(len(temp_list)-1)]
    parent_dir = '/'.join(temp_list)

    print("D: Invoking TSK API to get files under parent_dir: ", parent_dir)

    # Generate File_list for the parent directory to see if the
    dm = dimac()
    file_list, fs = dm.dimacGenFileList(image_path, image_index,
                                        int(image_partition), parent_dir)

    # Look for file_name in file_list
    for item in file_list:
        ## print("D: item-name={} file_name={} ".format(item['name'], file_name))
        if item['name'] == file_name:
            print("D : File {} Found in the list: ".format(file_name))
            break
    else:
        print("D: File_clicked: File {} not found in file_list".format(file_name))
            
    if item['isdir'] == True:
        # We will send the file_list under this directory to the template.
        # So calling once again the TSK API ipen_dir, with the current
        # directory, this time.
        file_list, fs = dm.dimacGenFileList(image_path, image_index,
                                        int(image_partition), path)

        # Generate the URL to communicate to the template:
        with app.test_request_context():
            url = url_for('file_clicked', image_name=str(image_name), image_partition=image_partition, path=path )

        print (">> Rendering template with URL: ", url)
        return render_template('fl_dir_temp_ext.html',
                   image_name=str(image_name),
                   partition_num=image_partition,
                   path=path,
                   file_list=file_list,
                   url=url)

    else:
        print("Downloading File: ", item['name'])
        # It is an ordinary file
        f = fs.open_meta(inode=item['inode'])
    
        # Read data and store it in a string
        offset = 0
        size = f.info.meta.size
        BUFF_SIZE = 1024 * 1024

        total_data = ""
        while offset < size:
            available_to_read = min(BUFF_SIZE, size - offset)
            data = f.read_random(offset, available_to_read)
            if not data:
                print("Done with reading")
                break

            offset += len(data)
            total_data = total_data+data 
            print "Length OF TOTAL DATA: ", len(total_data)
           

        mime = MimeTypes()
        mime_type, a = mime.guess_type(file_name)
        generator = (cell for row in total_data
                for cell in row)
        return Response(stream_with_context(generator),
                        mimetype=mime_type,
                        headers={"Content-Disposition":
                                    "attachment;filename=" + file_name })
        '''
        return render_template('fl_filecat_temp_ext.html',
        image_name=str(image_name),
        partition_num=image_partition,
        file_name=file_name,
        contents=str(data))
        #contents = data.decode("utf-8"))
        '''
@app.route('/testdb')
def testdb():
    if db_login.session.query("1").from_statement("SELECT 1").all():
        return 'It works.'
    else:
        return 'Something is broken.'

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    ##session = dbinit()
    form = SignupForm()
   
    if request.method == 'POST':
        if form.validate() == False:
            return render_template('fl_signup.html', form=form)
        else:
            newuser = User(form.firstname.data, form.lastname.data, form.email.data, form.password.data)
            db_login.session.add(newuser)
            db_login.session.commit()
       
            session['email'] = newuser.email
       
            ##return "[1] Create a new user [2] sign in the user [3] redirect to the user's profile"
            return redirect(url_for('profile'))
   
    elif request.method == 'GET':
        return render_template('fl_signup.html', form=form)

@app.route('/home')
def home():
    return render_template('profile.html')

@app.route('/about')
def about():
    return render_template('profile.html')

@app.route('/contact')
def contact():
    return render_template('profile.html')

@app.route('/profile')
def profile():
 
  if 'email' not in session:
    return redirect(url_for('signin'))
 
  user = User.query.filter_by(email = session['email']).first()
 
  if user is None:
    return redirect(url_for('signin'))
  else:
    return render_template('profile.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
  form = SigninForm()
   
  if request.method == 'POST':
    if form.validate() == False:
      return render_template('fl_signin.html', form=form)
    else:
      session['email'] = form.email.data
      return redirect(url_for('profile'))
                 
  elif request.method == 'GET':
    return render_template('fl_signin.html', form=form)

@app.route('/signout')
def signout():
 
  if 'email' not in session:
    return redirect(url_for('signin'))
     
  session.pop('email', None)
  return redirect(url_for('home'))

# FIXME: This is never called (since we run runserver.py)
# Remove once confirmed to be deleted
if __name__ == "__main__":
    dm = dimac()
    dimac_db.dimacdb()
    app.run()
