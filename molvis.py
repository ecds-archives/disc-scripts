#!/usr/bin/python

import os
import re
import zipfile
from eulxml import xmlmap
import shutil
from time import sleep, time
import logging

# This is a class for the eulxml lib to pull the things values we need from the XML
class Front(xmlmap.XmlObject):
    title = xmlmap.StringField('front/article-meta/title-group/article-title')
    year = xmlmap.StringField('front/article-meta/pub-date/year')
    month = xmlmap.StringField('front/article-meta/pub-date/month')
    day = xmlmap.StringField('front/article-meta/pub-date/day')
    surnames = xmlmap.StringListField('front/article-meta/contrib-group/contrib/name/surname')
    givennames = xmlmap.StringListField('front/article-meta/contrib-group/contrib/name/given-names')
    email = xmlmap.StringField('front/article-meta/author-notes/corresp/email')
    send_to = xmlmap.StringField('front/article-meta/author-notes/corresp')
    volume = xmlmap.StringField('front/article-meta/volume')

# Super simple function to convert numeric months to alpha months
def convert_to_month(num_month):
    alpha_month = ''
    if num_month == '1':
        alpha_month = 'January'
    elif num_month == '2':
        alpha_month = 'February'
    elif num_month == '3':
        alpha_month = 'March'
    elif num_month == '4':
        alpha_month = 'April'
    elif num_month == '5':
        alpha_month = 'May'
    elif num_month == '6':
        alpha_month = 'Jume'
    elif num_month == '7':
        alpha_month = 'July'
    elif num_month == '8':
        alpha_month = 'August'
    elif num_month == '9':
        alpha_month = 'September'
    elif num_month == '10':
        alpha_month = 'Ocotober'
    elif num_month == '11':
        alpha_month = 'November'
    elif num_month == '12':
        alpha_month = 'December'
    return alpha_month

# A function to send commands to our pymail script that uses the SES SMTP from AWS
def mail(name, email, volume, article_num, destination):
    top = ''
    bottom = ''
    sender = 'mvision@emory.edu'
    subject = ''
    cc = 'molvis@emory.edu'
    
    if 'galley' in destination:
        top = ''',
\nYour typeset galley is available at the following link. Please ensure that all figures and tables are present and associated with their correct legends. Please respond within 24 hours, otherwise we will assume all is well and proceed with publication.
ERRORS NOTED AFTER PUBLICATION CANNOT BE CORRECTED!\n
\thttp://www.molvis.org/molvis/galley/priv/'''
        
        bottom = '''\n\nBest regards,
The Editors of Molecular Vision'''

        subject = 'Molecular Vision galley proof notification'
        
    else:
        top = ''',\n
Congratulations!  Your article has been published in Molecular Vision.
You can see it at:\n
\thttp://www.molvis.org/molvis/'''

        bottom = '''\n
An announcement will be sent to the subscribers of Molecular Vision Announcements (MV-ANN).\n
Work funded by NIH, HHMI, Wellcome Trust, or MRC must be made available  in PubMed Central once it is published. Molecular Vision has already submitted your paper to PubMed Central and PubMed; it should appear in  those repositories within a few days. You do not need to do anything,  we have done all the work for you!\n
If your paper includes data that you released to GenBank or other databases, you should request that those databases add the citation information for your paper to the appropriate database entries. Sorry, we cannot do this for you!\n
Warmest Regards,
The Editors of Molecular Vision'''
        
        subject = 'Molecular Vision publication notification'
        
    msg = 'Dear ' + name + top + volume + '/' + article_num + bottom
    
    os.system('python /data/scripts/pymail.py --to \'' + email + '\' --cc \'' + cc + '\' --sender \'' + sender + '\' --subject \'' + subject + '\' --body \'' + msg + '\'')
    logging.info('Email sent to ' + email)

# This is where the real magic happens
def update(path, file):
    names = ''
    volume = ''
    toc_update = ''
    tmp = '/tmp/'
    destination = ''
    if 'publish' in path:
        destination = '/dav/molvis/'
    elif 'galley' in path:
        destination = '/dav/molvis/galley/priv/'
    os.system('unzip -d' + tmp + ' ' + path + file)
    os.remove(path + file)
    article_num = file[0:-4]
    ext_files = os.listdir(tmp + article_num)
    for ext_file in ext_files:
        if 'XML' in ext_file:
            article_info = xmlmap.load_xmlobject_from_file(tmp + file[0:-4] + '/' + ext_file, xmlclass=Front)
            volume = 'v' + article_info.volume
            send_to = re.sub('Correspondence to: ', "", article_info.send_to)
            send_to = re.sub(',.*', "", send_to)
            num = 0
            for name in article_info.surnames:
                names = article_info.givennames[num] + ' ' + name + ', ' + names
                num = num + 1

            alpha_month = convert_to_month(article_info.month)
            toc_update = '\n\t<p>\n\t\t<font size="4"><b>' + article_info.title + '</b></font><br />\n\t\t<font size="3">' + names[0:-2] + '<br />\n\t\tPublished: ' + article_info.day + ' ' + alpha_month + ' ' + article_info.year + ' [<a href="' + volume + '/' + article_num + '">Full Text</a>]</font>\n\t</p>'
            toc_update = toc_update.encode('ascii', 'ignore')
            mail(send_to, article_info.email, volume, article_num, destination)

    if 'publish' in path:
        toc = '/dav/molvis/toc.html'
        toc_bk = '/dav/molvis/toc.bk'
        os.remove(toc_bk)
        shutil.move(toc, toc_bk)
        
        with open(toc, 'w') as out:
            for line in open(toc_bk):
                out.write(line.replace('<!--new-->', '<!--new-->' + toc_update))
                
        logging.info('TOC upadated with ' + article_num)
        
    shutil.move(tmp + article_num, destination + volume + '/')

logging.basicConfig(filename='/data/logs/molvis.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

if os.path.isfile('/data/scripts/molvis-running'):
    logging.info('Script still working from previous run. Exiting')
    exit()
else:
    os.system('touch /data/scripts/molvis-running')

if not os.path.ismount('/dav'):
        os.system('/usr/sbin/mount.davfs https://files.web.emory.edu/site/www.molvis.org/htdocs/ /dav')
        logging.info('Mounting DAV')
else:
        logging.warning('DAV already mounted')

paths = ['/dav/to-publish/', '/dav/to-galley/']
for path in paths:
    files = os.listdir(path)
    files.sort()
    for file in files:
        if 'zip' in file.lower():
            logging.info(file + ' found in ' + path)
            st = os.stat(path + file)    
            mtime = st.st_mtime
            if (time() - mtime) > 300:
                update(path, file)
                sleep(30)
            else:
                logging.info(file + ' found but not old enough')

os.remove('/data/scripts/molvis-running')

os.system('umount /dav')
if not os.path.ismount('/dav'):
    logging.info('DAV unmounted')
elif os.path.ismount('/dav'):
    logging.warning('DAV failed to unmaount')
