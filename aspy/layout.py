from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout


presentation = Builder.load_file('./interface.kv')


class Interface(FloatLayout):
    def update_grid(self, place, r_elements):
        for child in r_elements.children:
            if child.state is 'down':
                place.text = child.text
                break


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()