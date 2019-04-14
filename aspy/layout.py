import re

from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from pylatex import Document

from aspy.core import *
from aspy.log import log
from aspy.methods import *

Config.set('graphics', 'width', '1500')
Config.set('graphics', 'height', '750')

# GLOBAL VARIABLES:
# DETERMINE UNIVOCALLY THE CURRENT SYSTEM STATE

N = 1
Y = np.zeros((N, N), complex)
BARRAS = np.zeros(N, object)
LINHAS = np.zeros(0, object)
GRID = np.zeros((10, 10), object)
SLACK = BarraSL()
GRID[4,0] = SLACK
BARRAS[0] = SLACK


class FloatInput(TextInput):
    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


class Interface(FloatLayout):
    def init_grid(self, grid, elements, toplevel):
        """Initializes the grid

        Parameters
        ----------
        grid: the grid to be initialized
        elements: the grid of togglebuttons
        toplevel: main grid (3 cols)
        """
        for i in range(grid.cols):
            for j in range(grid.rows):
                grid.add_widget(Button())

        for i, square in enumerate(grid.children):
            square.bind(on_press=lambda x: self.clicked_grid(x, elements, toplevel))
            square.coords = (9 - (i // 10), 9 - (i % 10))
            if i == 59:  # adds default slack
                square.background_normal = "./data/barra.jpg"
                square.background_down = "./data/barra.jpg"
                square.info = 'slack'

    def clicked_grid(self, square, elements, toplevel):
        """Updates the button icon in the grid

        Parameters
        ----------
        square: the button in the grid to be updated
        elements: the grid of togglebuttons
        toplevel: main grid (root.children[0]; 3 cols)
        """
        for child in elements.children:
            if isinstance(child, Button):
                if child.state == 'down':
                    # TODO: desenhos dos botões
                    if square.coords != [4, 0]:     # forbids removing slack bus
                        square.background_normal = child.background_normal
                        square.background_down = child.background_down
                        square.info = child.info
                        self.removed_element(square.coords)
                        if square.info == 'lt':
                            lt = LT()
                            self.added_element(lt, square.coords)
                        elif square.info == 'pq':
                            b = BarraPQ()
                            self.added_element(b, square.coords)
                        elif square.info == 'pv':
                            b = BarraPV()
                            self.added_element(b, square.coords)
                        elif square.info == 'trafo':
                            t = Trafo()
                            self.added_element(t, square.coords)
                        self.update()
                        break

        else:   # OPEN INSPECT ELEMENT
            mask = np.zeros(6, bool)
            if square.info == 'slack':      # SLACK
                mask[-1] = True
            elif square.info == 'lt':       # LT
                mask[-2] = True
            elif square.info == 'pq':       # PQ
                mask[-3] = True
            elif square.info == 'pv':       # PV
                mask[-4] = True
            elif square.info == 'trafo':    # TRAFO
                mask[-5] = True
            else:                           # DEFAULT
                mask[-6] = True
            for i in range(6):
                toplevel.children[i].visible = mask[i]
                toplevel.children[i].coords = square.coords

    def update(self):
        S = np.zeros((N, 2), float)
        V0 = np.ones(N, complex)
        # TODO: calculate Y
        for i in range(N):
            S[i, :] = BARRAS[i].P, BARRAS[i].Q
        V = gauss_seidel(Y, V0, S, eps=1e-12)
        for i in range(N):
            BARRAS[i].v = V[i]

    def edited_element(self, inspect):
        i, j = inspect.coords
        element = GRID[i, j]
        for key in element.__dict__.keys():
            setattr(element, key, getattr(inspect, key))
        self.update()

    def removed_element(self, coords):
        pass

    def added_element(self, element, coords):
        global BARRAS, N, LINHAS
        i, j = coords
        GRID[i, j] = element
        if isinstance(element, Barra):
            BARRAS = np.append(BARRAS, [element])
            N = N + 1
            element.id = N
        if isinstance(element, LT):
            LINHAS = np.append(LINHAS, [element])

    def report(self, S=None, V=None):
        """Generates report when required in execution"""
        # TODO: calculate S and V
        doc = Document('log')
        log(doc, S, V)
        doc.generate_pdf(clean_tex=False, compiler='pdflatex')
        print('Reporting...')
        doc.generate_tex()
        print('Reported')


presentation = Builder.load_file('./interface.kv')


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()
