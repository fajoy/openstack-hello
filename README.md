openstack-hello
===============

pip install Paste python-openstackclient
git clone https://github.com/openstack/oslo-incubator.git
mkdir hello helloclient
cd oslo-incubator/
python update.py --nodeps --base hello --dest-dir ../hello --modules service,eventlet_backdoor,gettextutils,log,importutils,jsonutils,timeutils,local,threadgroup,loopingcall,excutils
python update.py --nodeps --base helloclient --dest-dir ../helloclient --modules gettextutils,importutils,strutils,apiclient,cliutils,uuidutils,py3kcompat
