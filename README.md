
# docker-pull.py #

This python script allows you to pull a docker image with its parent layers into a tar.gz file which you can load into docker. 

I wrote this script to overcome the following error which may occur when passing through SSL proxy:

`x509: RSA modulus is not a positive number`

But it may be used whenever you'd like to create a docker image tar.gz file without caching the result on the host you are using for the download.

## Usage ##
Library image (library/hello-world):
`docker-pull.py hello-world`

With authentication:
`docker-pull.py -u myuser -p mypassword docker.io/namespace/myimage:1.2.3`

