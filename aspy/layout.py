from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button

presentation = Builder.load_file('./interface.kv')


class Interface(FloatLayout):
    def variables(self):
        """
        Called as a contructor but only for used variables
        """
        self.SYM = None

    def add_grid(self, grid):
        """
        Initializes the grid
        """
        for i in range(0, grid.cols):
            for j in range(0, grid.rows):
                grid.add_widget(Button())

        for child in grid.children:
            child.bind(on_press=self.update_grid)  # passes child as an argument

    def get_pressed_toggle_btn_symbol(self, elements):
        """
        Returns the text of the current (pressed) ToggleButton
        """
        for e in elements.children:
            if e.state == 'down':
                self.SYM = e.text
                break
            else:
                self.SYM = None

    def update_grid(self, child):
        print(self.SYM)
        """
        Updates the button icon in the grid
        :param child: the button in the grid to be updated
        """
        try:
            if self.SYM is not None:
                child.text = self.SYM
        except AttributeError:
            pass


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()