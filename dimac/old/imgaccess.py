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
# This is the main disk image access package script

from dimac import app
from flask import render_template
import pytsk3

@app.route("/")
@app.route("/<retstr>")

# Sample hello world for testing
# def hello():
#     return "Hello World!"

def tsktest(retstr=None):
    # Step 1: get an IMG_INFO object
    img = pytsk3.Img_Info("/home/bcadmin/Desktop/jo-work-usb-2009-12-11.E01")

    ## Step 2: get a Volume_Info object
    volume = pytsk3.Volume_Info(img)

    ## Step 3: Iterate over all the partitions.
    retstr = 'PARTITIONS ON THIS DISK:' + '\<br\>'
    for part in volume:
        #print part.addr, part.desc, part.start, part.len
        retstr += str(part.addr) + ' ' + str(part.desc) + ' ' + str(part.start) + ' ' + str(part.len) + '</br>'

    retstr += '</br>' + 'Contents of the root directory:' + '</br>'

    ## Now, a hack to recognize the start location. Do NOT use this
    ## code in production. It's just a demo.
    fs = pytsk3.FS_Info(img, offset = 63 * 512)

    for directory_entry in fs.open_dir(path="/"):
        directory_entry = directory_entry.info.name.name
        try:
            retstr += directory_entry.decode("utf8") + '<br>'
            directory_entry.decode("utf8")
        except UnicodeError:
            pass
    #return retstr
    return render_template('index.html', retstr=retstr)

#if __name__ == "__main__":
#    app.run()
