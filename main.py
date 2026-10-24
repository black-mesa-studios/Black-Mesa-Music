import importlib.util
from pathlib import Path
import sys, json
from nyuGUI.core import Dim, Widget, Root
from nyuGUI.widgets import TextInput, TextLabel, ImageLabel, Button
from pprint import pprint

def get_formatted_folder_size(folder_path):
  path = Path(folder_path)
  if not path.exists():
    return "0.0 B"

  try:
    total_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
  except (PermissionError, FileNotFoundError):
    total_bytes = 0

  units = ["B", "KB", "MB", "GB", "TB"]
  unit_index = 0
  size = float(total_bytes)

  while size >= 1024 and unit_index < len(units) - 1:
    size /= 1024
    unit_index += 1

  return f"{size:.1f} {units[unit_index]}"

sys.dont_write_bytecode = True
config_file = "config.json"
with open(config_file, "r") as f:
  config_data = json.load(f)

theme = config_data['app_theme_data']

app = Root(title="Music App", bgcolor=theme['background_color'])
sidebar = Widget(parent=app, bgcolor=theme['sidebar_color'], width=Dim(0, 250), height=Dim(1))

ROW_HEIGHT = 0.06

def make_header(text, y):
    return TextLabel(parent=sidebar, width=Dim(1), height=Dim(ROW_HEIGHT),
                     text=text, align="center", font_size=40, y=Dim(y))

def make_nav_button(text, y):
    button = Button(parent=sidebar, width=Dim(1), height=Dim(ROW_HEIGHT),
                  text=f" • {text}", align="left", font_size=30, y=Dim(y),
                  bgcolor=theme['sidebar_color'],
                  hover_bgcolor=theme['hover_color'],
                  pressed_bgcolor=theme['pressed_color'])
    image_path = f"./icons/{text.lower()}.png"
    if Path(image_path).exists():
        icon = ImageLabel(parent=button, image=image_path, width=Dim(0.2), height=Dim(0.6), y=Dim(0.2), x=Dim(0.8))
    return button

SECTIONS = [
    ("Library", ["Liked", "Playlists", "Artists", "Albums"]),
    ("Offline", ["Downloads", "Import"]),
    ("Custom",  ["Plugins", "Themes"]),
    ("System",  ["Settings"]),
]

headers = {}
buttons = {}

y = 0.05
for header_text, button_names in SECTIONS:
    headers[header_text] = make_header(header_text, y)
    y += ROW_HEIGHT
    for name in button_names:
        buttons[name.lower()] = make_nav_button(name, y)
        y += ROW_HEIGHT

download_space_label = TextLabel(parent=sidebar, width=Dim(0.85), height=Dim(0.1), y=Dim(0.9), x=Dim(0.15),
                                 text=get_formatted_folder_size("downloads"),
                                 align="center", font_size=40)
download_icon = ImageLabel(parent=sidebar, image="./icons/disk.png",
                           width=Dim(0.25), height=Dim(0.1), y=Dim(0.9), x=Dim(0.05))

loaded_plugins = {
    "metadata": [],
    "music": [],
    "lyrics": [],
}

plugins_dir = Path("plugins")

if plugins_dir.exists():
  for category_dir in plugins_dir.iterdir():
    if category_dir.is_dir():
      category = category_dir.name

      for plugin_folder in category_dir.iterdir():
        if plugin_folder.is_dir():
          init_file = plugin_folder / "__init__.py"

          if init_file.is_file():
            plugin_name = plugin_folder.name
            module_name = f"plugins.{category}.{plugin_name}"

            spec = importlib.util.spec_from_file_location(
                module_name,
                str(init_file),
                submodule_search_locations=[str(plugin_folder)],
            )

            if spec is not None and spec.loader is not None:
              plugin_module = importlib.util.module_from_spec(spec)
              sys.modules[module_name] = plugin_module

              spec.loader.exec_module(plugin_module)

              if category in loaded_plugins:
                loaded_plugins[category].append(plugin_module.Plugin("config.json"))

app.run()