from typing import Generator, Tuple, Dict

# By the default we expect bash return, otherwise if tuple is provided,
# second argument will be an expected output string
INSTALL_MULLVAD = (
    "apt-get update && apt-get install -qq -y curl jq openresolv wireguard docker.io",
    "curl -LO https://mullvad.net/media/files/mullvad-wg.sh",
    "chmod +x ./mullvad-wg.sh",
    # Here we expect to be asked for account number,
    # which is the only authentication value
    ("./mullvad-wg.sh", "Mullvad account number:"),
    # This is an important part, here you have to input account number
    "{MULLVAD_ID}",
)


RUN_MULLVAD = (
    # We can predefine which countries/servers we want
    # Examples:
    #   - "export NEW_WG=mullvad-gb19",
    #   - "export NEW_WG={MULLVAD_SERVER}",

    # We can just randomly choose from all config files
    r"export NEW_WG=$(ls /etc/wireguard/ | shuf -n 1 | sed 's/\(.*\)\..*/\1/')",
    # "wg-quick up $NEW_WG",
    # "systemctl enable wg-quick@$NEW_WG",
    "mkdir -p /tmp/mullvad_config",
    "cp /etc/wireguard/$NEW_WG.conf /tmp/mullvad_config/wg0.conf",
    # Sleep command
    "SLEEP_COMMAND",
    "docker run -d \
        --privileged \
        --name={MULLVAD_DOCKER_NAME} \
        --cap-add=NET_ADMIN \
        --cap-add=SYS_MODULE \
        -e PUID=1000 \
        -e PGID=1000 \
        -e TZ=Europe/London \
        -p 51820:51820/udp \
        -v /tmp/mullvad_config:/config \
        -v /lib/modules:/lib/modules \
        --sysctl=\"net.ipv4.conf.all.src_valid_mark=1\" \
        --sysctl=\"net.ipv6.conf.all.disable_ipv6=0\" \
        --restart unless-stopped \
        ghcr.io/linuxserver/wireguard",
)


COMMANDS = INSTALL_MULLVAD + RUN_MULLVAD


ASSERTIONS = (
    ("docker ps", "{MULLVAD_DOCKER_NAME}"),
)


def run_mullvad(commands: tuple = COMMANDS, **kwargs) -> Generator[Tuple[str, str], None, None]:
    for item in commands:
        if isinstance(item, str):
            yield item.format(**kwargs), None
        elif isinstance(item, tuple):
            cmd, expect = item
            yield cmd.format(**kwargs), expect.format(**kwargs)
        else:
            raise NotImplementedError(f"Argument {item} is not supported!")


def mullvad_assertions(**kwargs) -> Generator[Dict[str, str], None, None]:
    for item in ASSERTIONS:
        if isinstance(item, str):
            yield {
                "command": item.format(**kwargs),
                "contains": None
            }
        elif isinstance(item, tuple):
            cmd, expect = item
            yield {
                "command": cmd.format(**kwargs),
                "contains": expect.format(**kwargs),
            }
        else:
            raise NotImplementedError(f"Argument {item} is not supported!")


if __name__ == "__main__":
    ctx = {"a": 1, "MULLVAD_ID": "1111222233334444"}

    for cmd, expect in run_mullvad(commands=INSTALL_MULLVAD, **ctx):
        print(">>>", cmd)
        print("<<<", expect if expect else "Awaiting for shell ...")
    print(f"{'-' * 16}\nDoing assertions:\n{'-' * 16}")
    for i, item in enumerate(mullvad_assertions(**ctx)):
        print(f"Assertion #{i}")
        print("cmd:\t\t", item["command"])
        if item["contains"]: print("contains:\t", item["contains"])

