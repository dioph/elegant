import pyautogui

_TRANSLATOR_ = {
    'l': (-50, None),
    'u': (None, -50),
    'r': (50, None),
    'd': (None, 50),
    'lu': (-50, -50),
    'ul': (-50, -50),
    'ld': (-50, 50),
    'dl': (-50, 50),
    'ru': (50, -50),
    'ur': (50, -50),
    'rd': (50, 50),
    'dr': (50, 50)
}

def sequence_to_line(sequence, duration=0.15):
    commands = sequence.split(' ')
    pyautogui.mouseDown()
    for command in commands:
        if command[0].isdigit():
            for _ in range(int(command[0])):
                pyautogui.moveRel(*_TRANSLATOR_[command[1:]], duration=duration)
        else:
            pyautogui.moveRel(*_TRANSLATOR_[command], duration=duration)
    pyautogui.mouseUp()


def test_interface():
    # Put bars
    pyautogui.moveTo(x=317, y=316)
    pyautogui.doubleClick()
    pyautogui.moveRel(100, None)
    pyautogui.doubleClick()
    pyautogui.moveRel(100, -100)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 200)
    pyautogui.doubleClick()
    pyautogui.moveRel(100, -250)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 100)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(100, -350)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 100)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveRel(None, 50)
    pyautogui.doubleClick()
    pyautogui.moveTo(317, 316)
    # Put lines
    sequence_to_line('2r')
    sequence_to_line('2ur')
    sequence_to_line('ur r')
    top = pyautogui.position()
    pyautogui.moveRel(-100, 50)
    sequence_to_line('2r')
    pyautogui.moveRel(-100, None)
    sequence_to_line('rd r')
    pyautogui.moveRel(-200, 50)
    sequence_to_line('2dr')
    sequence_to_line('ur r')
    pyautogui.moveRel(-100, 50)
    sequence_to_line('2r')
    pyautogui.moveRel(-100, None)
    sequence_to_line('dr r')
    pyautogui.moveRel(-100, -50)
    sequence_to_line('d dr r')
    pyautogui.moveTo(*top)
    for _ in range(8):
        sequence_to_line('2r')
        pyautogui.moveRel(-100, 50)