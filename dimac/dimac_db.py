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
# This file contains DIMAC database support.
#


from flask import Flask, render_template, url_for, Response
from flask.ext.sqlalchemy import SQLAlchemy
from dimac_default_settings import *
from dimac_userlogin_db import db_login

app = Flask(__name__)
###db = SQLAlchemy(app)
##db_login = SQLAlchemy(app)
#app.config.from_pyfile(config.py) 
# FIXME: The above line gives error - so added the following 2 lines for now
#SQLALCHEMY_DATABASE_URI = "postgresql://bcadmin:bcadmin@localhost/DimacImages"
#db_uri = app.config['SQLALCHEMY_DATABASE_URI']
#db_uri = "postgresql://bcadmin:bcadmin@localhost/DimacImages"

import os
import dimac_utils
import xml.etree.ElementTree as ET

# FIXME: The following two lines for configuration are supposed to be
# in __init__.py. But somehow they are not getting picked up here. So
# added them here. Need to move it back there so these can be used by
# all the files.

app.config.from_object('dimac_default_settings')
#app.config.from_envvar('DIMAC_SETTINGS')

image_list = []
image_dir = app.config['IMAGEDIR']

#
# dimacGetXmlInfo: Extracts information from the dfxml file
#
def dimacGetXmlInfo(xmlfile):
    result = ""
    try:
        tree = ET.parse( xmlfile )
    except IOError, e:
        print "Failure Parsing %s: %s" % (xmlfile, e)

    dbrec = dict()
    root = tree.getroot() # root node
    for child in root:
        if ( child.tag == 'ewfinfo' ):
            ewfinfo = child
            for echild in ewfinfo:
                if (echild.tag == 'acquiry_information'):
                    acqinfo = echild 
                    for acq_child in acqinfo:
                        if (acq_child.tag == 'acquisition_date'):
                            dbrec['acq_date'] = acq_child.text
                        elif (acq_child.tag == 'system_date'):
                            dbrec['sys_date'] = acq_child.text
                        elif (acq_child.tag == 'acquisition_system'):
                            dbrec['os'] = acq_child.text
            
                elif (echild.tag == 'ewf_information'):
                    ewf_info = echild 
                    for ewfi_child in ewf_info:
                        if (ewfi_child.tag == 'file_format'):
                            dbrec['file_format'] = ewfi_child.text
                elif (echild.tag == 'media_information'):
                    media_info = echild
                    for minfo_child in media_info:
                        if (minfo_child.tag == 'media_type'):
                            dbrec['media_type'] = minfo_child.text
                        elif (minfo_child.tag == 'is_physical'):
                            dbrec['is_physical'] = minfo_child.text
                        elif (minfo_child.tag == 'bytes_per_sector'):
                            dbrec['bps'] = minfo_child.text
                        elif (minfo_child.tag == 'media_size'):
                            dbrec['media_size'] = minfo_child.text
                elif (echild.tag == 'hashdigest'):
                    hash_type = echild.text  ## FIXME
                    print("HASH TYPE: ", hash_type)
                    dbrec['md5'] = hash_type 
 
    return dbrec

#
# dimacGetDfxmlInfo: Extracts information from the dfxml file
#
from StringIO import StringIO
def dimacGetDfxmlInfo(dfxmlfile, img):
    result = ""
    try:
        tree = ET.parse( dfxmlfile )
    except IOError, e:
        print "Failure Parsing %s: %s" % (dxmlfile, e)

    d_dbrec = dict()
    root = tree.getroot() # root node

    '''
    print("D: Root: ", root) 
    print("D: Root-TAG: ", root.tag) 
    print("D: Root Attrib: ", root.attrib)
    '''

    for child in root:
        #print("D: Childtag: ", child.tag, child.attrib)
        if child.tag == 'volume':
            volume = child
            for vchild in volume:
                ## FIXME: The following check was commented out
                if (vchild.tag == 'partition offset'):
                    d_dbrec['partition_offset'] = vchild.text
                elif vchild.tag == 'sector_size':
                    d_dbrec['sector_size'] = vchild.text

                if vchild.tag == 'fileobject':
                    fileobject = vchild
                    for fo_child in fileobject:
                        if fo_child.tag == 'parent_object':
                            parent_object = fo_child
                            for po_child in parent_object:
                                if po_child.tag == 'inode':
                                    d_dbrec['p_inode'] = po_child.text
                        else:
                            # print("D: FileObject: ", fo_child.tag, fo_child.text)
                            d_dbrec[fo_child.tag] = fo_child.text
                    d_dbrec['image_name'] = img
                    dimacDfxmlDbSessionAdd(d_dbrec)
                else:
                   # print("Outside FileObject: ", vchild.tag, vchild.text)
                   d_dbrec[vchild.tag] = vchild.text
    return d_dbrec


def dbBrowseImages():
    global image_dir
    image_index = 0

    # Since image_list is declared globally, empty it before populating
    global image_list
    del image_list[:]

    for img in os.listdir(image_dir):
        if img.endswith(".E01") or img.endswith(".AFF"):
            print "\n Image: ", img
            ## global image_list
            image_list.append(img)

            # FIXME: Partition info will be added to the metadata info 
            # Till then the following three lines are not necessary.
            dm = dimac_utils.dimac()
            image_path = image_dir+'/'+img
            dm.num_partitions = dm.dimacGetNumPartsForImage(image_path, image_index)
            xmlfile = dm.dbGetImageInfoXml(image_path)
            if (xmlfile == None):
                print("No XML file generated for image info. Returning")
                return
            print("XML File {} generated for image {}".format(xmlfile, img))

            dfxmlfile = dm.dbGetInfoFromDfxml(image_path)
            if (dfxmlfile == None):
                print("No DFXML file generated for image info. Returning")
                return
            print("DFXML File {} generated for image {}".format(dfxmlfile, img))

            # Read the XML file and populate the record for this image
            dbrec = dimacGetXmlInfo(xmlfile)
            d_dbrec = dimacGetDfxmlInfo(dfxmlfile, img)

            ## print("D: Adding dbrec session to the DB: ", dbrec)
            dbrec['image_name'] = img

            # Populate the db:
            # Add the created record/session to the DB
            dimacDbSessionAdd(dbrec)

            image_index +=1
        else:
            continue
    #db.session.commit()
  
    print 'D: Image_list: ', image_list

class DimacImages(db_login.Model):
    __tablename__ = 'dimac_images'
    image_index = db_login.Column(db_login.Integer, primary_key=True)
    image_name = db_login.Column(db_login.String(60) )
    acq_date = db_login.Column(db_login.String(80))
    sys_date = db_login.Column(db_login.String(80))
    os = db_login.Column(db_login.String(255))
    file_format = db_login.Column(db_login.String(100))
    media_type = db_login.Column(db_login.String(100))
    is_physical = db_login.Column(db_login.String(10))
    bps = db_login.Column(db_login.Integer)
    media_size = db_login.Column(db_login.String(100))
    md5 = db_login.Column(db_login.String(255))


    def __init__(self, image_name = None, acq_date = None, sys_date = None,
os = None, file_format = None, media_type = None, is_physical = None, 
bps = None, media_size = None, md5 = None):
        self.image_name = image_name
        self.acq_date = acq_date
        self.sys_date = sys_date
        self.os = os
        self.file_format = file_format
        self.media_type = media_type
        self.is_physical = is_physical
        self.bps = bps
        self.media_size = media_size
        self.md5 = md5

class DimacDfxmlInfo(db_login.Model):
    __tablename__ = 'dimac_dfxmlinfo'
    image_index = db_login.Column(db_login.Integer, primary_key=True)
    image_name = db_login.Column(db_login.String(60))
    partition_offset = db_login.Column(db_login.BigInteger)
    sector_size = db_login.Column(db_login.Integer)
    block_size = db_login.Column(db_login.Integer)
    ftype = db_login.Column(db_login.Integer)
    ftype_str = db_login.Column(db_login.String(80))
    block_count = db_login.Column(db_login.Integer)
    first_block = db_login.Column(db_login.Integer)
    last_block = db_login.Column(db_login.Integer)
    fo_parent_inode = db_login.Column(db_login.Integer)
    fo_filename = db_login.Column(db_login.String(100))
    fo_partition = db_login.Column(db_login.Integer)
    fo_id = db_login.Column(db_login.Integer)
    fo_name_type = db_login.Column(db_login.String(1))
    fo_filesize = db_login.Column(db_login.Integer)
    fo_alloc = db_login.Column(db_login.Integer)
    fo_used = db_login.Column(db_login.Integer)
    fo_inode = db_login.Column(db_login.Integer)
    fo_meta_type = db_login.Column(db_login.Integer)
    fo_mode = db_login.Column(db_login.Integer)
    fo_nlink = db_login.Column(db_login.Integer)
    fo_uid = db_login.Column(db_login.BigInteger)
    fo_gid = db_login.Column(db_login.Integer)
    fo_mtime = db_login.Column(db_login.String(100))

    def __init__(self, image_name = None, partition_offset = None,
sector_size = None, block_size = None, ftype = None, ftype_str = None,
block_count = None, first_block = None, last_block = None,
fo_parent_inode = None, fo_filename = None, fo_partition = None,
fo_id = None, fo_name_type = None, fo_filesize = None, fo_alloc = None,
fo_used = None, fo_inode = None, fo_meta_type = None, fo_mode = None,
fo_nlink = None, fo_uid = None, fo_gid = None, fo_mtime = None):
        self.image_name = image_name
        self.partition_offset = partition_offset
        self.sector_size = sector_size
        self.block_size = block_size
        self.ftype = ftype
        self.ftype_str = ftype_str 
        self.block_count = block_count
        self.first_block = first_block
        self.last_block = last_block
        self.fo_parent_inode = fo_parent_inode
        self.fo_filename = fo_filename
        self.fo_partition = fo_partition
        self.fo_id = fo_id
        self.fo_name_type = fo_name_type
        self.fo_filesize = fo_filesize
        self.fo_alloc = fo_alloc
        self.fo_used = fo_used
        self.fo_inode = fo_inode
        self.fo_meta_type = fo_meta_type
        self.fo_mode = fo_mode
        self.fo_nlink = fo_nlink
        self.fo_uid = fo_uid
        self.fo_gid = fo_gid
        self.fo_mtime = fo_mtime


def dimacDbSessionAdd(dbrec):
    db_login.session.add(DimacImages(image_name=dbrec['image_name'], 
                         acq_date=dbrec['acq_date'],
                         sys_date=dbrec['sys_date'],
                         os=dbrec['os'], file_format=dbrec['file_format'],
                         media_type=dbrec['media_type'],
                         is_physical=dbrec['is_physical'],
                         bps = dbrec['bps'],
                         media_size = dbrec['media_size'],
                         md5 = dbrec['md5'])) 
    db_login.session.commit()

def dimacDfxmlDbSessionAdd(d_dbrec):
    db_login.session.add(DimacDfxmlInfo(image_name=d_dbrec['image_name'],
                   partition_offset=d_dbrec['partition_offset'],
                   ##sector_size=d_dbrec['sector_size'],
                   block_size=d_dbrec['block_size'],
                   ftype=d_dbrec['ftype'],
                   ftype_str=d_dbrec['ftype_str'],
                   block_count=d_dbrec['block_count'],
                   first_block=d_dbrec['first_block'],
                   last_block=d_dbrec['last_block'],
                   # FIXME: Find a way to add multiple directory levels
                   # like parent inode: Commented for now
                   #fo_parent_inode=d_dbrec['parent_inode'],
                   fo_filename=d_dbrec['filename'],
                   fo_partition=d_dbrec['partition'],
                   fo_id=d_dbrec['id'],
                   fo_name_type=d_dbrec['name_type'],
                   fo_filesize=d_dbrec['filesize'],
                   fo_alloc=d_dbrec['alloc'],
                   fo_used=d_dbrec['used'],
                   fo_inode=d_dbrec['inode'],
                   fo_meta_type=d_dbrec['meta_type'],
                   fo_mode=d_dbrec['mode'],
                   fo_nlink=d_dbrec['nlink'],
                   fo_uid=d_dbrec['uid'],
                   fo_gid=d_dbrec['gid'],
                   fo_mtime=d_dbrec['mtime']))
    db_login.session.commit()

    
def dbinit(): 
   print(">>> Creating tables ")
   db_login.drop_all() ## FIXME: TEMP
   db_login.create_all()

def dimacdb():
    dbinit()
    dbBrowseImages()

## FIXME: Just for testing - Will be removed
@app.route('/')
def index(image_name = None):
    '''
    # Hardcode the image for now: FIXME
    image_name = "charlie-work-usb-2009-12-11.E01"
    #image = DimacImages.query.filter_by(image_name=image_name).first()
    print("Querying the DB ...")
    #image = bcdb.query.filter_by(image_name=image_name).first()
    image = bcdb.query.filter_by(image_name=image_name).first()
    print("img", image.acq_date)
    return render_template("db_temp.html", image=image)
    '''

'''
if __name__=="__main__":
    db = SQLAlchemy(app)
    dbinit()
    dbBrowseImages()
    app.run(debug=True, host="0.0.0.0", port=8888)
'''
    
