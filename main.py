import importlib.util
from pathlib import Path
import sys, json, requests, os, shutil, threading
from concurrent.futures import ThreadPoolExecutor
from nyuGUI.core import Dim, Widget, Root
from nyuGUI.widgets import TextInput, TextLabel, ImageLabel, Button, Slider, ScrollingFrame
from pprint import pprint

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

def fetch_available_plugins_metadata():
    tree_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees/main?recursive=1"
    try:
        response = requests.get(tree_url, timeout=10)
        response.raise_for_status()
        tree_data = response.json().get("tree", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching repository tree: {e}")
        return []

    def fetch_one(path):
        parts = path.split("/")
        category, plugin_id = parts[1], parts[2]
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/{path}"
        try:
            res = requests.get(raw_url, timeout=10)
            if res.status_code == 200:
                meta = res.json()
                meta["category"] = category
                meta["id"] = plugin_id
                return meta
        except Exception as e:
            print(f"Failed to load metadata for {plugin_id}: {e}")
        return None

    paths = [
        item["path"] for item in tree_data
        if item["type"] == "blob"
        and item["path"].startswith("plugins/")
        and item["path"].endswith("data.json")
        and len(item["path"].split("/")) == 4
    ]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(fetch_one, paths)

    return [r for r in results if r]

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
def plugin_button_colors(state):
  """state is 'download', 'downloading' or 'delete'. Returns (color, hover_color, pressed_color) from the theme."""
  base = theme[f'plugin_{state}_color']
  hover = theme.get(f'plugin_{state}_hover_color', base)
  pressed = theme.get(f'plugin_{state}_pressed_color', base)
  return base, hover, pressed

INSTALLED_ROW_STEP = 102
installed_buttons = {}
installed_rows = []
installed_lock = threading.RLock()

def scan_installed_plugins():
  """Returns a sorted list of (category, plugin_id, data) for every plugin folder with a data.json."""
  found = []
  plugins_root = Path("plugins")
  if not plugins_root.is_dir():
    return found
  for plugin_category in sorted(plugins_root.iterdir()):
    if not plugin_category.is_dir():
      continue
    for plugin_folder in sorted(plugin_category.iterdir()):
      data_file = plugin_folder / "data.json"
      if not (plugin_folder.is_dir() and data_file.is_file()):
        continue
      try:
        with open(data_file, "r", encoding="utf-8") as f:
          plugin_data = json.load(f)
      except (OSError, ValueError) as e:
        print(f"Could not read {data_file}: {e}")
        continue
      found.append((plugin_category.name, plugin_folder.name, plugin_data))
  return found

def refresh_installed_tab():
  with installed_lock:
    for row in installed_rows:
      row.destroy()
    installed_rows.clear()
    installed_buttons.clear()

    for index, (category, plugin_id, plugin_data) in enumerate(scan_installed_plugins()):
      row = Widget(parent=plugins_installed_widget, width=Dim(1), height=Dim(0, 100),
                   y=Dim(0, INSTALLED_ROW_STEP * index),
                   bgcolor=theme['plugins_background_color'])
      TextLabel(parent=row, width=Dim(0.55), height=Dim(0.5), x=Dim(0.02), y=Dim(0.1),
                text=plugin_data.get("name", plugin_id), align="left",
                font_size=24, font_name=theme['font'])
      TextLabel(parent=row, width=Dim(0.55), height=Dim(0.5), x=Dim(0.02), y=Dim(0.5),
                text=plugin_data.get("Description", plugin_data.get("description", "")), align="left",
                font_size=12, font_name=theme['font'])
      TextLabel(parent=row, width=Dim(0.2), height=Dim(0.5), x=Dim(0.6), y=Dim(0.1),
                text=category, align="left",
                font_size=20, font_name=theme['font'])
      state = "downloading" if (category, plugin_id) in busy_plugins else "delete"
      color, hover, pressed = plugin_button_colors(state)
      delete_btn = Button(parent=row, text="", width=Dim(0, 50), height=Dim(0, 50),
                          x=Dim(1, -70), y=Dim(0.5, -25),
                          bgcolor=color, hover_bgcolor=hover, pressed_bgcolor=pressed,
                          on_press=lambda c=category, p=plugin_id: toggle_plugin({"category": c, "id": p}))
      ImageLabel(parent=delete_btn, image="./icons/delete.png", width=Dim(0.6), height=Dim(0.6),
                 x=Dim(0.2), y=Dim(0.2))
      installed_buttons[(category, plugin_id)] = delete_btn
      installed_rows.append(row)

    plugins_installed_widget.canvas_h_dim = Dim(0, INSTALLED_ROW_STEP * len(installed_rows))

def update_everything_downloading():
  download_space_label.text = get_formatted_folder_size("downloads")
  refresh_installed_tab()
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
    ("System",  ["Settings", "Sources"]),
]

def make_tab(name):
    return Widget(parent=app, bgcolor=theme['tab_color'],
                  width=Dim(1, -250), height=Dim(0.925, -100),
                  x=Dim(0, 250), y=Dim(0.075),
                  visible=name == "liked")

widgets = {
    name.lower(): make_tab(name.lower())
    for _, names in SECTIONS
    for name in names
}

plugins_tab = widgets["plugins"]

plugins_installed_widget = ScrollingFrame(parent=plugins_tab, bgcolor=theme['tab_color'],
                                  width=Dim(1), height=Dim(0.9), y=Dim(0.1), visible=True, canvas_height=Dim(2))
plugins_store_widget = Widget(parent=plugins_tab, bgcolor=theme['tab_color'],
                              width=Dim(1), height=Dim(0.9), y=Dim(0.1), visible=False)

executor = ThreadPoolExecutor(max_workers=1)
store_plugins = []

store_row_buttons = {}
busy_plugins = set()
action_executor = ThreadPoolExecutor(max_workers=2)

def is_plugin_installed(category, plugin_id):
    return (Path("plugins") / category / plugin_id).is_dir()

def remove_plugin_folder(category, plugin_id):
    folder = Path("plugins") / category / plugin_id
    try:
        shutil.rmtree(folder)
        return True
    except OSError as e:
        print(f"Error removing plugin '{plugin_id}': {e}")
        return False

def make_action_button(row, plugin):
    key = (plugin["category"], plugin["id"])
    installed = is_plugin_installed(*key)
    icon_path = "./icons/delete.png" if installed else "./icons/downloads.png"
    if key in busy_plugins:
        state = "downloading"
    else:
        state = "delete" if installed else "download"
    color, hover, pressed = plugin_button_colors(state)
    btn = Button(parent=row, text="", width=Dim(0, 50), height=Dim(0, 50),
                 x=Dim(1, -70), y=Dim(0.5, -25),
                 bgcolor=color, hover_bgcolor=hover, pressed_bgcolor=pressed,
                 on_press=lambda p=plugin: toggle_plugin(p))
    ImageLabel(parent=btn, image=icon_path, width=Dim(0.6), height=Dim(0.6),
               x=Dim(0.2), y=Dim(0.2))
    return btn

def refresh_store_buttons(category, plugin_id):
    for entry in store_row_buttons.get((category, plugin_id), []):
        row, old_btn, plugin = entry
        old_btn.destroy()
        entry[1] = make_action_button(row, plugin)

def toggle_plugin(plugin):
    key = (plugin["category"], plugin["id"])
    if key in busy_plugins:
        return
    busy_plugins.add(key)
    installed = is_plugin_installed(*key)

    color, hover, pressed = plugin_button_colors("downloading")
    for entry in store_row_buttons.get(key, []):
        entry[1].set_color(color, hover_color=hover, pressed_color=pressed)
    if key in installed_buttons:
        installed_buttons[key].set_color(color, hover_color=hover, pressed_color=pressed)

    def work():
        try:
            if installed:
                remove_plugin_folder(*key)
            else:
                download_plugin_folder(*key)
        finally:
            busy_plugins.discard(key)
            refresh_store_buttons(*key)
            update_everything_downloading()

    action_executor.submit(work)

def add_store_plugin_row(frame, plugin):
    row = Widget(parent=frame, width=Dim(1), height=Dim(0, 100),
                 y=Dim(0, 102 * len(frame.children)),
                 bgcolor=theme['plugins_background_color'])

    btn = make_action_button(row, plugin)
    store_row_buttons.setdefault((plugin["category"], plugin["id"]), []).append([row, btn, plugin])

    TextLabel(parent=row, width=Dim(0.55), height=Dim(0.5), x=Dim(0.02), y=Dim(0.1),
              text=plugin.get("name", plugin["id"]), align="left",
              font_size=24, font_name=theme['font'])
    TextLabel(parent=row, width=Dim(0.55), height=Dim(0.5), x=Dim(0.02), y=Dim(0.5),
              text=plugin.get("Description", plugin.get("description", "")), align="left",
              font_size=12, font_name=theme['font'])
    TextLabel(parent=row, width=Dim(0.2), height=Dim(0.5), x=Dim(0.6), y=Dim(0.1),
              text=plugin["category"], align="left",
              font_size=20, font_name=theme['font'])
    return row

def on_metadata_loaded(future):
    global store_plugins
    try:
        store_plugins = future.result()
    except Exception as e:
        print(f"Failed to fetch plugin metadata: {e}")
        return

    for plugin in store_plugins:
        for key in ("all", plugin["category"]):
            frame = store_category_widgets.get(key)
            if frame is not None:
                add_store_plugin_row(frame, plugin)

    for frame in store_category_widgets.values():
        frame.canvas_h_dim = Dim(0, 102 * len(frame.children))

STORE_ROW_HEIGHT = 0.07

store_category_widgets = {}
store_category_buttons = {}
selected_store_category = "all"

def make_store_category_widget(visible):
    return ScrollingFrame(parent=plugins_store_widget, bgcolor=theme['tab_color'],
                          width=Dim(1), height=Dim(1 - STORE_ROW_HEIGHT),
                          y=Dim(STORE_ROW_HEIGHT), visible=visible)

def store_category_pressed(key):
    global selected_store_category
    if key == selected_store_category:
        return

    old_button = store_category_buttons[selected_store_category]
    old_button.set_color(
        theme['nav_button_color'],
        hover_color=theme['nav_button_hover_color'],
        pressed_color=theme['nav_button_pressed_color'])
    store_category_widgets[selected_store_category].visible = False

    selected_store_category = key
    store_category_buttons[key].set_color(
        theme['nav_button_selected_color'],
        hover_color=theme['nav_button_selected_color'],
        pressed_color=theme['nav_button_selected_color'])
    store_category_widgets[key].visible = True

def make_store_category_button(key, text, x):
    selected = key == selected_store_category
    btn = Button(parent=plugins_store_widget, text=text,
                 width=Dim(0.2), height=Dim(STORE_ROW_HEIGHT), x=Dim(x),
                 font_size=24, font_name=theme['font'],
                 bgcolor=theme['nav_button_selected_color'] if selected else theme['nav_button_color'],
                 hover_bgcolor=theme['nav_button_selected_color'] if selected else theme['nav_button_hover_color'],
                 pressed_bgcolor=theme['nav_button_selected_color'] if selected else theme['nav_button_pressed_color'],
                 on_press=lambda: store_category_pressed(key))
    store_category_buttons[key] = btn
    store_category_widgets[key] = make_store_category_widget(visible=selected)
    return btn

all_button = make_store_category_button("all", "All", 0.025)
plugins_scrolling_frame = store_category_widgets["all"]

for i, category_dir in enumerate(p for p in Path("plugins").iterdir() if p.is_dir()):
    make_store_category_button(category_dir.name, category_dir.name.capitalize(), 0.247 + i * 0.22)

future = executor.submit(fetch_available_plugins_metadata)
future.add_done_callback(on_metadata_loaded)

plugin_widgets = {
    "installed": plugins_installed_widget,
    "store": plugins_store_widget,
}

selected_plugins_button = None

def plugins_type_button_pressed(button):
    global selected_plugins_button

    if selected_plugins_button:
        selected_plugins_button.set_color(
            theme['nav_button_color'],
            hover_color=theme['nav_button_hover_color'],
            pressed_color=theme['nav_button_pressed_color'])
        old_name = selected_plugins_button.text.strip(" •").lower()
        if old_name in plugin_widgets:
            plugin_widgets[old_name].visible = False

    selected_plugins_button = button
    button.set_color(
        theme['nav_button_selected_color'],
        hover_color=theme['nav_button_selected_color'],
        pressed_color=theme['nav_button_selected_color'])
    new_name = button.text.strip(" •").lower()
    if new_name in plugin_widgets:
        plugin_widgets[new_name].visible = True

def make_plugin_tab_button(text, x, bg):
    btn = Button(parent=plugins_tab, width=Dim(0.2), height=Dim(0.07),
                 x=Dim(x), y=Dim(0.02), text=text, font_size=24,
                 font_name=theme['font'], bgcolor=bg,
                 hover_bgcolor=theme['nav_button_hover_color'],
                 pressed_bgcolor=theme['nav_button_pressed_color'],
                 on_press=lambda: plugins_type_button_pressed(btn))
    return btn

plugins_installed_button = make_plugin_tab_button("Installed", 0.05, theme['nav_button_selected_color'])
plugins_store_button = make_plugin_tab_button("Store", 0.3, theme['nav_button_color'])
selected_plugins_button = plugins_installed_button

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

              with open(str(plugin_folder / "data.json"), "r") as f:
                plugin_data = json.load(f)

              if category in loaded_plugins:
                loaded_plugins[category].append([plugin_module.Plugin("config.json"), plugin_data])

update_everything_downloading()
app.run()