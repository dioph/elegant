from kivy.app import App
from kivy.config import Config
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from pylatex import Document

from aspy.core import *
from aspy.log import log
from aspy.methods import *

Config.set('graphics', 'width', '1500')
Config.set('graphics', 'height', '750')

# GLOBAL VARIABLES:
# DETERMINE UNIVOCALLY THE CURRENT SYSTEM STATE

N = 1   # NUMERO DE BARRAS
BARRAS = np.zeros(N, object)
LINHAS = []
GRID = np.zeros((10, 10), object)
SLACK = BarraSL()
GRID[4, 0] = SLACK
BARRAS[0] = SLACK
SECTORS = np.zeros((1, 1), bool)
SECTOR_IDS = np.ones((10, 10), int) * -1
SECTOR_IDS[4, 0] = 0
TOTAL = 1


def BFS(source):
    visitados = []
    q = [source]
    while len(q) > 0:
        current = q.pop()
        vizinhos = np.arange(TOTAL, dtype=int)[SECTORS[current]]
        vizinhos = np.array([v for v in vizinhos if v not in visitados])
        for v in vizinhos:
            q.append(v)
        visitados.append(current)
    return visitados


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

        else:
            # OPEN INSPECT ELEMENT
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
            for k in range(6):
                toplevel.children[k].visible = mask[k]
                toplevel.children[k].coords = square.coords
                i, j = square.coords
                # UPDATE INSPECT LABELS
                if mask[k] and k > 0:
                    for key in GRID[i, j].__dict__.keys():
                        if key is 'm' or key is 'barra_id':
                            setattr(toplevel.children[k], key, getattr(GRID[i, j], key))
                        else:
                            setattr(toplevel.children[k], key, float('{:.6g}'.format(getattr(GRID[i, j], key))))

    def update(self):
        S = np.zeros((N, 2), float)
        V0 = np.ones(N, complex)
        Y = np.zeros((N, N), complex)
        print('visitados =', BFS(0))
        # Calcula Ybarra:
        for l in LINHAS:
            lt, i, j = l
            node1 = None
            node2 = None
            if j > 0 and isinstance(GRID[i, j - 1], Barra):
                node1 = GRID[i, j - 1].barra_id
            if j < 9 and isinstance(GRID[i, j + 1], Barra):
                node2 = GRID[i, j + 1].barra_id
            if node1 is not None:
                Y[node1, node1] += lt.vbase**2/(lt.Z * 1e8) + (lt.Y * lt.vbase**2)/2e8
            if node2 is not None:
                Y[node2, node2] += lt.vbase**2/(lt.Z * 1e8) + (lt.Y * lt.vbase**2)/2e8
            if node1 is not None and node2 is not None:
                Y[node1, node2] -= lt.vbase**2/(lt.Z * 1e8)
                Y[node2, node1] -= lt.vbase**2/(lt.Z * 1e8)
        print('Ybarra =', Y)
        # Caclula S e V0:
        for i in range(N):
            S[i, :] = BARRAS[i].P/1e8, BARRAS[i].Q/1e8
            if isinstance(BARRAS[i], BarraPV):
                V0[i] = BARRAS[i].v / BARRAS[i].vbase
                S[i, 1] = np.nan
            if isinstance(BARRAS[i], BarraSL):
                V0[i] = BARRAS[i].v * np.exp(1j * BARRAS[i].delta * np.pi/180) / BARRAS[i].vbase
                S[i, :] = np.nan, np.nan
        print('S0 =', S)
        print('V0 =', V0)
        # Calcula V e atualiza:
        V = gauss_seidel(Y, V0, S, eps=1e-3, nmax=1000)
        Scalc = V * np.conjugate(np.dot(Y, V))
        print('Scalc =', Scalc)
        for i in range(N):
            BARRAS[i].v = np.abs(V[i]) * BARRAS[i].vbase
            BARRAS[i].delta = np.angle(V[i]) * 180/np.pi
            if isinstance(BARRAS[i], BarraPV):
                BARRAS[i].qg = np.imag(Scalc[i] * 1e8) + BARRAS[i].ql
            if isinstance(BARRAS[i], BarraSL):
                BARRAS[i].pg = np.real(Scalc[i] * 1e8) + BARRAS[i].pl
                BARRAS[i].qg = np.imag(Scalc[i] * 1e8) + BARRAS[i].ql
        # UPDATE INSPECT LABELS
        toplevel = self.children[0].children[0]
        for k in range(6):
            if toplevel.children[k].visible and k > 0:
                i, j = toplevel.children[k].coords
                for key in GRID[i, j].__dict__.keys():
                    if key is 'm' or key is 'barra_id':
                        setattr(toplevel.children[k], key, getattr(GRID[i, j], key))
                    else:
                        setattr(toplevel.children[k], key, float('{:.6g}'.format(getattr(GRID[i, j], key))))
        print('UPDATED')

    def edited_element(self, inspect, key, value):
        setattr(inspect, key, value)
        i, j = inspect.coords
        element = GRID[i, j]
        for key in element.__dict__.keys():
            setattr(element, key, getattr(inspect, key))
        self.update()
        print('EDITED {0},{1}'.format(i, j))

    def removed_element(self, coords):
        i, j = coords
        element = GRID[i, j]
        if isinstance(element, Barra):
            pass
        if isinstance(element, LT):
            pass
        GRID[i, j] = 0
        SECTOR_IDS[i, j] = -1

    def added_element(self, element, coords):
        global BARRAS, N, LINHAS, SECTORS, TOTAL
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

        if isinstance(element, Barra):
            BARRAS = np.append(BARRAS, [element])
            element.barra_id = N
            N = N + 1

        if isinstance(element, LT):
            LINHAS.append([element, i, j])

        print('Barras:', BARRAS)
        print('Linhas:', LINHAS)
        print('Sectors:', SECTORS)
        print('IDs:', SECTOR_IDS)
        print('ADDED')

    def extend(self, inspect, grid, add):
        i, j = inspect.coords
        element = GRID[i, j]
        sector_id = SECTOR_IDS[i, j]
        GRID[i + add, j] = element
        SECTOR_IDS[i + add, j] = sector_id
        k = (9 - i) * 10 + (9 - j)
        bkg_normal = grid[k].background_normal
        bkg_down = grid[k].background_down
        info = grid[k].info
        k = (9 - (i+add)) * 10 + (9 - j)
        grid[k].background_normal = bkg_normal
        grid[k].background_down = bkg_down
        grid[k].info = info

    def report(self):
        """Generates report when required in execution"""
        doc = Document('log')
        log(doc, BARRAS, LINHAS)
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
