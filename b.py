from autoreply import command, command_args


def main() -> None:
    for label, result in (
        ("command", command("ls")),
        ("command_args", command_args(["whoami"])),
    ):
        if result["returncode"] != 0 or not result["stdout"]:
            raise RuntimeError(f"{label} failed: {result['stderr']}")
        print(f"{label}: {result['stdout']}")


if __name__ == "__main__":
    main()
