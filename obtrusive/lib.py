from .mullvad import run_mullvad, mullvad_assertions
from hcloud.server_types.domain import ServerType
from hcloud.images.domain import Image
from collections import defaultdict
from pexpect import pxssh, TIMEOUT
from queue import Queue, Empty
import threading
import pexpect
import asyncio
import string
import random
import time
import yaml
import sys


# Sync printing queue
Q = Queue()


class Runner:
    # Content delimiter
    DELIMITER = "-" * 55
    # A hack to sync writing
    NEEDS_NEW_LINE = False
    # Global indecies for config arrays
    INDECIES = defaultdict(lambda: -1)

    def __init__(self, host: str, user: str, password: str, path: str = "config.yml", context: dict = {}):
        self.host = host
        self.user = user
        self.password = password
        # This is a main ssh client for running commands.
        self.p = pxssh.pxssh(
            # Set timeout to 10 minutes, because commands like 'apt-get install' and/or
            # 'bazel build' (depending on the arguments of course) tend to take very long.
            timeout = 600,
            options = {
                # Avoid hostkey checking, since it's annoying to automate.
                "StrictHostKeyChecking": "no",
                # Avoid "changing key host" issue when recreating servers.
                "UserKnownHostsFile": "/dev/null"
            },
        )
        self.context = context
        # Parse config
        self.path = path
        self.config = self.read_config(self.path)
        self.commands, self.assertions = self.parse_config(self.path)
        self.loop = asyncio.get_event_loop()

    @staticmethod
    def start_printer():
        # This function is being run in the thread as daemon.
        def _printer():
            # This is used to rewrite line with seconds count
            prev = None
            # Seconds counter to add by the end of the line while executing.
            # This works because we are using timeout and adding timeout period
            # after each timeout.
            seconds = 0
            while True:
                try:
                    text, new_line = Q.get(timeout=0.1)

                    if new_line:
                        text += "\n"
                        prev = None
                    else:
                        prev = text

                    sys.stdout.write(text + "\r")
                    sys.stdout.flush()
                    # If we got here, the timeout didn't throw an error, so
                    # we definitely have a new line. Restart seconds counter.
                    Q.task_done()
                    seconds = 0
                except Empty:
                    if prev:
                        sys.stdout.write(f"{prev} ... {round(seconds, 1)} s\r")
                        seconds += 0.1
        # Starting daemon
        threading.Thread(target=_printer, daemon=True).start()

    @staticmethod
    def gen_passwd():
        characters = string.ascii_letters + string.digits
        return "".join(random.choice(characters) for x in range(24))

    @staticmethod
    def read_config(path: str = "config.yml"):
        with open(path) as conf:
            config = yaml.load(conf, Loader=yaml.FullLoader)
        return config

    # This is kinda terrible but I don't want to spend time on it
    def parse_config(self, path):
        config = self.read_config(path)

        commands = list()
        for item in config.get("commands", []):
            if isinstance(item, str):
                commands.append({
                    "command": item.format(
                        **self.context
                    ),
                    "show": False,
                    "period": 1,
                    "expect": None,
                })
            elif isinstance(item, dict):
                show = item.pop("show") if "show" in item else False
                period = item.pop("period") if "period" in item else 1
                expect = item.pop("expect") if "expect" in item else None
                if "use" in item:
                    use = item["use"]
                    if use not in config.get("vars", []):
                        raise ValueError(f"Couldn't find '{use}' in vars!")
                    if item.get("increment", True): self.INDECIES[use] += 1
                    length = len(config["vars"][use])
                    it = config["vars"][use][self.INDECIES[use] % length]
                else:
                    it = None

                commands.append({
                    "command": item["command"].format(
                        **self.context, **item, it=it,
                    ),
                    "show": show,
                    "period": period,
                    "expect": expect,
                })
            else:
                raise NotImplementedError(
                    f"Unparsable config type: {type(item)}.\n"
                    f"Value: {item}."
                )

        assertions = list()
        for item in config.get("assertions", []):
            if isinstance(item, str):
                assertions.append({
                    "command": item.format(
                        **self.context
                    ),
                    show: False,
                    period: 1,
                    contains: False,
                })
            elif isinstance(item, dict):
                show = item.pop("show") if "show" in item else False
                period = item.pop("period") if "period" in item else 1
                contains = item.pop("contains") if "contains" in item else False
                if "use" in item:
                    use = item["use"]
                    if use not in config.get("vars", []):
                        raise ValueError(f"Couldn't find '{use}' in vars!")
                    if item.get("increment", True): self.INDECIES[use] += 1
                    length = len(config["vars"][use])
                    it = config["vars"][use][self.INDECIES[use] % length]
                else:
                    it = None

                assertions.append({
                    "command": item["command"].format(
                        **self.context, **item, it=it,
                    ),
                    "show": show,
                    "period": period,
                    "contains": contains,
                })
            else:
                raise NotImplementedError(
                    f"Unparsable config type: {type(item)}.\n"
                    f"Value: {item}."
                )
        return commands, assertions

    def sys_p(self, text: str, new_line: bool = False, prefix: str = "..."):
        # We can't/shouldn't do this inline.
        text = text.strip(" \n")
        index = self.context["index"]
        if prefix:
            prefix += " "

        text = f"[Server #{index}] {prefix}{text}\033[K"
        Q.put((text, new_line))

    def cmd_out(self, cmd):
        # For commands use special prefix
        self.sys_p(cmd, prefix = "~#:")

    def out(self):
        lines = []

        raw_lines = self.p.before.decode().split("\n")
        for line in raw_lines:
            # Make sure to strip all bad special symbols
            line = line.strip(" \n\r")
            if line:  lines.append(line)

        # First line is our command
        _command = lines.pop(0)

        # The last line is shell prompt
        for line in lines:
            self.sys_p(line, new_line = True)

    async def do_assert(self, item):
        self.p.sendline(item["command"])
        await self.prompt()

        # If "contains" keyword present, check if value is present in the command output
        if item["contains"]:
            if item["contains"] not in self.p.before.decode():
                raise Exception(
                    "[Server #{index}] Assertion Error: command output didn't contain \"{contains}\""
                    .format(**self.context, contains=item["contains"])
                )

    @staticmethod
    def _create_server(client, stype, image, index):
        response = client.servers.create(
            name        = f"manifold-venom-{index}",
            server_type = ServerType(name=stype),
            image       = Image(name=image),
        )
        print(f"[Server #{index}] Created the server with ID {response.server.id}  ({stype}, {image}).")
        print(f"[Server #{index}] IPv4: {response.server.public_net.ipv4.ip}. IPv6: {response.server.public_net.ipv6.ip}.")
        print(f"[Server #{index}] Root password: {response.root_password}.")

        # Hetzner returns some actions, which we can wait for. They are useful, because
        # they can help to know when the server started and ready for connection.
        actions = list()
        if response.action:       actions.append(response.action)
        if response.next_actions: actions.extend(response.next_actions)

        print(f"[Server #{index}] Awaiting {len(actions)} (initialization) actions ...")
        for a in actions:
            a.wait_until_finished()
        print(f"[Server #{index}] Spinning up ...")
        return response

    @classmethod
    async def create_server(cls, client, stype, image, index):
        loop = asyncio.get_event_loop()
        # Running in executor because '.wait_until_finished' in hetzner api uses
        # synchronous polling over network.
        resp = await loop.run_in_executor(None, cls._create_server, client, stype, image, index)
        return resp

    async def prompt(self):
        # Using some prefilled parameters here.
        await self.p.expect([self.p.PROMPT, TIMEOUT], async_=True, timeout=self.p.timeout)

    async def expect(self, p, text):
        # Prefilled asynchronous 'wait', using default timeout
        await p.expect(text, async_=True, timeout=self.p.timeout)

    async def deploy(self):
        # Connecting as raw client and changing password. Hetzner enforces this.
        tmp = pexpect.spawn(f"ssh -tt -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no {self.user}@{self.host}")
        await self.expect(tmp, "'s password")
        tmp.sendline(self.password)  # log in
        await self.expect(tmp, "urrent pass")
        tmp.sendline(self.password)  # change pass
        # Here we generate and show new password
        new_passwd = self.gen_passwd()
        print(f"[Server #{self.context['index']}] Changed password to {new_passwd} ...")
        await self.expect(tmp, "New password:")
        tmp.sendline(new_passwd)  # change pass
        await self.expect(tmp, "new password:")
        tmp.sendline(new_passwd)  # confirm pass
        tmp.kill(0)

        self.password = new_passwd
        self.p.login(self.host, self.user, self.password)

        # If mullvad vpn is configured, we install/launch it first
        if self.config["general"].get("mullvad", False):

            # TODO: Test this, this probably will drop connection when launching vpn
            for cmd, expect in run_mullvad(**self.context):
                self.cmd_out(cmd)
                self.p.sendline(cmd)
                if expect:  await self.expect(self.p, expect)
                else:       await self.prompt()

            for item in mullvad_assertions(**self.context):
                await self.do_assert(item)

        # Running commands
        for item in self.commands:
            self.cmd_out(item["command"])
            self.p.sendline(item["command"])
            await self.prompt()
            if item["show"]: self.out()
    
        # Running assertions
        for item in self.assertions:
            await self.do_assert(item)
            if item["show"]: self.out()

        # Report about assertion-tests if there were any
        if self.assertions:
            self.sys_p(
                f"Successfully ran {len(self.assertions)} assertions!",
                new_line = True, prefix = ""
            )

        self.p.logout()

