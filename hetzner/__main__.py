from hcloud import Client
from .lib import Runner
import asyncio
import time
import yaml
import sys
import os


async def start(server_tasks: list, sleep_for: int, user: str):
    Runner.start_printer()
    resp_list = await asyncio.gather(*server_tasks)
    print(Runner.LIMITER)
    print(f"[Global] Sleeping for {sleep_for} seconds ...")
    await asyncio.sleep(sleep_for)
    # Draw line after sleep to make current action very clear
    print(Runner.LIMITER)
    runners = [Runner(r.server.public_net.ipv4.ip, user, r.root_password, context = {"index": i}) for i, r in enumerate(resp_list)]
    coros = [r.deploy() for r in runners]
    return await asyncio.gather(*coros)


CONF = Runner.read_config()
CONFIG = CONF["general"]

if not CONFIG.get("token"):
    print("Please, run this script with (Hetzner) \"token\" variable in config.yml!\nMore in the Authentication section - https://docs.hetzner.cloud/#authentication.")
    exit(1)

# Create a client
client = Client(token=CONFIG["token"])

# Servers:
# Taken from https://www.hetzner.com/cloud
# Interesting options:
CX11 = "cx11"  # 2.96  €/m - 0.005 €/h - 1vCPU - 2GB RAM  - 20GB storage  - 20TB network cap - the cheapest option, could run any scripts
CX21 = "cx21"  # 5.83  €/m - 0.010 €/h - 2vCPU - 4GB RAM  - 40GB storage  - 20TB network cap - medium, could probably run stripped client
CX31 = "cx31"  # 10.59 €/m - 0.017 €/h - 2vCPU - 8GB RAM  - 80GB storage  - 20TB network cap - minimum specs by the Prysm team for full pledged client
CX41 = "cx41"  # 18.92 €/m - 0.031 €/h - 4vCPU - 16GB RAM - 160GB storage - 20TB network cap - recommended specs by the Prysm team for full pledged client

# In practise, it looks like CX41 would be enough to run 5 attacker nodes even if they will need to sync.
# Running more nodes (if we somehow configure ipv6 traffic), for example 10 becomes very questionable due
# to RAM and storage contraint (CPUs probably can handle this, though the sync will probably take up to
# 2-3 times as long due to being overloaded and increased waste due to context switching between many
# threads). So the worst case scenario (running full node) price for one victim (30 connections) will be
# 6 instances of 5 nodes each, rounding up to about 0.2 €/h (taking into account fees). Thankfully,
# network limits on hetzner are huge so we don't need to worry about that ever despite anything we do.

# This actual type will be used in the code below
TYPE = CONFIG.get("instance", CX11)

# OS name for the server images
IMAGE = CONFIG.get("image", "ubuntu-20.04")

# Sleep to let server finish initialization
SLEEP_PERIOD = CONFIG["wait"]
# TODO: For now only root is supported
USER = CONFIG.get("user", "root")


# To delete servers use `-d` or `--delete` keywords
if len(sys.argv) > 1 and (sys.argv[1] == "-d" or sys.argv[1] == "--delete"):
    servers = client.servers.get_all()
    command = input(f"Servers to delete - {len(servers)}. Do you confirm? [y/N] ")
    if command.lower() != "y":
        print("Didn't recieve confirmation, exiting ...")
        exit(1)

    for server in servers:
        print(f"Deleting server of ID {server.id} with name {server.name}.")
        server.delete()
        print(f"Deleted server with ID {server.id}!")
else:
    start_t = time.time()
    # Number of servers to create.
    if not CONFIG.get("servers"):
        print(f"You didn't set \"servers\" var for amount of servers to create, exiting!")
        exit(1)
    else:
        N = int(CONFIG["servers"])
        print(f"[Global] Deploying {N} servers according to config.yml ...")
        print(Runner.LIMITER)

    tasks = [Runner.create_server(client, TYPE, IMAGE, i) for i in range(N)]
    asyncio.run(start(tasks, SLEEP_PERIOD, USER))
    print(Runner.LIMITER)
    print(f"[Global] Done in {round(time.time() - start_t, 2)} seconds!")

