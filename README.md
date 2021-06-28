### Tool description
Obtrusive is a tool, which was used to manage multiclient, multivictim DOS fleet for eth2 based on the prysm client.  
  
Helped to do:
* establishes adverserial connections to up to [N] clients
* attacking eth clients like Prysm (tested primarily with it), Nimbus, Teku, Lighthouse
* rate limit conform
* vpn support for rate limit circumvention

### Setup

##### Prerequisites
* python3.8 or later  
* virtualenv  

##### Installation
First, clone the repo and move into directory:
```
git clone https://github.com/org404/obtrusive.git
cd obtrusive
```
Setup python virtual environment:
```
virtualenv -p python3.8 .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

##### Configuration
Use sample file from the examples folder:
```
cp examples/basic-config.yml config.yml
```
Now, open the file with editor of your choice and fill your hetzner token.

##### Run
You already can run the script and see how it goes:
```
python -m obtrusive
```
When the execution finishes, you can open config file again and tweak some stuff or check what was executed.
But you should finish reading through readme first.

##### Remove servers
After execution you need to clean up the servers, so you don't get charged for them:
```
# Note: you can also use `--delete` flag
python -m obtrusive -d
```

##### Config options
First, it's recommended to read through [examples/basic-config.yml](./examples/basic-config.yml). If something is still not clear, you can try checking out [other example configs](./examples), or open an issue.
