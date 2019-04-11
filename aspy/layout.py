import re

from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput


from aspy.core import *
from aspy.methods import *
from aspy.log import log
from pylatex import Document

Config.set('graphics', 'width', '1500')
Config.set('graphics', 'height', '750')

N = 0
Y = np.zeros((N, N), complex)
V0 = np.zeros(N, complex)
BARRAS = np.zeros(N, object)
GRID = np.zeros((10, 10), object)
SLACK = BarraSL()


class FloatInput(TextInput):
    pat = re.compile('[^0-9]')

    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)


def insert_LT(coords, l, r, D, d, m):
    lt = LT(l=l, r=r, D=D, d=d, m=m)
    GRID[coords[0], coords[1]] = lt
    add_line()


def add_line():
    pass


def insert_trafo():
    pass

# insert_barra(SLACK, [4, 0])


class Interface(FloatLayout):
    def add_grid(self, grid, elements, toplevel):
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
            square.bind(on_press=lambda x: self.update_grid(x, elements, toplevel))
            square.coords = (9 - (i // 10), 9 - (i % 10))
            if i == 59:  # adds default slack
                square.background_normal = "./data/barra.jpg"
                square.background_down = "./data/barra.jpg"
                square.info = 'slack'

    def update_grid(self, square, elements, toplevel):
        """Updates the button icon in the grid

        Parameters
        ----------
        square: the button in the grid to be updated
        elements: the grid of togglebuttons
        toplevel: main grid (3 cols)
        """
        for child in elements.children:
            if isinstance(child, Button):
                if child.state == 'down':
                    # TODO: desenhos dos botões
                    if square.coords != [4, 0]:
                        square.background_normal = child.background_normal
                        square.background_down = child.background_down
                        square.info = child.info
                    else:
                        pass
                    if square.coords != [4, 0]:
                        if square.info == 'lt':
                            lt = LT()
                            self.add_line(lt, square.coords)
                        elif square.info == 'pq':
                            b = BarraPQ()
                            self.add_bus(b, square.coords)
                        elif square.info == 'trafo':
                            pass
                        break
                    else:
                        pass
        else:
            print(square.coords, square.info)
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

    def update(self):
        S = np.zeros((N, 2), float)
        for i in range(N):
            S[i, :] = BARRAS[i].P, BARRAS[i].Q
        V = gauss_seidel(Y, V0, S, eps=1e-12)
        for i in range(N):
            BARRAS[i].V = V[i]

    def add_bus(self, b, coords):
        global N
        GRID[coords[0], coords[1]] = b
        N += 1
        BARRAS[N] = b

    def add_line(self, lt, coords):
        global N
        i, j = coords
        node1 = None
        node2 = None
        if j > 0 and isinstance(GRID[i,j-1], Barra):
            node1 = GRID[i,j-1].id
        if j < 9 and isinstance(GRID[i,j+1], Barra):
            node2 = GRID[i,j-1].id
        if node1 is not None:
            Y[node1, node1] += 1/lt.Z + lt.Y/2
        if node2 is not None:
            Y[node2, node2] += 1/lt.Z + lt.Y/2
        if node1 is not None and node2 is not None:
            Y[node1, node2] -= 1/lt.Z
            Y[node2, node1] -= 1/lt.Z

    def report(self, S=None, V=None):
        """Generates report when required in execution"""
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
