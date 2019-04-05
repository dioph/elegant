from kivy.uix.widget import Widget

from .core import *


class System(Widget):
    def __init__(self):
        super(System, self).__init__()
        self.n = 0
        self.Y = np.zeros((self.n, self.n))
        self.grid = np.zeros((10, 10), dtype=object)

    def update(self):
        pass

    def update_node(self):
        pass

    def update_line(self, i, j):
        node1 = None
        node2 = None
        if isinstance(self.grid[i, j-1], Barra) and j > 0:
            node1 = self.grid[i, j-1].id
        if isinstance(self.grid[i, j - 1], Barra) and j < self.n - 1:
            node2 = self.grid[i, j+1].id
        lt = self.grid[i, j]
        self.add_line(node1, node2, lt)

    def add_node(self):
        self.n = self.n + 1
        Ynew = np.zeros((self.n, self.n))
        Ynew[:-1, :-1] = self.Y
        self.Y = Ynew

    def add_line(self, node1, node2, lt):
        if node1 is not None and node2 is not None:
            self.Y[node1][node2] -= 1/lt.Z
            self.Y[node2][node1] -= 1/lt.Z
        if node1 is not None:
            self.Y[node1][node1] += 1/lt.Z + lt.Y/2
        if node2 is not None:
            self.Y[node2][node2] += 1/lt.Z + lt.Y/2
