# НАСТРОЙКА МОБИЛЬНОГО ДВИЖКА (СТРОГО В САМЫЙ ВЕРХ ФАЙЛА)
from kivy.config import Config
Config.set('input', 'mouse', 'mouse') # Намертво отключаем красные точки мультитача

import json
import os
import random
import shutil
from datetime import datetime, timedelta

# Кроссплатформенные компоненты Kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.scatter import Scatter
from kivy.uix.stencilview import StencilView
from kivy.graphics import Color, Rectangle
from PIL import Image as PILImg

DATA_FILE = "tracker_data.json"

class DataManager:
    @staticmethod
    def load_data():
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "task_history" not in data: data["task_history"] = {}
            if "shop_limits" not in data: data["shop_limits"] = {}
            if "custom_rewards" not in data: data["custom_rewards"] = []
            if "custom_history" not in data: data["custom_history"] = []
            return data
        return {
            "days": 0, "coins": 0, "total_earned": 0, "last_month": datetime.now().month,
            "task_history": {}, "shop_limits": {}, "custom_rewards": [], "custom_history": []
        }

    @staticmethod
    def save_data(days, coins, total_earned, last_month, task_history, shop_limits=None, custom_rewards=None, custom_history=None):
        if shop_limits is None: shop_limits = {}
        if custom_rewards is None: custom_rewards = []
        if custom_history is None: custom_history = []
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "days": days, "coins": coins, "total_earned": total_earned,
                "last_month": last_month, "task_history": task_history,
                "shop_limits": shop_limits, "custom_rewards": custom_rewards,
                "custom_history": custom_history
            }, f, ensure_ascii=False, indent=4)


# --- ЧАСТЬ 2. ГЛАВНОЕ МЕНЮ (МОБИЛЬНЫЙ ГРАНЖ-СТИЛЬ С ЗАЩИТОЙ ОТ МИСКЛИКОВ) ---
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_layout = BoxLayout(orientation='vertical')

        # Настройка мягкого матово-черного фона для AMOLED экранов
        with self.main_layout.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.rect = Rectangle(size=self.main_layout.size, pos=self.main_layout.pos)
        self.main_layout.bind(size=self._update_rect, pos=self._update_rect)

        root_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        layout.add_widget(Label(
            text="[ туман внутри ]\n+----------------------+",
            font_size='22sp', bold=True, halign='center',
            size_hint_y=None, height=80, color=(0.8, 0.8, 0.8, 1)
        ))

        # Блок статистики (Опыт считается скрытно в коде)
        self.stats_label = Label(
            text="загрузка...", font_size='15sp', halign='center', valign='middle',
            size_hint_y=None, height=110, color=(0.6, 0.6, 0.6, 1)
        )
        self.stats_label.bind(size=self.stats_label.setter('text_size'))
        layout.add_widget(self.stats_label)

        # Крупные кнопки навигации, удобные для пальцев на смартфоне
        btn_tasks = Button(
            text="[ задачи ]", font_size='16sp', size_hint_y=None, height=60,
            background_normal='', background_color=(0.2, 0.22, 0.24, 1), color=(0.8, 0.8, 0.8, 1)
        )
        btn_tasks.bind(on_press=self.go_to_tasks)
        layout.add_widget(btn_tasks)

        btn_shop = Button(
            text="[ магазин ]", font_size='16sp', size_hint_y=None, height=60,
            background_normal='', background_color=(0.18, 0.2, 0.22, 1), color=(0.8, 0.8, 0.8, 1)
        )
        btn_shop.bind(on_press=self.go_to_shop)
        layout.add_widget(btn_shop)

        btn_custom_rewards = Button(
            text="[ копилка ]", font_size='16sp', size_hint_y=None, height=60,
            background_normal='', background_color=(0.15, 0.16, 0.18, 1), color=(0.8, 0.8, 0.8, 1)
        )
        btn_custom_rewards.bind(on_press=self.go_to_custom_rewards)
        layout.add_widget(btn_custom_rewards)

        self.btn_clean = Button(
            text="", font_size='16sp', size_hint_y=None, height=60,
            background_normal='', color=(0.8, 0.8, 0.8, 1)
        )
        self.btn_clean.bind(on_press=self.claim_clean_day)
        layout.add_widget(self.btn_clean)

        self.btn_reset = Button(
            text="", font_size='13sp', size_hint_y=None, height=50,
            background_normal='', color=(0.5, 0.5, 0.5, 1)
        )
        self.btn_reset.bind(on_press=self.confirm_reset_popup)
        layout.add_widget(self.btn_reset)

        root_scroll.add_widget(layout)
        self.main_layout.add_widget(root_scroll)
        self.add_widget(self.main_layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def get_rank(self, total_earned):
        if total_earned < 200:
            return "гуль C ранга"
        elif total_earned < 600:
            return "гуль B ранга"
        elif total_earned < 1500:
            return "гуль A ранга"
        elif total_earned < 2300:
            return "гуль S ранга"
        elif total_earned < 3200:
            return "гуль S+ ранга"
        elif total_earned < 5000:
            return "гуль SS ранга"
        else:
            return "гуль SSS ранга"

    def check_monthly_reset(self):
        app = App.get_running_app()
        current_month = datetime.now().month
        if current_month != app.last_month:
            app.total_earned += 1000
            app.coins = 0
            app.days_clean = 0
            app.last_month = current_month
            DataManager.save_data(app.days_clean, app.coins, app.total_earned, app.last_month, app.task_history,
                                  app.shop_limits, app.custom_rewards, app.custom_history)

    def on_enter(self):
        self.check_monthly_reset()
        self.update_event = Clock.schedule_interval(self.update_menu_ui, 1)
        self.update_menu_ui(0)

    def on_leave(self):
        Clock.unschedule(self.update_event)

    def update_menu_ui(self, dt):
        app = App.get_running_app()
        rank = self.get_rank(app.total_earned)

        self.stats_label.text = (
            f" {rank}\n"
            f"дней серии: {app.days_clean}\n"
            f"{app.coins} осколков"
        )

        now = datetime.now()
        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        td = tomorrow - now
        hours, remainder = divmod(int(td.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_until_midnight = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        today_date = now.strftime("%Y-%m-%d")

        # КД кнопки «День без слабостей»
        last_clean_date = app.task_history.get("main_clean_day_button")
        if last_clean_date == today_date:
            self.btn_clean.disabled = True
            self.btn_clean.text = f"[ откат дня. осталось: {time_until_midnight} ]"
            self.btn_clean.background_color = (0.1, 0.1, 0.1, 1)
            self.btn_clean.color = (0.4, 0.4, 0.4, 1)
        else:
            self.btn_clean.disabled = False
            self.btn_clean.text = "[ + ] день без слабостей"
            self.btn_clean.background_color = (0.22, 0.25, 0.22, 1)
            self.btn_clean.color = (0.8, 0.8, 0.8, 1)

        # КД кнопки срыва строго до 00:00:00 сегодняшнего дня
        last_reset_date = app.task_history.get("main_reset_streak_button")
        if last_reset_date == today_date:
            self.btn_reset.disabled = True
            self.btn_reset.text = f"[ срыв заблокирован. кд: {time_until_midnight} ]"
            self.btn_reset.background_color = (0.08, 0.08, 0.08, 1)
            self.btn_reset.color = (0.3, 0.3, 0.3, 1)
        else:
            self.btn_reset.disabled = False
            self.btn_reset.text = "== срыв =="
            self.btn_reset.background_color = (0.18, 0.12, 0.12, 1)
            self.btn_reset.color = (0.6, 0.5, 0.5, 1)

    def claim_clean_day(self, instance):
        app = App.get_running_app()
        app.days_clean += 1
        app.coins += 50
        app.total_earned += 50
        app.task_history["main_clean_day_button"] = datetime.now().strftime("%Y-%m-%d")
        DataManager.save_data(app.days_clean, app.coins, app.total_earned, app.last_month, app.task_history,
                              app.shop_limits, app.custom_rewards, app.custom_history)
        self.update_menu_ui(0)

    def confirm_reset_popup(self, instance):
        from kivy.uix.popup import Popup
        layout = BoxLayout(orientation='vertical', padding=15, spacing=12)
        layout.add_widget(Label(
            text="ты действительно сорвался?\nэто отбросит твой ранг на -1000 опыта.",
            font_size='14sp', halign='center', color=(0.8, 0.8, 0.8, 1)
        ))

        buttons_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        btn_yes = Button(text="да", background_normal='', background_color=(0.25, 0.15, 0.15, 1),
                         color=(0.8, 0.5, 0.5, 1))
        btn_no = Button(text="отмена", background_normal='', background_color=(0.2, 0.22, 0.24, 1),
                        color=(0.8, 0.8, 0.8, 1))

        buttons_layout.add_widget(btn_yes)
        buttons_layout.add_widget(btn_no)
        layout.add_widget(buttons_layout)

        popup = Popup(
            title="признание слабости", content=layout, size_hint=(0.85, 0.35),
            title_color=(0.7, 0.7, 0.7, 1), separator_color=(0.3, 0.3, 0.3, 1), background_color=(0.05, 0.05, 0.05, 1)
        )

        def execute_reset(inst):
            app = App.get_running_app()
            app.days_clean = 0
            app.total_earned = max(0, app.total_earned - 1000)
            app.coins += 1
            app.task_history["main_reset_streak_button"] = datetime.now().strftime("%Y-%m-%d")

            DataManager.save_data(app.days_clean, app.coins, app.total_earned, app.last_month, app.task_history,
                                  app.shop_limits, app.custom_rewards, app.custom_history)
            popup.dismiss()
            self.update_menu_ui(0)

        btn_yes.bind(on_press=execute_reset)
        btn_no.bind(on_press=popup.dismiss)
        popup.open()

    def go_back(self, instance):
        pass

    def go_to_tasks(self, instance):
        self.manager.current = 'tasks'

    def go_to_shop(self, instance):
        self.manager.current = 'shop'

    def go_to_custom_rewards(self, instance):
        self.manager.current = 'custom_rewards'


# --- ЧАСТЬ 3.1. ЭКРАН ЗАДАЧ (МОБИЛЬНАЯ ВЕРСИЯ С КАТЕГОРИЯМИ) ---
class TasksScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_layout = BoxLayout(orientation='vertical')

        with self.main_layout.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.rect = Rectangle(size=self.main_layout.size, pos=self.main_layout.pos)
        self.main_layout.bind(size=self._update_rect, pos=self._update_rect)

        self.main_layout.add_widget(Label(
            text="список испытаний", font_size='20sp', bold=True,
            size_hint_y=None, height=45, color=(0.8, 0.8, 0.8, 1)
        ))

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.task_list_layout = BoxLayout(orientation='vertical', spacing=8, size_hint_y=None)
        self.task_list_layout.bind(minimum_height=self.task_list_layout.setter('height'))

        self.categories = {
            "+--- порядок в доме ---+": [
                ("вынести мусор и проветрить", 5, "midnight"),
                ("помыть посуду", 10, "midnight"),
                ("уборать комнату)", 20, "midnight"),
            ],
            "+--- испытания тела ---+": [
                ("чистая вода натощак", 5, "midnight"),
                ("умыться и почистить зубы", 10, "midnight"),
                ("утренняя зарядка и растяжка", 15, "midnight"),
                ("прогулка", 0, "hours_2"),
                ("день без сладостей", 40, "midnight"),
                ("тренировка", 40, "midnight"),
            ],
            "+--- испытания разума ---+": [
                ("сделано дз", 30, "midnight"),
                ("написание кода/изучение python", 35, "midnight"),
                ("работа", 0, "hours_1"),
                ("день без ютуба и тт)", 50, "midnight"),
                ("день воздержания", 50, "midnight"),
            ],
            "+--- хобби ---+": [
                ("написать сэмпл", 20, "midnight"),
                ("написать рисунок/арт", 30, "midnight"),
                ("написать бит", 40, "midnight"),
            ],
            "+--- погружение в сон ---+": [
                ("изоляция от экранов за час до сна", 25, "midnight"),
                ("встать по первому будильнику", 30, "midnight"),
                ("встать без будильника", 35, "midnight"),
            ]
        }

        self.buttons_registry = {}

        for cat_name, tasks in self.categories.items():
            cat_label = Label(text=cat_name, font_size='14sp', size_hint_y=None, height=35, color=(0.6, 0.6, 0.6, 0.5))
            self.task_list_layout.add_widget(cat_label)

            for text, reward, cd_type in tasks:
                self.create_task_button(text, reward, cd_type)

            if cat_name == "+--- погружение в сон ---+":
                self.create_task_button("уснуть вовремя", 40, "midnight", is_sleep=True)

        scroll.add_widget(self.task_list_layout)
        self.main_layout.add_widget(scroll)

        btn_back = Button(
            text="<-- назад", font_size='14sp', size_hint_y=None, height=55,
            background_color=(0.15, 0.15, 0.15, 1), background_normal='', color=(0.7, 0.7, 0.7, 1)
        )
        btn_back.bind(on_press=self.go_back)
        self.main_layout.add_widget(btn_back)
        self.add_widget(self.main_layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = self.main_layout.size

    def create_task_button(self, text, reward, cd_type, is_sleep=False):
        btn = Button(
            text="", font_size='13sp', halign='center', size_hint_y=None, height=65,
            background_normal='', color=(0.8, 0.8, 0.8, 1)
        )
        btn.bind(
            on_press=lambda inst, b=btn, t=text, r=reward, ct=cd_type, s=is_sleep: self.handle_click(b, t, r, ct, s))
        self.task_list_layout.add_widget(btn)
        self.buttons_registry[text] = {"button": btn, "reward": reward, "cd_type": cd_type, "is_sleep": is_sleep}

    def get_sleep_target(self):
        app = App.get_running_app()
        steps = app.days_clean // 2
        start_time = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=24, minutes=30)
        target = start_time - timedelta(minutes=int(steps * 30))
        limit = datetime.combine(datetime.today(), datetime.min.time()) + timedelta(hours=22)
        return max(target, limit).strftime("%H:%M")

    def on_enter(self):
        self.update_event = Clock.schedule_interval(self.update_buttons_status, 1)
        self.update_buttons_status(0)

    def on_leave(self):
        Clock.unschedule(self.update_event)

    # --- ЧАСТЬ 3.2. ОБНОВЛЕНИЕ КНОПОК И ОКНА ВВОДА ВРЕМЕНИ ДЛЯ ЗАКАЗОВ ---
    def update_buttons_status(self, dt):
        app = App.get_running_app()
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        sleep_t = self.get_sleep_target()

        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        td_mid = tomorrow - now
        mid_str = f"{td_mid.seconds // 3600:02d}:{(td_mid.seconds % 3600) // 60:02d}:{td_mid.seconds % 60:02d}"

        for text, info in self.buttons_registry.items():
            btn = info["button"]
            reward = info["reward"]
            cd_type = info["cd_type"]

            display_text = text
            if info["is_sleep"]:
                display_text = f"уснуть до {sleep_t}"

            last_done_str = app.task_history.get(text)
            if last_done_str:
                if cd_type == "midnight" and last_done_str == today_str:
                    btn.disabled = True
                    btn.text = f"{display_text}\n[ доступно через: {mid_str} ]"
                    btn.background_color = (0.08, 0.08, 0.08, 1)
                    btn.color = (0.4, 0.4, 0.4, 1)
                    continue
                elif "hours_" in cd_type:
                    last_done = datetime.fromisoformat(last_done_str)
                    # ИСПРАВЛЕННЫЙ ФИКС: берем точный элемент из списка после split
                    hours_delta = int(cd_type.split("_")[1])
                    available_at = last_done + timedelta(hours=hours_delta)
                    if now < available_at:
                        td_rem = available_at - now
                        rem_str = f"{int(td_rem.total_seconds()) // 3600:02d}:{(int(td_rem.total_seconds()) % 3600) // 60:02d}:{int(td_rem.total_seconds()) % 60:02d}"
                        btn.disabled = True
                        btn.text = f"{display_text}\n[ кд. осталось: {rem_str} ]"
                        btn.background_color = (0.08, 0.08, 0.08, 1)
                        btn.color = (0.4, 0.4, 0.4, 1)
                        continue

            btn.disabled = False
            btn.background_color = (0.16, 0.18, 0.2, 1)
            btn.color = (0.8, 0.8, 0.8, 1)
            if cd_type == "midnight":
                btn.text = f"{display_text}\n[ +{reward} осколков ]"
            elif cd_type == "hours_2":
                btn.text = f"{display_text}\n[ динамическая награда | КД 2ч ]"
            elif cd_type == "hours_1":
                btn.text = f"{display_text}\n[ динамическая награда | КД 1ч ]"

    def handle_click(self, button, text, reward, cd_type, is_sleep):
        if text == "прогулка":
            self.show_walk_popup(text)
        elif text == "работа":
            self.show_order_popup(text)
        else:
            app = App.get_running_app()
            app.coins += reward
            app.total_earned += reward
            app.task_history[text] = datetime.now().strftime(
                "%Y-%m-%d") if cd_type == "midnight" else datetime.now().isoformat()
            DataManager.save_data(app.days_clean, app.coins, app.total_earned, app.last_month, app.task_history,
                                  app.shop_limits, app.custom_rewards, app.custom_history)
            self.update_buttons_status(0)

    def show_walk_popup(self, task_key):
        from kivy.uix.popup import Popup
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header.add_widget(
            Label(text="фиксация прогулки", font_size='15sp', bold=True, color=(0.7, 0.7, 0.7, 1), halign='left'))
        btn_close_popup = Button(text="[ X ]", size_hint_x=None, width=50, font_size='14sp', bold=True,
                                 background_normal='', background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close_popup)
        layout.add_widget(header)

        layout.add_widget(Label(text="сколько минут длилось блуждание?", font_size='14sp', color=(0.6, 0.6, 0.6, 1)))

        inp = TextInput(
            hint_text="введите минуты...", multiline=False, input_filter="int", size_hint_y=None, height=45,
            background_normal='', background_color=(0.12, 0.13, 0.15, 1), foreground_color=(1, 1, 1, 1),
            hint_text_color=(0.5, 0.5, 0.5, 1)
        )
        layout.add_widget(inp)

        btn_confirm = Button(text="[ зачесть ]", size_hint_y=None, height=45, background_normal='',
                             background_color=(0.2, 0.22, 0.24, 1), color=(0.8, 0.8, 0.8, 1))
        layout.add_widget(btn_confirm)

        popup = Popup(title="", title_size=0, content=layout, size_hint=(0.9, 0.42), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close_popup.bind(on_press=popup.dismiss)

        def process_walk(instance):
            if inp.text.strip():
                mins = int(inp.text.strip())
                if mins > 0:
                    app = App.get_running_app()
                    app.coins += mins
                    app.total_earned += mins
                    app.task_history[task_key] = datetime.now().isoformat()
                    DataManager.save_data(app.days_clean, app.coins, app.total_earned, app.last_month, app.task_history,
                                          app.shop_limits, app.custom_rewards, app.custom_history)
                    popup.dismiss()
                    self.update_buttons_status(0)

        btn_confirm.bind(on_press=process_walk)
        popup.open()

    def show_order_popup(self, task_key):
        from kivy.uix.popup import Popup
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header.add_widget(
            Label(text="работа", font_size='15sp', bold=True, color=(0.7, 0.7, 0.7, 1), halign='left'))
        btn_close_popup = Button(text="[ X ]", size_hint_x=None, width=50, font_size='14sp', bold=True,
                                 background_normal='', background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close_popup)
        layout.add_widget(header)

        state = {"loc": "studio"}
        btn_studio = Button(text="[X] в студии", size_hint_y=None, height=45, background_normal='',
                            background_color=(0.2, 0.22, 0.24, 1), color=(0.8, 0.8, 0.8, 1))
        btn_field = Button(text=" выезд (х2)", size_hint_y=None, height=45, background_normal='',
                           background_color=(0.12, 0.13, 0.15, 1), color=(0.5, 0.5, 0.5, 1))

        def set_studio(inst):
            state["loc"] = "studio"
            btn_studio.text = "[X] в студии";
            btn_studio.background_color = (0.2, 0.22, 0.24, 1);
            btn_studio.color = (0.8, 0.8, 0.8, 1)
            btn_field.text = " выезд (х2)";
            btn_field.background_color = (0.12, 0.13, 0.15, 1);
            btn_field.color = (0.5, 0.5, 0.5, 1)

        def set_field(inst):
            state["loc"] = "field"
            btn_studio.text = " в студии";
            btn_studio.background_color = (0.12, 0.13, 0.15, 1);
            btn_studio.color = (0.5, 0.5, 0.5, 1)
            btn_field.text = "[X] выезд(х2)";
            btn_field.background_color = (0.2, 0.22, 0.24, 1);
            btn_field.color = (0.8, 0.8, 0.8, 1)

        btn_studio.bind(on_press=set_studio);
        btn_field.bind(on_press=set_field)
        layout.add_widget(btn_studio)
        layout.add_widget(btn_field)

        layout.add_widget(Label(text="сколько времени работал?", font_size='14sp', color=(0.6, 0.6, 0.6, 1)))

        time_input_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        inp_hours = TextInput(hint_text="часы...", multiline=False, input_filter="int", background_normal='',
                              background_color=(0.12, 0.13, 0.15, 1), foreground_color=(1, 1, 1, 1),
                              hint_text_color=(0.4, 0.4, 0.4, 1))
        inp_mins = TextInput(hint_text="минуты...", multiline=False, input_filter="int", background_normal='',
                             background_color=(0.12, 0.13, 0.15, 1), foreground_color=(1, 1, 1, 1),
                             hint_text_color=(0.4, 0.4, 0.4, 1))
        time_input_layout.add_widget(inp_hours)
        time_input_layout.add_widget(inp_mins)
        layout.add_widget(time_input_layout)

        btn_confirm = Button(text="[ зафиксировать ]", size_hint_y=None, height=45, background_normal='',
                             background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
        layout.add_widget(btn_confirm)

        popup = Popup(title="", title_size=0, content=layout, size_hint=(0.9, 0.68), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close_popup.bind(on_press=popup.dismiss)

        def process_order(instance):
            raw_h = inp_hours.text.strip()
            raw_m = inp_mins.text.strip()
            hours = int(raw_h) if raw_h else 0
            minutes = int(raw_m) if raw_m else 0

            if hours > 0 or minutes > 0:
                total_hours = hours + (minutes / 60.0)
                multiplier = 50 if state["loc"] == "studio" else 100
                reward = int(total_hours * multiplier)

                app = App.get_running_app()
                app.coins += reward
                app.total_earned += reward
                app.task_history[task_key] = datetime.now().isoformat()
                DataManager.save_data(app.days_clean, app.coins, app.total_earned, app.last_month, app.task_history,
                                      app.shop_limits, app.custom_rewards, app.custom_history)
                popup.dismiss()
                self.update_buttons_status(0)

        btn_confirm.bind(on_press=process_order)
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'menu'


# --- ЧАСТЬ 4.1. ЭКРАН МАГАЗИНА (МОБИЛЬНАЯ РАЗМЕТКА И ТАЙМЕРЫ) ---
class ShopScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Адаптивный матово-чёрный фон под экраны смартфонов
        from kivy.graphics import Color, Rectangle
        with self.main_layout.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.rect = Rectangle(size=self.main_layout.size, pos=self.main_layout.pos)
        self.main_layout.bind(size=self._update_rect, pos=self._update_rect)

        root_scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.layout_inside = BoxLayout(orientation='vertical', padding=10, spacing=12, size_hint_y=None)
        self.layout_inside.bind(minimum_height=self.layout_inside.setter('height'))

        self.title_label = Label(
            text="магазин", font_size='20sp', bold=True, halign='center',
            size_hint_y=None, height=60, color=(0.8, 0.8, 0.8, 1)
        )
        self.layout_inside.add_widget(self.title_label)

        # --- БЛОК ВРЕМЕНИ ИГРЫ (НА САМОМ ВЕРХУ) ---
        self.time_status_label = Label(
            text="", font_size='13sp', color=(0.7, 0.7, 0.7, 1), halign='center', size_hint_y=None, height=85
        )
        self.layout_inside.add_widget(self.time_status_label)

        self.time_input = TextInput(
            text='', hint_text='введите количество минут игры...', multiline=False, input_filter='int',
            size_hint_y=None, height=45, background_color=(0.12, 0.13, 0.15, 1),
            foreground_color=(1, 1, 1, 1), hint_text_color=(0.4, 0.4, 0.4, 1)
        )
        self.layout_inside.add_widget(self.time_input)

        btn_buy_time = Button(
            text="[ выкупить время игры (1 мин = 2) ]", font_size='14sp', size_hint_y=None, height=55,
            background_normal='', background_color=(0.2, 0.22, 0.24, 1), color=(0.8, 0.8, 0.8, 1)
        )
        btn_buy_time.bind(on_press=self.buy_custom_time)
        self.layout_inside.add_widget(btn_buy_time)

        self.layout_inside.add_widget(Label(
            text="--- другие награды ---", font_size='13sp', color=(0.5, 0.5, 0.5, 1), halign='center',
            size_hint_y=None, height=30
        ))

        # База данных остальных наград по возрастанию стоимости
        self.rewards_data = [
            ("кино/сериала по минутам", 0, "series_dyn", "limit_180"),
            ("видео на youtube по минутам", 0, "youtube_dyn", "limit_180"),
            ("покупка сладостей", 120, "sweets_pack", "48"),
            ("покупка вредной еды", 250, "fastfood", "168"),
            ("скин или донат в игру", 500, "ingame_buy", "336"),
            ("полный день безделья и лени", 800, "lazy_day", "720")
        ]

        self.reward_buttons = {}
        for name, cost, item_id, cd_info in self.rewards_data:
            btn = Button(
                text="", font_size='13sp', halign='center', size_hint_y=None, height=55,
                background_normal='', color=(0.8, 0.8, 0.8, 1)
            )
            btn.bind(on_press=lambda inst, c=cost, i=item_id, cd=cd_info: self.handle_shop_click(c, i, cd))
            self.layout_inside.add_widget(btn)
            self.reward_buttons[item_id] = {"button": btn, "name": name, "cost": cost, "cd_info": cd_info}

        root_scroll.add_widget(self.layout_inside)
        self.main_layout.add_widget(root_scroll)

        btn_back = Button(
            text="<-- назад", font_size='14sp', size_hint_y=None, height=55,
            background_color=(0.15, 0.15, 0.15, 1), background_normal='', color=(0.7, 0.7, 0.7, 1)
        )
        btn_back.bind(on_press=self.go_back)
        self.main_layout.add_widget(btn_back)
        self.add_widget(self.main_layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = self.main_layout.size

    def on_enter(self):
        self.update_event = Clock.schedule_interval(self.update_shop_ui, 1)
        self.update_shop_ui(0)
        self.time_input.text = ''

    def on_leave(self):
        Clock.unschedule(self.update_event)

    def format_seconds(self, total_seconds):
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # --- ЧАСТЬ 4.2. ЖИВЫЕ ТАЙМЕРЫ И ОКНА ВЫКУПА МИНУТ ДЛЯ СМАРТФОНА ---
    def update_shop_ui(self, dt):
        app = App.get_running_app()
        self.title_label.text = f"обмен осколков \n(баланс: {app.coins} осколков)"
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Автосброс суточных лимитов выкупа строго в полночь
        if app.shop_limits.get("play_time_last_date") != today_str:
            app.shop_limits["play_minutes_bought"] = 0;
            app.shop_limits["play_time_last_date"] = today_str
        if app.shop_limits.get("series_last_date") != today_str:
            app.shop_limits["series_minutes_bought"] = 0;
            app.shop_limits["series_last_date"] = today_str
        if app.shop_limits.get("youtube_last_date") != today_str:
            app.shop_limits["youtube_minutes_bought"] = 0;
            app.shop_limits["youtube_last_date"] = today_str

        tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
        td_midnight = tomorrow - now
        time_until_midnight = f"{td_midnight.seconds // 3600:02d}:{(td_midnight.seconds % 3600) // 60:02d}:{td_midnight.seconds % 60:02d}"

        for item_id, info in self.reward_buttons.items():
            btn = info["button"]
            cd_info = info["cd_info"]

            btn.disabled = False
            btn.background_color = (0.16, 0.18, 0.2, 1)
            btn.color = (0.8, 0.8, 0.8, 1)

            if cd_info == "limit_180":
                spent = app.shop_limits.get(f"{item_id.split('_')[0]}_minutes_bought", 0)
                current_left = app.series_time_left if "series" in item_id else app.youtube_time_left
                time_left_str = self.format_seconds(current_left)

                if spent >= 180:
                    btn.disabled = True
                    btn.text = f"{info['name']}\nбаланс: {time_left_str} | [ лимит на сегодня исчерпан ]"
                    btn.background_color = (0.1, 0.1, 0.1, 1);
                    btn.color = (0.4, 0.4, 0.4, 1)
                else:
                    btn.text = f"{info['name']}\nбаланс: {time_left_str} [ куплено сегодня: {spent}/180 мин ]"
                continue

            last_bought_str = app.shop_limits.get(item_id)
            if last_bought_str and isinstance(last_bought_str, str):
                try:
                    last_bought = datetime.fromisoformat(last_bought_str)
                    available_at = last_bought + timedelta(hours=int(cd_info))

                    if now < available_at:
                        td_item = available_at - now
                        item_hours = int(td_item.total_seconds()) // 3600
                        item_mins = (int(td_item.total_seconds()) % 3600) // 60
                        item_secs = int(td_item.total_seconds()) % 60

                        btn.disabled = True
                        btn.text = f"{info['name']}\n[ лимит исчерпан. обновление через: {item_hours:02d}:{item_mins:02d}:{item_secs:02d} ]"
                        btn.background_color = (0.1, 0.1, 0.1, 1);
                        btn.color = (0.4, 0.4, 0.4, 1)
                        continue
                except Exception:
                    pass

            btn.text = f"{info['name']}\nцена: {info['cost']} осколков (доступно: 1/1)"

        play_time_str = self.format_seconds(app.game_time_left)
        spent_today = app.shop_limits.get("play_minutes_bought", 0)

        self.time_status_label.text = (
            f"--- купить игровое время ---\n"
            f"осталось играть: {play_time_str}\n"
            f"сегодня выкуплено: {spent_today} / 180 мин.\n"
            f"[ сброс лимита через: {time_until_midnight} ]"
        )

    def handle_shop_click(self, cost, item_id, cd_info):
        if cd_info == "limit_180":
            self.show_time_purchase_popup(item_id)
        else:
            app = App.get_running_app()
            if app.coins >= cost:
                app.coins -= cost
                app.shop_limits[item_id] = datetime.now().isoformat()
                app.save_all_data()
                self.update_shop_ui(0)
            else:
                self.show_no_coins_popup(cost - app.coins)

    def show_time_purchase_popup(self, item_id):
        from kivy.uix.popup import Popup
        is_series = "series" in item_id
        type_label = "кино/сериалов" if is_series else "youtube"
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header.add_widget(
            Label(text=f"контракт: {type_label}", font_size='15sp', bold=True, color=(0.7, 0.7, 0.7, 1), halign='left'))
        btn_close_popup = Button(text="[ X ]", size_hint_x=None, width=50, font_size='14sp', bold=True,
                                 background_normal='', background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close_popup)
        layout.add_widget(header)

        layout.add_widget(
            Label(text=f"сколько минут {type_label} покупаешь?\n[ курс: 1 минута = 1 осколок]", font_size='13sp',
                  halign='center', color=(0.6, 0.6, 0.6, 1)))

        inp = TextInput(hint_text="число минут...", multiline=False, input_filter="int", size_hint_y=None, height=45,
                        background_normal='', background_color=(0.12, 0.13, 0.15, 1), foreground_color=(1, 1, 1, 1),
                        hint_text_color=(0.5, 0.5, 0.5, 1))
        layout.add_widget(inp)

        btn_confirm = Button(text="[ подтвердить покупку ]", size_hint_y=None, height=45, background_normal='',
                             background_color=(0.2, 0.22, 0.24, 1), color=(0.8, 0.8, 0.8, 1))
        layout.add_widget(btn_confirm)

        popup = Popup(title="", title_size=0, content=layout, size_hint=(0.9, 0.42), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close_popup.bind(on_press=popup.dismiss)

        def process_time_buy(instance):
            raw_text = inp.text.strip()
            if not raw_text: return
            minutes = int(raw_text)
            if minutes <= 0: return

            app = App.get_running_app()
            prefix = "series" if is_series else "youtube"
            spent = app.shop_limits.get(f"{prefix}_minutes_bought", 0)

            if spent + minutes > 180:
                self.title_label.text = f"лимит превышен. осталось: {180 - spent} мин."
                popup.dismiss();
                return

            if app.coins >= minutes:
                app.coins -= minutes
                app.shop_limits[f"{prefix}_minutes_bought"] = spent + minutes
                app.shop_limits[f"{prefix}_last_date"] = datetime.now().strftime("%Y-%m-%d")

                if is_series:
                    app.series_time_left += (minutes * 60)
                else:
                    app.youtube_time_left += (minutes * 60)

                app.save_all_data()
                popup.dismiss()
                self.update_shop_ui(0)
            else:
                popup.dismiss();
                self.show_no_coins_popup(minutes - app.coins)

        btn_confirm.bind(on_press=process_time_buy)
        popup.open()

    def buy_custom_time(self, instance):
        app = App.get_running_app()
        raw_text = self.time_input.text.strip()
        if not raw_text: return
        minutes = int(raw_text)
        if minutes <= 0: return

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        if app.shop_limits.get("play_time_last_date") != today_str:
            app.shop_limits["play_minutes_bought"] = 0

        spent_today = app.shop_limits.get("play_minutes_bought", 0)

        if spent_today + minutes > 180:
            allowed = 180 - spent_today
            self.title_label.text = f"превышен лимит. доступно: {allowed} мин.";
            return

        cost = minutes * 2
        if app.coins >= cost:
            app.coins -= cost
            app.game_time_left += (minutes * 60)
            app.shop_limits["play_minutes_bought"] = spent_today + minutes
            app.shop_limits["play_time_last_date"] = today_str
            app.save_all_data()
            self.update_shop_ui(0)
            self.time_input.text = ''
        else:
            self.show_no_coins_popup(cost - app.coins)

    def show_no_coins_popup(self, missing_amount):
        from kivy.uix.popup import Popup
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header.add_widget(
            Label(text="отказ магазина", font_size='15sp', bold=True, color=(0.7, 0.7, 0.7, 1), halign='left'))
        btn_close_popup = Button(text="[ X ]", size_hint_x=None, width=50, font_size='14sp', bold=True,
                                 background_normal='', background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close_popup)
        layout.add_widget(header)
        layout.add_widget(
            Label(text=f"недостаточно осколков.\nнужно еще: {missing_amount}", font_size='14sp', halign='center',
                  color=(0.6, 0.6, 0.6, 1)))
        btn_ok = Button(text="[ ок ]", size_hint_y=None, height=45, background_normal='', background_color=(1, 1, 1, 1),
                        color=(0, 0, 0, 1))
        layout.add_widget(btn_ok)
        popup = Popup(title="", title_size=0, content=layout, size_hint=(0.85, 0.36), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close_popup.bind(on_press=popup.dismiss);
        btn_ok.bind(on_press=popup.dismiss)
        popup.open()

    def go_back(self, instance):
        self.manager.current = 'menu'


# --- ЧАСТЬ 5.1. ЭКРАН СЕЙФА С ОБЩИМ КОШЕЛЬКОМ (ИНТЕРФЕЙС И РАЗМЕТКА) ---
# ==============================================================================
# --- ПОЛНЫЙ МОНОЛИТНЫЙ КЛАСС СЕЙФА НАЛИЧНЫХ НАГРАД (БЕЗ ВЫЛЕТОВ И ЛАГОВ) ---
# ==============================================================================
class CustomRewardsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = "active"
        self.selected_image_path = ""  # Сюда пишется чистый путь после обрезки Pillow

        self.main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        with self.main_layout.canvas.before:
            Color(0.05, 0.05, 0.05, 1)
            self.rect = Rectangle(size=self.main_layout.size, pos=self.main_layout.pos)
        self.main_layout.bind(size=self._update_rect, pos=self._update_rect)

        # --- БЛОК ОБЩЕГО КОШЕЛЬКА (НА САМОМ ВЕРХУ) ---
        wallet_box = BoxLayout(orientation='vertical', size_hint_y=None, height=90, spacing=5)
        self.balance_label = Label(
            text="В конверте: 0 руб.", font_size='17sp', bold=True, color=(0.6, 0.8, 0.6, 1)
        )
        btn_add_to_wallet = Button(
            text="[ + пополнить конверт ]", font_size='14sp', bold=True,
            background_normal='', background_color=(0.15, 0.25, 0.15, 1), color=(0.8, 1, 0.8, 1)
        )
        btn_add_to_wallet.bind(on_press=self.show_wallet_deposit_popup)
        wallet_box.add_widget(self.balance_label)
        wallet_box.add_widget(btn_add_to_wallet)
        self.main_layout.add_widget(wallet_box)

        # Переключатель вкладок
        tab_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        self.btn_tab_active = Button(text="[ конверт: наличные ]", background_normal='',
                                     background_color=(0.15, 0.16, 0.18, 1), color=(1, 1, 1, 1))
        self.btn_tab_history = Button(text="архив покупок", background_normal='',
                                      background_color=(0.08, 0.08, 0.08, 1), color=(0.5, 0.5, 0.5, 1))

        self.btn_tab_active.bind(on_press=lambda x: self.switch_tab("active"))
        self.btn_tab_history.bind(on_press=lambda x: self.switch_tab("history"))
        tab_box.add_widget(self.btn_tab_active)
        tab_box.add_widget(self.btn_tab_history)
        self.main_layout.add_widget(tab_box)

        # Блок создания новой цели
        self.creation_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None, height=180)
        self.name_in = TextInput(hint_text="название...", multiline=False, size_hint_y=None,
                                 height=38,
                                 background_normal='', background_color=(0.12, 0.13, 0.15, 1),
                                 foreground_color=(1, 1, 1, 1), hint_text_color=(0.4, 0.4, 0.4, 1))
        self.price_in = TextInput(hint_text="цена...", multiline=False, input_filter="int",
                                  size_hint_y=None, height=38,
                                  background_normal='', background_color=(0.12, 0.13, 0.15, 1),
                                  foreground_color=(1, 1, 1, 1), hint_text_color=(0.4, 0.4, 0.4, 1))

        self.btn_photo_pick = Button(
            text="[ выбрать фото ]", size_hint_y=None, height=38,
            background_normal='', background_color=(0.14, 0.16, 0.18, 1), color=(0.6, 0.7, 0.6, 1)
        )
        self.btn_photo_pick.bind(on_press=self.open_file_chooser)

        btn_add = Button(text="[ + ] новая цель", font_size='14sp', size_hint_y=None, height=45,
                         background_normal='', background_color=(0.2, 0.22, 0.24, 1), color=(0.8, 0.8, 0.8, 1))
        btn_add.bind(on_press=self.add_reward)

        self.creation_box.add_widget(self.name_in)
        self.creation_box.add_widget(self.price_in)
        self.creation_box.add_widget(self.btn_photo_pick)
        self.creation_box.add_widget(btn_add)
        self.main_layout.add_widget(self.creation_box)

        # Зона скролла карточек
        self.scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.rewards_container = BoxLayout(orientation='vertical', spacing=12, size_hint_y=None)
        self.rewards_container.bind(minimum_height=self.rewards_container.setter('height'))
        self.scroll_view.add_widget(self.rewards_container)
        self.main_layout.add_widget(self.scroll_view)

        btn_back = Button(text="<-- назад", size_hint_y=None, height=55, background_normal='',
                          background_color=(0.15, 0.15, 0.15, 1), color=(0.7, 0.7, 0.7, 1))
        btn_back.bind(on_press=self.go_back)
        self.main_layout.add_widget(btn_back)
        self.add_widget(self.main_layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = self.main_layout.size

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        if self.creation_box in self.main_layout.children:
            self.main_layout.remove_widget(self.creation_box)
        if tab_name == "active":
            self.btn_tab_active.background_color = (0.15, 0.16, 0.18, 1);
            self.btn_tab_active.color = (1, 1, 1, 1)
            self.btn_tab_history.background_color = (0.08, 0.08, 0.08, 1);
            self.btn_tab_history.color = (0.5, 0.5, 0.5, 1)
            self.main_layout.add_widget(self.creation_box, index=2)
        else:
            self.btn_tab_active.background_color = (0.08, 0.08, 0.08, 1);
            self.btn_tab_active.color = (0.5, 0.5, 0.5, 1)
            self.btn_tab_history.background_color = (0.15, 0.16, 0.18, 1);
            self.btn_tab_history.color = (1, 1, 1, 1)
        self.update_ui()

    # --- ЧАСТЬ 5.2.2.2. ОБНОВЛЕНИЕ КАРТОЧЕК, ВНЕСЕНИЕ И ЧЕСТНОЕ СПИСАНИЕ НАЛИЧНЫХ ---
    def on_enter(self):
        self.update_ui()

    def update_ui(self):
        app = App.get_running_app()
        self.rewards_container.clear_widgets()

        # Вытаскиваем чистый баланс общего кошелька
        wallet_balance = app.shop_limits.get("wallet_total_cash", 0)
        self.balance_label.text = f"В конверте: {wallet_balance} руб."

        current_list = app.custom_rewards if self.current_tab == "active" else app.custom_history

        for index, item in enumerate(current_list):
            card = BoxLayout(orientation='horizontal', padding=10, spacing=10, size_hint_y=None, height=100)

            with card.canvas.before:
                Color(0.1, 0.1, 0.12, 1)
                Rectangle(size=card.size, pos=card.pos)
            card.bind(size=self._update_card_rect, pos=self._update_card_rect)

            # Рендеринг миниатюры
            img_path = item.get("img", "").strip()
            if img_path and os.path.exists(img_path):
                card.add_widget(Image(source=img_path, size_hint_x=None, width=80, keep_ratio=True))
            else:
                card.add_widget(
                    Label(text="[нет фото]", font_size='11sp', size_hint_x=None, width=80, color=(0.4, 0.4, 0.4, 1)))

            price = item["price"]

            info_box = BoxLayout(orientation='vertical', spacing=3)
            info_box.add_widget(Label(text=item["name"], font_size='15sp', bold=True, halign='left'))

            if self.current_tab == "active":
                # Динамический индикатор: Сколько в кошельке / Сколько стоит вещь
                info_box.add_widget(Label(text=f"в конверте: {wallet_balance} / {price} руб.", font_size='13sp',
                                          color=(0.6, 0.7, 0.6, 1), halign='left'))
                card.add_widget(info_box)

                # ЯРКАЯ ЗЕЛЕНАЯ КНОПКА: Сравнивает цену с общим кошельком каждую секунду
                if wallet_balance >= price:
                    btn_buy = Button(text="[ купил ]", size_hint_x=None, width=100, font_size='13sp', bold=True,
                                     background_normal='', background_color=(0.15, 0.35, 0.15, 1),
                                     color=(0.8, 1, 0.8, 1))
                    btn_buy.bind(on_press=lambda inst, idx=index: self.archive_item(idx))
                else:
                    btn_buy = Button(text="коплю...", size_hint_x=None, width=100, font_size='13sp', disabled=True,
                                     background_normal='', background_color=(0.08, 0.08, 0.08, 1),
                                     color=(0.4, 0.4, 0.4, 1))
                card.add_widget(btn_buy)
            else:
                info_box.add_widget(
                    Label(text=f"цена: {price} руб.", font_size='13sp', color=(0.5, 0.5, 0.5, 1), halign='left'))
                card.add_widget(info_box)
                done_date = item.get("date", "ууплено")
                card.add_widget(Label(text=f"[ куплено ]\n{done_date}", font_size='11sp', size_hint_x=None, width=100,
                                      color=(0.4, 0.6, 0.4, 1), halign='center'))

            self.rewards_container.add_widget(card)

    def _update_card_rect(self, instance, value):
        """Очищает старый фон карточки и рисует пепельно-угольную подложку"""
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.1, 0.1, 0.12, 1)
            Rectangle(size=instance.size, pos=instance.pos)

    def show_wallet_deposit_popup(self, instance):
        from kivy.uix.popup import Popup
        app = App.get_running_app()

        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header.add_widget(Label(text="внесение наличных в конверт", font_size='15sp', bold=True, color=(0.7, 0.7, 0.7, 1)))
        btn_close = Button(text="[ X ]", size_hint_x=None, width=50, font_size='14sp', bold=True, background_normal='',
                           background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close)
        layout.add_widget(header)

        layout.add_widget(
            Label(text="какую сумму ты кладаешь?", font_size='13sp',
                  halign='center', color=(0.6, 0.6, 0.6, 1)))

        inp = TextInput(hint_text="сумма пополнения...", multiline=False, input_filter="int", size_hint_y=None,
                        height=45,
                        background_normal='', background_color=(0.12, 0.13, 0.15, 1), foreground_color=(1, 1, 1, 1),
                        hint_text_color=(0.5, 0.5, 0.5, 1))
        layout.add_widget(inp)

        btn_confirm = Button(text="[ подтвердить ]", size_hint_y=None, height=45, background_normal='',
                             background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
        layout.add_widget(btn_confirm)

        popup = Popup(title="", title_size=0, content=layout, size_hint=(0.9, 0.42), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close.bind(on_press=popup.dismiss)

        def process_wallet_deposit(inst):
            if inp.text.strip():
                try:
                    amount = int(inp.text.strip())
                    if amount > 0:
                        # Наличные ложатся строго на баланс кошелька без преждевременных автораспределений
                        current_wallet = app.shop_limits.get("wallet_total_cash", 0)
                        app.shop_limits["wallet_total_cash"] = current_wallet + amount

                        app.save_all_data()
                        popup.dismiss()
                        self.update_ui()
                except ValueError:
                    pass

        btn_confirm.bind(on_press=process_wallet_deposit)
        popup.open()

    def archive_item(self, index):
        """Переносит цель в архив истории покупок и честно списывает рубли в момент клика КУПИЛ"""
        app = App.get_running_app()
        bought_item = app.custom_rewards.pop(index)

        # ЧЕСТНОЕ СПИСАНИЕ: вычитаем цену вещи из кошелька строго в момент клика по кнопке КУПИЛ
        current_wallet = app.shop_limits.get("wallet_total_cash", 0)
        app.shop_limits["wallet_total_cash"] = max(0, current_wallet - bought_item["price"])

        bought_item["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        app.custom_history.append(bought_item)
        app.save_all_data()
        self.update_ui()

    # --- ЧАСТЬ 5.2.2.3. МОБИЛЬНЫЙ ПРОВОДНИК И РЕДАКТОР С ДВОЙНОЙ КОНТРАСТНОЙ РАМКОЙ ---
    # --- ЧАСТЬ 5.2.2.3. МОБИЛЬНЫЙ ПРОВОДНИК И КОНТРАСТНЫЙ РЕДАКТОР С БЛОКИРОВКОЙ ---
    def open_file_chooser(self, instance):
        from kivy.uix.popup import Popup
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=45)
        header.add_widget(Label(text="выберите фото", font_size='16sp', bold=True, color=(0.7, 0.7, 0.7, 1)))
        btn_close = Button(text="[ X ]", size_hint_x=None, width=50, background_normal='',
                           background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close);
        popup_layout.add_widget(header)

        file_chooser = FileChooserIconView(path=os.getcwd(), filters=['*.png', '*.jpg', '*.jpeg'], size_hint=(1, 1))
        popup_layout.add_widget(file_chooser)

        btn_select = Button(text="[ открыть ]", size_hint_y=None, height=50, font_size='15sp',
                            background_normal='', background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
        popup_layout.add_widget(btn_select)

        popup = Popup(title="", title_size=0, content=popup_layout, size_hint=(0.95, 0.95), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close.bind(on_press=popup.dismiss)

        def on_submit(inst):
            if file_chooser.selection:
                # ФИКС: берем первый элемент списка, чтобы получить чистую строку пути
                selected_path = os.path.abspath(file_chooser.selection[0])
                popup.dismiss()
                Clock.schedule_once(lambda dt: self.open_hardware_editor_popup(selected_path), 0.2)

        btn_select.bind(on_press=on_submit);
        popup.open()

    def open_hardware_editor_popup(self, img_path):
        from kivy.uix.popup import Popup
        from kivy.uix.slider import Slider
        from kivy.uix.widget import Widget
        from kivy.graphics import Color, Line
        from kivy.cache import Cache
        from kivy.uix.relativelayout import RelativeLayout

        Cache.remove('kv.image')
        Cache.remove('kv.texture')

        editor_layout = BoxLayout(orientation='vertical', padding=10, spacing=8)

        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=45)
        header.add_widget(
            Label(text="кадрирование", font_size='15sp', bold=True, color=(0.7, 0.7, 0.7, 1)))
        btn_close = Button(text="[ X ]", size_hint_x=None, width=50, font_size='15sp', bold=True, background_normal='',
                           background_color=(0, 0, 0, 0), color=(0.8, 0.5, 0.5, 1))
        header.add_widget(btn_close)
        editor_layout.add_widget(header)

        # Заменяем StencilView на RelativeLayout, чтобы Kivy не сжимал картинку в ноль
        box_4_3 = RelativeLayout(size_hint=(1, 0.5))

        # Создаем пустой виджет картинки, путь загрузим чуть позже
        img = Image(size_hint=(1, 1), keep_ratio=True, nocache=True)
        box_4_3.add_widget(img)
        editor_layout.add_widget(box_4_3)

        with PILImg.open(img_path) as temp_im:
            orig_w, orig_h = temp_im.size

        crop_frame = Widget(size_hint=(None, None))
        box_4_3.add_widget(crop_frame)

        editor_layout.add_widget(
            Label(text="область обрезки:", font_size='11sp', color=(0.5, 0.5, 0.5, 1),
                  size_hint_y=None, height=12))
        scale_slider = Slider(min=10, max=100, value=80, size_hint_y=None, height=28, value_track=True,
                              value_track_color=(1, 1, 1, 0.2))
        editor_layout.add_widget(scale_slider)

        editor_layout.add_widget(
            Label(text="сдвиг по горизонтали:", font_size='11sp', color=(0.5, 0.5, 0.5, 1),
                  size_hint_y=None, height=12))
        horiz_slider = Slider(min=0, max=100, value=50, size_hint_y=None, height=28, value_track=True,
                              value_track_color=(1, 1, 1, 0.2))
        editor_layout.add_widget(horiz_slider)

        editor_layout.add_widget(
            Label(text="сдвиг по вертикали:", font_size='11sp', color=(0.5, 0.5, 0.5, 1),
                  size_hint_y=None, height=12))
        vert_slider = Slider(min=0, max=100, value=50, size_hint_y=None, height=28, value_track=True,
                             value_track_color=(1, 1, 1, 0.2))
        editor_layout.add_widget(vert_slider)

        btn_crop = Button(text="[ сохранить ]", size_hint_y=None, height=45, font_size='14sp',
                          background_normal='', background_color=(1, 1, 1, 1), color=(0, 0, 0, 1))
        editor_layout.add_widget(btn_crop)

        popup = Popup(title="", title_size=0, content=editor_layout, size_hint=(0.95, 0.95), separator_height=0,
                      background_color=(0.05, 0.05, 0.05, 1))
        btn_close.bind(on_press=popup.dismiss)

        def draw_crop_frame(instance, value):
            if img.width <= 0 or img.height <= 0: return
            img_ratio = img.image_ratio
            container_ratio = img.width / img.height

            if img_ratio > container_ratio:
                actual_w = img.width;
                actual_h = img.width / img_ratio
            else:
                actual_h = img.height;
                actual_w = img.height * img_ratio

            img_start_x = img.center_x - actual_w / 2
            img_start_y = img.center_y - actual_h / 2

            max_frame_w = actual_w;
            max_frame_h = actual_w * (3.0 / 4.0)
            if max_frame_h > actual_h:
                max_frame_h = actual_h;
                max_frame_w = actual_h * (4.0 / 3.0)

            frame_scale = scale_slider.value / 100.0
            crop_frame.width = max_frame_w * frame_scale
            crop_frame.height = max_frame_h * frame_scale

            max_x_move = actual_w - crop_frame.width
            if max_x_move > 0:
                target_x = img_start_x + (max_x_move * (horiz_slider.value / 100.0))
                crop_frame.x = max(img_start_x, min(target_x, img_start_x + max_x_move))
            else:
                crop_frame.x = img_start_x + (actual_w - crop_frame.width) / 2

            max_y_move = actual_h - crop_frame.height
            if max_y_move > 0:
                target_y = img_start_y + (max_y_move * (vert_slider.value / 100.0))
                crop_frame.y = max(img_start_y, min(target_y, img_start_y + max_y_move))
            else:
                crop_frame.y = img_start_y + (actual_h - crop_frame.height) / 2

            crop_frame.canvas.after.clear()
            with crop_frame.canvas.after:
                Color(0, 0, 0, 1)
                Line(rectangle=(crop_frame.x - 1, crop_frame.y - 1, crop_frame.width + 2, crop_frame.height + 2),
                     width=2)
                Line(points=[crop_frame.center_x, crop_frame.y, crop_frame.center_x, crop_frame.y + crop_frame.height],
                     width=2)
                Line(points=[crop_frame.x, crop_frame.center_y, crop_frame.x + crop_frame.width, crop_frame.center_y],
                     width=2)

                Color(1, 1, 1, 1)
                Line(rectangle=(crop_frame.x, crop_frame.y, crop_frame.width, crop_frame.height), width=1.5)
                Color(1, 1, 1, 0.4)
                Line(points=[crop_frame.center_x, crop_frame.y, crop_frame.center_x, crop_frame.y + crop_frame.height],
                     width=1)
                Line(points=[crop_frame.x, crop_frame.center_y, crop_frame.x + crop_frame.width, crop_frame.center_y],
                     width=1)

        scale_slider.bind(value=draw_crop_frame)
        horiz_slider.bind(value=draw_crop_frame)
        vert_slider.bind(value=draw_crop_frame)
        img.bind(size=draw_crop_frame, pos=draw_crop_frame)

        # ЖЕЛЕЗНЫЙ МОБИЛЬНЫЙ ФИКС: Загружаем картинку только ПОСЛЕ открытия окна
        def delayed_load(dt):
            img.source = img_path
            img.reload()
            # Даем Kivy 0.05 секунды переварить размеры и рисуем рамку
            Clock.schedule_once(lambda d: draw_crop_frame(None, None), 0.05)

        def save_slider_crop(inst):
            try:
                with PILImg.open(img_path) as im:
                    img_ratio = img.image_ratio
                    container_ratio = img.width / img.height
                    if img_ratio > container_ratio:
                        actual_w = img.width;
                        actual_h = img.width / img_ratio
                    else:
                        actual_h = img.height;
                        actual_w = img.height * img_ratio

                    img_start_x = img.center_x - actual_w / 2
                    img_start_y = img.center_y - actual_h / 2
                    ratio = orig_w / actual_w

                    rel_x = crop_frame.x - img_start_x
                    rel_y = crop_frame.y - img_start_y

                    file_x = rel_x * ratio;
                    file_y = rel_y * ratio
                    file_w = crop_frame.width * ratio;
                    file_h = crop_frame.height * ratio
                    crop_top = orig_h - file_y - file_h

                    left = max(0, int(file_x));
                    top = max(0, int(crop_top))
                    right = min(orig_w, int(file_x + file_w));
                    bottom = min(orig_h, int(crop_top + file_h))

                    cropped_im = im.crop((left, top, right, bottom))
                    new_filename = f"reward_{int(datetime.now().timestamp())}.png"
                    final_path = os.path.join("custom_images", new_filename)
                    cropped_im.save(final_path, "PNG")

                    self.selected_image_path = final_path
                    self.btn_photo_pick.text = "[ фото успешно загружено ✓ ]"
                    self.btn_photo_pick.background_color = (0.15, 0.25, 0.15, 1)
                    popup.dismiss();
                    self.update_ui()
            except Exception:
                popup.dismiss()

        btn_crop.bind(on_press=save_slider_crop)
        popup.open()
        # Запускаем отложенную загрузку фото
        Clock.schedule_once(delayed_load, 0.1)

    def add_reward(self, instance):
        app = App.get_running_app()
        name = self.name_in.text.strip();
        price_txt = self.price_in.text.strip()
        if name and price_txt:
            try:
                price = int(price_txt)
                if price > 0:
                    app.custom_rewards.append(
                        {"name": name, "price": price, "img": self.selected_image_path, "saved": 0})
                    app.save_all_data();
                    self.update_ui()
                    self.name_in.text = '';
                    self.price_in.text = '';
                    self.selected_image_path = ''
                    self.btn_photo_pick.text = "[ выбрать ]"
                    self.btn_photo_pick.background_color = (0.14, 0.16, 0.18, 1)
            except ValueError:
                pass

    def go_back(self, instance):
        self.manager.current = 'menu'


# --- ЧАСТЬ 5.2.2.3. ГЛАВНЫЙ МОБИЛЬНЫЙ КЛАСС ЗАПУСКА ПРИЛОЖЕНИЯ ---
class LifeRPGApp(App):
    def build(self):
        # Создаем папку для вечного хранения картинок, если её ещё нет
        if not os.path.exists("custom_images"):
            os.makedirs("custom_images")

        data = DataManager.load_data()
        self.days_clean = data["days"]
        self.coins = data["coins"]
        self.total_earned = data.get("total_earned", 0)
        self.last_month = data.get("last_month", datetime.now().month)
        self.task_history = data.get("task_history", {})
        self.shop_limits = data.get("shop_limits", {})
        self.custom_rewards = data.get("custom_rewards", [])
        self.custom_history = data.get("custom_history", [])

        # Заморозка времени для всех трех таймеров отдыха с диска
        self.game_time_left = data.get("game_time_left", 0)
        self.series_time_left = data.get("series_time_left", 0)
        self.youtube_time_left = data.get("youtube_time_left", 0)

        # Запуск фонового таймера без компьютерных пушей Windows
        Clock.schedule_interval(self.check_timer, 1)

        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(TasksScreen(name='tasks'))
        sm.add_widget(ShopScreen(name='shop'))
        sm.add_widget(CustomRewardsScreen(name='custom_rewards'))
        return sm

    def save_all_data(self):
        """Полное намертво сохранение всех трех счетчиков и сейфа на жесткий диск"""
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "days": self.days_clean, "coins": self.coins, "total_earned": self.total_earned,
                "last_month": self.last_month, "task_history": self.task_history,
                "shop_limits": self.shop_limits, "game_time_left": self.game_time_left,
                "series_time_left": self.series_time_left, "youtube_time_left": self.youtube_time_left,
                "custom_rewards": self.custom_rewards, "custom_history": self.custom_history
            }, f, ensure_ascii=False, indent=4)

    def check_timer(self, dt):
        now = datetime.now()

        # Строим уникальный текстовый ключ для текущего часа (Год-Месяц-День_Час)
        # Пример: "2026-06-15_20"
        current_hour_key = f"{now.strftime('%Y-%m-%d')}_{now.hour}"

        # Получаем из базы данных ключ последнего отправленного пуша
        last_sent_alert = self.task_history.get("last_sent_notification_timestamp", "")

        # Проверяем: если в этот час пуш еще НЕ отправлялся, запускаем проверку времени
        if current_hour_key != last_sent_alert:

            # 1. УТРЕННИЙ ПУШ (Строго в 09:00)
            if now.hour == 9 and now.minute == 0:
                self.show_windows_toast("утреннее пробуждение", random.choice(self.morning_alerts))
                self.task_history["last_sent_notification_timestamp"] = current_hour_key
                self.save_all_data()

            # 2. ПОЛУДЕННЫЙ ПУШ (Строго в 15:00)
            elif now.hour == 15 and now.minute == 0:
                self.show_windows_toast("полуденный контроль", random.choice(self.day_alerts))
                self.task_history["last_sent_notification_timestamp"] = current_hour_key
                self.save_all_data()

            # 3. ВЕЧЕРНИЙ ПУШ (Строго в 20:00)
            elif now.hour == 20 and now.minute == 0:
                self.show_windows_toast("вечернее напоминание", random.choice(self.evening_alerts))
                self.task_history["last_sent_notification_timestamp"] = current_hour_key
                self.save_all_data()

        # Ежесекундное тихое вычитание времени из активных таймеров отдыха (игры/ютуб)
        need_save = False
        if self.game_time_left > 0:
            self.game_time_left -= 1
            if self.game_time_left == 0: need_save = True
        if self.series_time_left > 0:
            self.series_time_left -= 1
            if self.series_time_left == 0: need_save = True
        if self.youtube_time_left > 0:
            self.youtube_time_left -= 1
            if self.youtube_time_left == 0: need_save = True

        # Автосохранение на диск каждую минуту
        if need_save or (now.second == 0):
            self.save_all_data()


if __name__ == '__main__':
    LifeRPGApp().run()
