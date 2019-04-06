from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton

presentation = Builder.load_file('./interface.kv')



class Interface(FloatLayout):
    def add_grid(self, grid, elements):
        """Initializes the grid"""
        for i in range(grid.cols):
            for j in range(grid.rows):
                grid.add_widget(Button())

        for child in grid.children:
            child.bind(on_press=lambda x: self.update_grid(x, elements))
        print('ok')

    def update_grid(self, child, elements):
        """
        Updates the button icon in the grid
        :param child: the button in the grid to be updated
        """
        for toggleButton in elements.children:
            if isinstance(toggleButton, ToggleButton):
                if toggleButton.state == 'down':
                    child.text = toggleButton.text
                    break
                else:
                    child.text = ""


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()