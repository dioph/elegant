import re

from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.textinput import TextInput
from pylatex import Document

from aspy.core import *
from aspy.log import report
from aspy.methods import *
Config.set('graphics', 'width', '500')
Config.set('graphics', 'height', '500')

# GLOBAL VARIABLES:
# DETERMINE UNIVOCALLY THE CURRENT SYSTEM STATE

N = 1   # NUMERO DE BARRAS
BARRAS = np.zeros(N, object)
LINHAS = []
TRAFOS = []
GRID = np.zeros((10, 10), object)  # OBJECTS THAT RECEIVES THE ELEMENTS PUT INTO THE INTERFACE GRID
SLACK = BarraSL()  # DEFAULT SLACK BAR
GRID[4, 0] = SLACK  # DEFAULT SLACK BAR PUT INTO THE GRID
BARRAS[0] = SLACK  # DEFAULT SLACK BAR PUT INTO THE 'BARRAS' ARRAY
SECTORS = np.zeros((1, 1), bool)
SECTOR_IDS = np.ones((10, 10), int) * -1
SECTOR_IDS[4, 0] = 0
TOTAL = 1
Y = np.zeros((1, 1), complex)

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
            if isinstance(child, Button) and child.state == 'down' and square.coords != [4, 0]:
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
                i, j = square.coords
                for key in GRID[i, j].__dict__.keys():  # UPDATE INSPECT LABELS
                    setattr(toplevel.children[i], key, getattr(GRID[i, j], key))

    def update(self):
        global Y
        S = np.zeros((N, 2), float)
        V0 = np.ones(N, complex)
        Y = np.zeros((N, N), complex) * -1
        for l in LINHAS:
            lt, i, j = l
            node1 = None
            node2 = None
            if j > 0 and isinstance(GRID[i, j - 1], Barra):
                node1 = GRID[i, j - 1].barra_id
            if j < 9 and isinstance(GRID[i, j + 1], Barra):
                node2 = GRID[i, j + 1].barra_id
            if node1 is not None:
                Y[node1, node1] += 1/lt.Z + lt.Y/2
            if node2 is not None:
                Y[node2, node2] += 1/lt.Z + lt.Y/2
            if node1 is not None and node2 is not None:
                Y[node1, node2] -= 1/lt.Z
                Y[node2, node1] -= 1/lt.Z
        for i in range(N):
            S[i, :] = BARRAS[i].P, BARRAS[i].Q  # USER-SPECIFIED POWERS ARRAY COMPLETION
            if isinstance(BARRAS[i], BarraPV):
                V0[i] = BARRAS[i].v / BARRAS[i].vbase
            if isinstance(BARRAS[i], BarraSL):
                V0[i] = BARRAS[i].v * np.exp(1j * BARRAS[i].delta * np.pi/180) / BARRAS[i].vbase
        V = gauss_seidel(Y, V0, S, eps=1e-12)
        for i in range(N):
            BARRAS[i].v = V[i] * BARRAS[i].vbase  # PUT VOLTAGES ENCOUNTERED ON METHOD RUN IN EACH BAR IN 'BARRAS', REAL BASIS

    def edited_element(self, inspect):
        i, j = inspect.coords
        element = GRID[i, j]
        for key in element.__dict__.keys():
            setattr(element, key, getattr(inspect, key))
        self.update()
        print('EDITED')

    def removed_element(self, coords):
        pass

    def added_element(self, element, coords):
        global BARRAS, N, LINHAS, SECTORS, SECTOR_IDS, TOTAL, TRAFOS
        i, j = coords
        GRID[i, j] = element

        if not isinstance(element, Trafo):
            SECTOR_IDS[i, j] = TOTAL
            TOTAL = TOTAL + 1
            SECTORS = np.zeros((TOTAL, TOTAL), bool)
        for a in range(10):
            for b in range(9):
                if SECTOR_IDS[a, b] >= 0 and SECTOR_IDS[a, b + 1] >= 0:
                    SECTORS[SECTOR_IDS[a, b], SECTOR_IDS[a, b + 1]] = True
                    SECTORS[SECTOR_IDS[a, b + 1], SECTOR_IDS[a, b]] = True

        if isinstance(element, Trafo):  # ADDS TRAFO TO TRAFOS (WILL BE USED IN CALCULATIONS INSIDE REPORT)
            TRAFOS.append([element, coords])

        if isinstance(element, Barra):  # ADDS BARRA TO BARRAS (WILL BE USED IN CALCULATIONS INSIDE REPORT)
            BARRAS = np.append(BARRAS, [element])
            element.barra_id = N
            N = N + 1

        if isinstance(element, LT):
            LINHAS.append([element, coords])

        print(BARRAS, LINHAS, SECTORS, SECTOR_IDS)

    def report(self):
        """Generates report when required in execution"""
        doc = Document('report')
        data = [Y, BARRAS, LINHAS, TRAFOS, GRID]
        report(doc, data)
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
