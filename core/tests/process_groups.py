"""Process helpers for the pool tests: list the live processes of a process group from /proc (Linux)."""

from pathlib import Path


def process_names_in_group(process_group_id: int) -> list[str]:
    """The command names of every live (not zombie) process in the group."""
    process_names = []
    for stat_path in Path("/proc").glob("[0-9]*/stat"):
        try:
            stat_line = stat_path.read_text()
        except OSError:
            continue  # the process ended while we looked
        command_name = stat_line[stat_line.index("(") + 1 : stat_line.rindex(")")]
        state, _, group_id = stat_line[stat_line.rindex(")") + 2 :].split()[:3]
        if int(group_id) == process_group_id and state != "Z":
            process_names.append(command_name)
    return process_names
