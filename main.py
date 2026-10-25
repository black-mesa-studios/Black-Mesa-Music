import importlib.util
from pathlib import Path
import sys, json, requests, os
from nyuGUI.core import Dim, Widget, Root
from nyuGUI.widgets import TextInput, TextLabel, ImageLabel, Button, Slider

GITHUB_OWNER = "black-mesa-studios"
GITHUB_REPO = "Black-Mesa-Music-Extensions"

def download_plugin_folder(category, plugin_name):
    tree_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees/main?recursive=1"
    
    try:
        response = requests.get(tree_url)
        response.raise_for_status()
        tree_data = response.json().get("tree", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching repository tree: {e}")
        return False

    target_prefix = f"plugins/{category}/{plugin_name}/"
    
    plugin_files = [
        item for item in tree_data 
        if item["path"].startswith(target_prefix) and item["type"] == "blob"
    ]

    if not plugin_files:
        print(f"Plugin '{plugin_name}' under category '{category}' not found in repository.")
        return False

    print(f"Downloading plugin '{plugin_name}' ({len(plugin_files)} files)...")

    for file_item in plugin_files:
        file_path = file_item["path"]
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{file_path}"
        
        relative_path = file_path.replace("plugins/", "", 1)
        local_file_path = os.path.join("plugins", relative_path)
        
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        
        file_response = requests.get(raw_url)
        if file_response.status_code == 200:
            with open(local_file_path, "w", encoding="utf-8") as f:
                f.write(file_response.text)

    return True

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

playing = True
def toggle_playing():
  global playing
  playing = not playing
  if playing:
    play_button_image.set_image("./icons/play.png")
  else:
    play_button_image.set_image("./icons/pause.png")
volume = 50
def slider_change(value):
  global volume
  volume = value
app = Root(title="Music App", bgcolor=theme['app_background_color'])
sidebar = Widget(parent=app, bgcolor=theme['sidebar_color'], width=Dim(0, 250), height=Dim(1, -100))
search_image = ImageLabel(parent=app, image="./icons/search.png", width=Dim(0, 30), height=Dim(0.05), x=Dim(0, 290), y=Dim(0.02))
search_bar = TextInput(parent=app, width=Dim(1, -600), height=Dim(0.05), x=Dim(0, 350), y=Dim(0.02), placeholder="Search...", bgcolor=theme['search_bar_color'], focused_bgcolor=theme['search_bar_focused_color'], font_name=theme['font'], font_size=20)
playing_widget = Widget(parent=app, bgcolor=theme['player_bar_color'], width=Dim(1), height=Dim(0, 100), y=Dim(1, -100))
play_button_size = 50
play_button = Button(parent=playing_widget, text="", width=Dim(0, play_button_size), height=Dim(0, play_button_size), x=Dim(0.5, -play_button_size//2), y=Dim(0.5, -play_button_size//2), bgcolor=theme['play_button_color'], pressed_bgcolor=theme['play_button_pressed_color'], hover_bgcolor=theme['play_button_hover_color'], on_press=toggle_playing)
play_button_image = ImageLabel(parent=play_button, image="./icons/play.png", width=Dim(0.6), height=Dim(0.6), x=Dim(0.2), y=Dim(0.2))
volume_slider = Slider(parent=playing_widget, width=Dim(0.15), height=Dim(0.05), x=Dim(0.85), y=Dim(0.5), min_val=0, max_val=100, initial_val=50, bgcolor=theme['slider_background_color'], thumb_color=theme['slider_thumb_color'], fill_color=theme['slider_fill_color'], on_change=slider_change)

image_label = ImageLabel(parent=playing_widget, width=Dim(0, 100), height=Dim(0, 100), x=Dim(0.03), y=Dim(0), bgcolor=theme['album_art_color'])
track_label = TextLabel(parent=playing_widget, width=Dim(0.2), height=Dim(0.5), x=Dim(0.07, 100), y=Dim(0), text="Track Name", align="left", font_size=24, font_name=theme['font'])
artist_label = TextLabel(parent=playing_widget, width=Dim(0.2), height=Dim(0.5), x=Dim(0.07, 100), y=Dim(0.5), text="Artist Name", align="left", font_size=24, font_name=theme['font'])

SECTIONS = [
    ("Library", ["Liked", "Playlists", "Artists", "Albums"]),
    ("Offline", ["Downloads", "Import"]),
    ("Custom",  ["Plugins", "Themes"]),
    ("System",  ["Settings"]),
]

def make_tab(name):
    return Widget(parent=app, bgcolor=theme['tab_color'],
                  width=Dim(1, -250), height=Dim(1 - 0.075, -100),
                  x=Dim(0, 250), y=Dim(0.075),
                  visible=name == "liked")

widgets = {
    name.lower(): make_tab(name.lower())
    for _, names in SECTIONS
    for name in names
}
ROW_HEIGHT = 0.06
def nav_button_pressed(button):
    global selected_button
    if selected_button:
        selected_button.set_color(theme['nav_button_color'], hover_color=theme['nav_button_hover_color'], pressed_color=theme['nav_button_pressed_color'])
        widget_name = selected_button.text.strip(" •").lower()
        if widget_name in widgets:
            widgets[widget_name].visible = False
    selected_button = button
    button.set_color(theme['nav_button_selected_color'], hover_color=theme['nav_button_selected_color'], pressed_color=theme['nav_button_selected_color'])
    widget_name = button.text.strip(" •").lower()
    if widget_name in widgets:
        widgets[widget_name].visible = True

def make_header(text, y):
    return TextLabel(parent=sidebar, width=Dim(1), height=Dim(ROW_HEIGHT),
                     text=text, align="center", font_size=30, y=Dim(y), font_name=theme['font'])

def make_nav_button(text, y):
  bg_color = theme['nav_button_color']
  if text.lower() == "liked":
    bg_color = theme['nav_button_selected_color']

  button = Button(parent=sidebar, width=Dim(1), height=Dim(ROW_HEIGHT),
                  text=f" • {text}", align="left", font_size=24, font_name=theme['font'], y=Dim(y),
                  bgcolor=bg_color,
                  hover_bgcolor=theme['nav_button_hover_color'],
                  pressed_bgcolor=theme['nav_button_pressed_color'],
                  on_press=lambda: nav_button_pressed(button))
  image_path = f"./icons/{text.lower()}.png"
  if Path(image_path).exists():
      icon = ImageLabel(parent=button, image=image_path, width=Dim(0.2), height=Dim(0.6), y=Dim(0.2), x=Dim(0.8))
  return button

selected_button = None
headers = {}
buttons = {}

y = 0.02
for header_text, button_names in SECTIONS:
    headers[header_text] = make_header(header_text, y)
    y += ROW_HEIGHT
    for name in button_names:
        buttons[name.lower()] = make_nav_button(name, y)
        if name.lower() == "liked":
            selected_button = buttons[name.lower()]
        y += ROW_HEIGHT
download_space_label = TextLabel(parent=sidebar, width=Dim(0.85), height=Dim(0.1), y=Dim(0.885), x=Dim(0.15),
                                 text=get_formatted_folder_size("downloads"),
                                 align="center", font_size=30, font_name=theme['font'])
download_icon = ImageLabel(parent=sidebar, image="./icons/disk.png",
                           width=Dim(0.25), height=Dim(0.06), y=Dim(0.9), x=Dim(0.05))

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