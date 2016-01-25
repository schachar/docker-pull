#!/usr/bin/python
import sys
import os
import json
import urllib2
import base64
import tarfile
import tempfile
import shutil
import optparse
import re
'''
Created on Jan 26, 2016

@author: 
'''
registry="https://registry-1.docker.io"
bar_size = 0
def get_token(reponame,actions,username,password):
    
    if username and password:
        cred = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        headers = {'Authorization':'Basic %s' % cred}
    else:
        headers = {}
    url = 'https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s:%s' % (reponame, actions)
    req = urllib2.Request(url,None,headers)
    response = urllib2.urlopen(req)
    data = json.load(response)
    return data['token']


def get_manifest(token, reponame, tag):
    url = '%s/v2/%s/manifests/%s' % (registry,reponame, tag)
    headers = {'Authorization': 'Bearer %s' % (token,)
               }
    req = urllib2.Request(url,None,headers)
    txt = urllib2.urlopen(req).read()
    manifest = json.loads(txt)
    return manifest

def length_to_human(length):
    if length < 1500:
        human = '% dB' % (length,)
    elif length < 1500*1024:
        human = '%d Kb' % (length/1024)
    elif length < 1500*1024*1024:
        human = '%d Mb' % (length/1024/1024)
    elif length < 1500*1000*1000*1000:
        human = '%d Gb' % (length/1024/1024/1024)
    else:
        human = '%d Tb' % (length/1024/1024/1024/1024)
    return human

def print_progress(image_id, downloaded_bytes, content_length):
    global bar_size
    bar_chars = 50
    if downloaded_bytes == -1:
        text = 'Done downloading: %s size: %s' % (image_id[:12],length_to_human(content_length))
        text = text + ' '*(bar_size-len(text)) + '\n'
        bar_size=0
    else:
        perc_done = int(bar_chars*(1.0+downloaded_bytes) / (1.0+content_length))
        bar =  '#'*perc_done + ' '*(bar_chars-perc_done)
        text = 'Downloading image: %s [%s] %s/%s   ' % (image_id[:12], bar, length_to_human(downloaded_bytes),length_to_human(content_length))
        bar_size = max(bar_size,len(text))
        text = text + '\b'*len(text)
        
        
    sys.stdout.write(text)
    sys.stdout.flush()


def get_layer(token,outpath,reponame, image_id, blobdigest):
    url = '%s/v2/%s/blobs/%s' % (registry,reponame, blobdigest)
    headers = {'Authorization': 'Bearer %s' % (token,)}
    req = urllib2.Request(url,None,headers)
    response = urllib2.urlopen(req)
    content_length = int(response.headers['content-length'])
    blocksize = 1024*1024
    downloaded_bytes = 0;
    with open('%s/layer.tar' % outpath,'wb') as f:
        while True:
            
            block = response.read(blocksize)
            downloaded_bytes = downloaded_bytes + len(block)
            if (content_length > downloaded_bytes):
                print_progress (image_id, downloaded_bytes, content_length)
            if not block: break
            f.write(block)
    print_progress (image_id, -1, content_length)
    
def download(reponame,tag,username,password,):
    token = get_token(reponame,"pull",username,password)
    manifest = get_manifest(token,reponame,tag)
    tempdir = tempfile.mkdtemp(prefix='dockerpull-')
    image_json = manifest['history'][0]['v1Compatibility']
    image_id = json.loads(image_json)['id']
    with open('%s/repositories' % tempdir,'wb') as f:
        data = {reponame: {tag:image_id}}
        json.dump(data,f,indent=4)
    layer_count = len(manifest['fsLayers'])
    print 'downloading %d layers' % layer_count
    downloaded_images = set()
    for layer_index in xrange(0,layer_count):
        image_json = manifest['history'][layer_index]['v1Compatibility']
        image_id = json.loads(image_json)['id']
        if image_id in downloaded_images: continue
        downloaded_images.add(image_id)
        path = os.path.join(tempdir,image_id)
        os.makedirs(path)
        f = open('%s/json' % path,'wb')
        f.write(image_json)
        f.close()
        blobdigest = manifest['fsLayers'][layer_index]['blobSum']
        token = get_token(reponame,"pull",username,password)
        get_layer(token,path,reponame,image_id, blobdigest)
    return tempdir

def create_tar(reponame,tag,image_path):
    
    tar_name = '%s.tar.gz' % re.sub('[^A-Za-z0-9]','_','%s:%s' % (reponame,tag))
    tf = tarfile.open( tar_name,'w|gz')
    tf.add(image_path,'.')
    tf.close()
    return tar_name
        
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i','--image',dest='image',  help='image: repo/image:tag')
    parser.add_option('-u','--username',dest='username', default=None, help='username')
    parser.add_option('-p','--password',dest='password',default=None,  help='password')
    (options, args) = parser.parse_args()
    if not options.image:
        parser.print_help( sys.stderr)
        sys.stderr.write('Image can''t be empty\n')
        sys.exit(-1)
    username= options.username
    password= options.password
    reponame= options.image
    if '/' not in reponame:
        reponame = 'library/%s' % reponame
    if ':' in reponame:
        s = reponame.split(':')
        reponame=s[0]
        tag=s[1]
    else:
        tag='latest'
    tempdir = download(reponame,tag,username,password)
    tar_name = create_tar(reponame, tag, tempdir)
    shutil.rmtree(tempdir)
    print 'Created %s: you can use docker load -i %s to load it' % (tar_name, tar_name)
    

    
    
        
