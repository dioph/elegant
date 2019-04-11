import re

from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

from aspy.core import *
from aspy.methods import *

Config.set('graphics', 'width', '1500')
Config.set('graphics', 'height', '750')

# GLOBAL VARIABLES:
# DETERMINE UNIVOCALLY THE CURRENT SYSTEM STATE

N = 1
Y = np.zeros((N, N), complex)
V0 = np.zeros(N, complex)
BARRAS = np.zeros(N, object)
GRID = np.zeros((10, 10), object)
SLACK = BarraSL()
GRID[4,0] = SLACK
BARRAS[0] = SLACK


class InspectSL(BoxLayout):
    def __init__(self, V=1e3, Vbase=1e3, delta=0.0, pg=np.nan, qg=np.nan, pl=0.0, ql=0.0, coords=None):
        super(InspectSL, self).__init__()
        self.V = V
        self.Vbase = Vbase
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.coords = coords


class InspectLT(BoxLayout):
    def __init__(self, l=80e3, rho=1.78e-8, r=2.5e-2, D12=1., D23=1., D31=1., d=0.5, m=1, coords=None):
        super(InspectLT, self).__init__()
        self.l = l
        self.rho = rho
        self.r = r
        self.D12 = D12
        self.D23 = D23
        self.D31 = D31
        self.d = d
        self.m = m
        self.coords = coords


class InspectPQ(BoxLayout):
    def __init__(self, V=np.nan, delta=np.nan, pl=0.0, ql=0.0, coords=None):
        super(InspectPQ, self).__init__()
        self.V = V
        self.delta = delta
        self.pl = pl
        self.ql = ql
        self.coords = coords


class InspectPV(BoxLayout):
    def __init__(self, V=1e3, delta=np.nan, pg=0.0, qg=np.nan, pl=0.0, ql=0.0, coords=None):
        super(InspectPV, self).__init__()
        self.V = V
        self.delta = delta
        self.pg = pg
        self.qg = qg
        self.pl = pl
        self.ql = ql
        self.coords = coords


class InspectTRAFO(BoxLayout):
    def __init__(self, Vbase1=1e3, Vbase2=1e3, Snom=1e6, X=0., coords=None):
        super(InspectTRAFO, self).__init__()
        self.Vbase1 = Vbase1
        self.Vbase2 = Vbase2
        self.Snom = Snom
        self.X = X
        self.coords = coords


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
            if i == 59:
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
                    square.background_normal = child.background_normal
                    square.background_down = child.background_down
                    square.info = child.info
                    if square.info == 'lt':
                        lt = LT()
                        self.add_line(lt, square.coords)
                    elif square.info == 'pq':
                        b = BarraPQ()
                        # self.add_bus(b, square.coords)
                    elif square.info == 'trafo':
                        pass
                    break
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
                toplevel.children[i].coords = square.coords

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
            node1 = GRID[i, j-1].id
        if j < 9 and isinstance(GRID[i,j+1], Barra):
            node2 = GRID[i, j+1].id
        if node1 is not None:
            Y[node1, node1] += 1/lt.Z + lt.Y/2
        if node2 is not None:
            Y[node2, node2] += 1/lt.Z + lt.Y/2
        if node1 is not None and node2 is not None:
            Y[node1, node2] -= 1/lt.Z
            Y[node2, node1] -= 1/lt.Z


presentation = Builder.load_file('./interface.kv')


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()
