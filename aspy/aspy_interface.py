from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

class Core(Screen):
    pass

class SimulationControl(Screen):
    pass

class ScreenManagement(ScreenManager):
    pass

presentation = Builder.load_file("aspy_interface.kv")

class AspyApp(App):
    def build(self):
        return presentation

if __name__ == '__main__':
    AspyApp().run()