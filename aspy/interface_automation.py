import pyautogui
import autoit

__all__ = ['sequence_to_line', 'sequence_to_bus', 'move_to_initial_position']

_TRANSLATOR_ = {
    'l': (-50, 0),
    'u': (0, -50),
    'r': (50, 0),
    'd': (0, 50),
    'lu': (-50, -50),
    'ul': (-50, -50),
    'ld': (-50, 50),
    'dl': (-50, 50),
    'ru': (50, -50),
    'ur': (50, -50),
    'rd': (50, 50),
    'dr': (50, 50)
}


def move_to_initial_position(win_name='ASPy'):
    left_upper_corner = autoit.win_get_pos(win_name)
    pyautogui.moveTo(left_upper_corner[0] + 272, left_upper_corner[1] + 298)


def _move(sequence):
    commands = sequence.split(' ')
    offset = {'x': 0, 'y': 0}
    for command in commands:
        tms = 1
        if command[0].isdigit():
            tms = int(command[0])
            command = command[1:]
        offset['x'] += tms * _TRANSLATOR_[command][0]
        offset['y'] += tms * _TRANSLATOR_[command][1]
    pyautogui.moveRel(offset['x'], offset['y'], duration=0)


def _step_move(sequence, duration=0.15):
    commands = sequence.split(' ')
    for command in commands:
        tms = 1
        if command[0].isdigit():
            tms = int(command[0])
            command = command[1:]
        for i in range(0, tms):
            pyautogui.moveRel(*_TRANSLATOR_[command], duration=duration)


def _parse_drag(sequence):
    pos = 0
    drag = str()
    while sequence[pos] != '>':
        drag += sequence[pos]
        pos += 1
    drag += sequence[pos]
    return pos + 1, drag


def _parse_move(sequence):
    pos = 0
    move = str()
    while sequence[pos] != ')':
        move += sequence[pos]
        pos += 1
    move += sequence[pos]
    return pos + 1, move


def _get_commands_from_seq(sequence):
    pos = 0
    commands = []
    while pos < len(sequence):
        char = sequence[pos]
        if char == '<':
            pos_inc, nxt_evnt = _parse_drag(sequence[pos:])
        elif char == '(':
            pos_inc, nxt_evnt = _parse_move(sequence[pos:])
        else:
            raise Exception('Hit non key-character')
        commands.append(nxt_evnt)
        pos += pos_inc
    return commands


def _in_event(char, curr):
    if char in ('<', '('):
        return True
    elif char in ('>', ')'):
        return False
    else:
        return curr


def _strip_outside_event_spaces(sequence):
    sequence = list(sequence)
    in_evnt = False
    pos = 0
    while pos < len(sequence):
        in_evnt = _in_event(sequence[pos], in_evnt)
        if not in_evnt and sequence[pos] == ' ':
            sequence.pop(pos)
        else:
            pos += 1
    return "".join(sequence)


def _strip_inside_event_spaces(sequence):
    pass


def sequence_to_line(grand_sequence: str, duration=0.15):
    """Transform an string sequence in interface automated movements

    Parameters
    ----------
    grand_sequence: string containing the sequence that generates interface movements

    Example
    -------
    grand_sequence = '<2u r>(2dr)'\n
    <2u r>: draw line moving cursor two squares upper and one square to the right\n
    (2dr): move the cursor in down-right diagonal direction by two squares

    Notes
    -----
    'r', 'u', 'l' and 'd' means 'to right one square', 'upper one square', 'to left one square' and 'down one square'\n
    It is possible to mix movements in different directions (diagonal movements) with 'ur', 'ul', 'dr', 'dl'\n
    If a number N is written before the commands (e.g.: Nr), the command will be repeated N times\n
    One should use "<>" to indicate line to be drawn while the movement is performed or "()" to indicate a move
    without line drawing\n
    **Spaces should be expressly avoided in any movement code**
    """
    grand_sequence = _strip_outside_event_spaces(grand_sequence)
    parsed_sequence = _get_commands_from_seq(grand_sequence)
    for sequence in parsed_sequence:
        print(sequence)
        start = sequence[0]
        sequence = sequence[1: -1]
        if start == '<':
            pyautogui.mouseDown()
            _step_move(sequence, duration=duration)
            pyautogui.mouseUp()
        elif start == '(':
            _move(sequence)
        else:
            raise Exception('Invalid start key-character found')


def sequence_to_bus(sequence):
    commands = sequence.split(' ')
    for command in commands:
        if command == '.':
            pyautogui.doubleClick()
        else:
            _move(command)