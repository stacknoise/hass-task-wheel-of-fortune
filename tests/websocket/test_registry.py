"""Die Befehlstabelle: Namen, Rechte und Vollständigkeit gegen KONZEPT §6.4."""

from custom_components.task_wheel.const import events
from custom_components.task_wheel.websocket.command import Access
from custom_components.task_wheel.websocket.registry import COMMANDS

ADMIN_PREFIXES = (
    events.WS_PERSON_PREFIX,
    events.WS_TASK_PREFIX,
    events.WS_SCHEDULE_PREFIX,
    events.WS_SETTINGS_UPDATE,
    events.WS_ROUND_DELETE,
)
EXPECTED = {
    events.WS_SNAPSHOT,
    events.WS_SUBSCRIBE,
    events.WS_HISTORY_LIST,
    events.WS_STATISTICS_GET,
    events.WS_ASSIGNMENT_COMPLETE,
    events.WS_ASSIGNMENT_SWAP,
    events.WS_ASSIGNMENT_SKIP,
    events.WS_ROUND_DELETE,
    events.WS_DRAW_BEGIN,
    events.WS_DRAW_SPIN,
    events.WS_DRAW_SPIN_REST,
    events.WS_DRAW_COMMIT,
    events.WS_DRAW_CANCEL,
    events.WS_SETTINGS_UPDATE,
}


def test_names_are_unique_and_prefixed() -> None:
    names = [command.name for command in COMMANDS]
    assert len(names) == len(set(names))
    assert all(name.startswith(events.WS_PREFIX) for name in names)


def test_all_documented_commands_exist() -> None:
    names = {command.name for command in COMMANDS}
    assert names >= EXPECTED
    for prefix in (events.WS_PERSON_PREFIX, events.WS_TASK_PREFIX, events.WS_SCHEDULE_PREFIX):
        for action in (events.WS_ACTION_CREATE, events.WS_ACTION_UPDATE, events.WS_ACTION_DELETE):
            assert prefix + action in names


def test_only_configuration_and_deleting_rounds_need_admin() -> None:
    for command in COMMANDS:
        is_config = command.name.startswith(ADMIN_PREFIXES)
        assert (command.access is Access.ADMIN) is is_config, command.name


def test_reads_do_not_mutate() -> None:
    reads = {
        events.WS_SNAPSHOT,
        events.WS_SUBSCRIBE,
        events.WS_HISTORY_LIST,
        events.WS_STATISTICS_GET,
        events.WS_AVAILABILITY_PREVIEW,
        events.WS_DRAW_PREVIEW,
    }
    for command in COMMANDS:
        assert command.mutates is (command.name not in reads), command.name
