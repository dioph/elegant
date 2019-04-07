import numpy as np
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout

presentation = Builder.load_file('./interface.kv')


class Interface(FloatLayout):
    def __init__(self):
        super(Interface, self).__init__()
        self.n = 0
        self.Y = np.zeros((self.n, self.n))
        self.grid = np.zeros((10, 10), dtype=object)

    def add_grid(self, grid, elements):
        """Initializes the grid

        Parameters
        ----------
        grid: the grid to be initialized
        elements: the grid of togglebuttons
        """
        for i in range(grid.cols):
            for j in range(grid.rows):
                grid.add_widget(Button())

        for square in grid.children:
            square.bind(on_press=lambda x: self.update_grid(x, elements))

    def update_grid(self, square, elements):
        """Updates the button icon in the grid

        Parameters
        ----------
        square: the position in the grid to be updated
        elements: the grid of togglebuttons
        """
        for child in elements.children:
            if isinstance(child, Button):
                if child.state == 'down':
                    square.text = child.text
                    break
                else:
                    square.text = ""


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()
