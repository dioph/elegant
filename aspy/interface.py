from kivy.app import App
#kivy.require("1.0")
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Line
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

# Widgets é a classe pai. Referenciar a classe pai significa adicionar filhos, que é o que é feito no arquivo .kv

class MainScreen(Screen):
    pass

class AnotherScreen(Screen):
    pass

class ScreenManagement(ScreenManager):
    pass

presentation = Builder.load_file("aspy2.kv")

class aspy2(App):
    def build(self):
        return presentation

if __name__ == '__main__':
    aspy2().run()