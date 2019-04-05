from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button

presentation = Builder.load_file('./interface.kv')


class Interface(FloatLayout):
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