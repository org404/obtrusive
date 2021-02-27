
### Setup

##### Installation
First, clone the repo and move into directory:
```
git clone `url`
cd `project`
```
Setup python virtual environment:
```
virtualenv -p python3.8 .venv
source .venv/bin/active
python -m pip install -r requirements.txt
```

##### Configuration
Use sample file from the repo:
```
cp sample-config.yml config.yml
```
Now, open the file with editor of your choice and fill your hetzner token.

##### Run
You already can run the script and see how it goes. For that run:
```
python -m hetzner
```
When the execution finishes, you can open config file again and tweak some stuff or check what was executed.
But you should finish reading through readme first.

##### Remove servers
After execution we need to clean up the servers, so we don't get charged for them:
```
# Note: you can also use `--delete` flag
python -m hetzner -d
```
