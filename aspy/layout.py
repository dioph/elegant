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

# Config.set('graphics', 'width', '1500')
# Config.set('graphics', 'height', '750')
Config.set('graphics', 'width', '600')
Config.set('graphics', 'height', '600')

N = 0
Y = np.zeros((N, N), complex)
V0 = np.zeros(N, complex)
BARRAS = np.zeros(N, object)
GRID = np.zeros((10, 10), object)
SLACK = BarraSL()
MANIPULATOR = {"coords": [0, 0], "info": None}


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
        global N, BARRAS
        for i in range(grid.cols):
            for j in range(grid.rows):
                grid.add_widget(Button())

        for i, square in enumerate(grid.children):
            # Issue: this blocks runs two times
            square.bind(on_press=lambda x: self.update_grid(x, elements, toplevel))
            square.coords = (9 - (i // 10), 9 - (i % 10))
            if i == 59:  # adds default slack
                square.background_normal = "./data/barra.jpg"
                square.background_down = "./data/barra.jpg"
                square.info = 'slack'
                GRID[4][0] = BarraSL(id=N)


    def update_grid(self, square, elements, toplevel):
        """Updates the button icon in the grid

        Parameters
        ----------
        square: the button in the grid to be updated
        elements: the grid of togglebuttons
        toplevel: main grid (3 cols)
        """
        global MANIPULATOR
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
                            # self.add_line(lt, square.coords)
                            self.update_GRID_BUS(lt, square.coords)
                        elif square.info == 'pq':
                            b = BarraPQ(id=N)
                            self.update_GRID_BUS(b, square.coords)
                        elif square.info == 'pv':
                            b = BarraPV(id=N)
                            self.update_GRID_BUS(b, square.coords)
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
            MANIPULATOR['coords'] = square.coords
            MANIPULATOR['info'] = square.info


    def update(self):
        S = np.zeros((N, 2), float)
        for i in range(N):
            S[i, :] = BARRAS[i].P, BARRAS[i].Q
        V = gauss_seidel(Y, V0, S, eps=1e-12)
        for i in range(N):
            BARRAS[i].V = V[i]


    def update_GRID_BUS(self, b, coords):
        global N, BARRAS
        # TODO: Problema: adicionando duas vezes SLACK
        if isinstance(GRID[coords[0], coords[1]], Barra) and isinstance(b, Barra):  # BarraNova <- BarraVelha
            id = GRID[coords[0], coords[1]].id
            for POS, BAR in enumerate(BARRAS):
                if BAR.id == id:
                    BARRAS[POS] = b
        elif isinstance(GRID[coords[0], coords[1]], Barra) and (isinstance(b, LT) or isinstance(b, Trafo)):  # LT, Trafo <- Barra
            id = GRID[coords[0], coords[1]].id
            for POS, BAR in enumerate(BARRAS):
                if BAR.id == id:
                    BARRAS[POS] = 0
                    BARRAS = np.delete(BARRAS, BARRAS[POS])
                    N -= 1
            for ID in range(N):
                BARRAS[ID].id = ID
        else:
            if isinstance(b, Barra):  # free square
                BARRAS = np.append(BARRAS, b)
                N += 1
        GRID[coords[0], coords[1]] = b
        print(BARRAS)

    def update_element(self, inspector):
        """Updates element parameters in GRID. Isolated function from update GRID"""
        global GRID
        coords = MANIPULATOR['coords'][0], MANIPULATOR['coords'][1]
        element = GRID[coords[0]][coords[1]]
        if MANIPULATOR['info'] == 'slack':  # SLACK
            VBarraSL, VBaseSL, deltaBarraSL, PlBarraSL, QlBarraSL = inspector
            element.V = complex(VBarraSL[0].text)
            element.Vbase = float(VBaseSL[0].text)
            element.delta = float(deltaBarraSL[0].text)
            element.pl = float(PlBarraSL[0].text)
            element.ql = float(QlBarraSL[0].text)
            print(element.V, element.Vbase, element.delta, element.pl, element.ql)
        if MANIPULATOR['info'] == 'lt':  # LT
            lLT, rhoLT, rLT, D12LT, D23LT, D31LT, D31LT, dLT, mLT = inspector
            element.l = float(lLT[0].text)  # \ell
            element.rho = float(rhoLT[0].text)  # \rho
            element.r = float(rLT[0].text)  # r
            element.D = [float(D12LT[0].text), float(D23LT[0].text), float(D31LT[0].text)]  # D
            element.d = float(dLT[0].text)  # d
            element.m = float(mLT[0].text)  # m
            print(element.l, element.rho, element.r, element.D, element.d, element.m)
        if MANIPULATOR['info'] == 'pq':  # BARRAPQ
            PBarraPQ, QBarraPQ = inspector
            element.pl = float(PBarraPQ[0].text)  # PL
            element.ql = float(QBarraPQ[0].text)  # QL
            print('PL: {0} QL: {1}'.format(element.pl, element.ql))
        if MANIPULATOR['info'] == 'pv':  # BARRAPV
            VBarraPV, PgBarraPV, PlBarraPV, QlBarraPV = inspector
            print(element)
            element.V = complex(VBarraPV[0].text)  # V
            element.pg = float(PgBarraPV[0].text)  # PG
            element.pl = float(PlBarraPV[0].text)  # PL
            element.ql = float(QlBarraPV[0].text)  # QL
            print('V: {0} PG: {1} PL: {2} QL: {3}'.format(element.V, element.pg, element.pl, element.ql))
        if MANIPULATOR['info'] == 'trafo':  # TRAFO
            # TODO: como será com os trafos?
            pass


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

    def report(self, BARRAS):
        doc = Document('log')
        log(doc, BARRAS)
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
