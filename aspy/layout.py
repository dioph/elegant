import kivy
from kivy.uix import *
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout


presentation = Builder.load_file('./interface.kv')


class Interface(FloatLayout):
    def update_grid(self, b11, r_elements):
        # if elements[0].state == 'down':
        #     b11.text = elements[0].text
        # pass
        print(r_elements.children.state)


class InterfaceApp(App):
    def build(self):
        return Interface()


if __name__ == '__main__':
    InterfaceApp().run()