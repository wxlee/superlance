# Use mailx to send alarm mail
Install mailx (Ubuntu, Debian)
```sh
# apt-get install heirloom-mailx -y
```
# Install supervisor and superlance 
```sh
# apt-get install python-pip -y
# pip install supervisor
# git clone https://github.com/wxlee/superlance
# cd superlance
# python setup.py install
```

# Add event listener to /etc/supervisord.conf
```sh
[eventlistener:crashmail]
command=crashmail -f "crash@xxx.com" -s "NodeCrash" -S smtp=x.x.x.x:25 -m recv@xxx.com
events=PROCESS_STATE_EXITED
```
Note: Do not use space!!
# Start supervisord
```sh
supervisord -c /etc/supervisord.conf
```

