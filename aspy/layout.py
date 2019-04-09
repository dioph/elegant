from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout

from aspy.core import *
from aspy.methods import *

N = 0
Y = np.zeros((N, N), complex)
V = np.zeros(N, complex)
BARRAS = np.zeros(N, object)
GRID = np.zeros((10, 10), object)
SLACK = BarraSL()


def insert_barra(b, coords):
    global N
    GRID[coords[0], coords[1]] = b
    N += 1
    BARRAS[N] = b


def insert_LT(coords, l, r, D, d, m):
    lt = LT(l=l, r=r, D=D, d=d, m=m)
    GRID[coords[0], coords[1]] = lt
    add_line()


def add_line():
    pass


def insert_trafo():
    pass


def update():
    """For all-purposes update function

    Parameters
    ----------

    Returns
    -------

    """
    V = gauss_seidel(Y, V0, S)
    for i in range(N):
        BARRAS[i].V = V[i]


#insert_barra(SLACK, [4, 0])


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
                    square.background_normal = child.background_normal
                    square.background_down = child.background_down
                    square.info = child.info
                    break
        else:
            print(square.coords)
            if square.info == 'lt':  # LT
                toplevel.children[0].visible = False
                toplevel.children[1].visible = False
                toplevel.children[2].visible = True
            if square.info == 'pq':  # Barra
                toplevel.children[0].visible = False
                toplevel.children[1].visible = True
                toplevel.children[2].visible = False


presentation = Builder.load_file('./interface.kv')


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()
