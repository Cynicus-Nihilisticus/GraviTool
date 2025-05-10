import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import shutil
import configparser
import time
import re # For sanitizing folder names

# --- Tooltip Class ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{int(x)}+{int(y)}")

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"), wraplength=350)
        label.pack(ipadx=2, ipady=2)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

# --- Configuration ---
CONFIG_FILE = "gt_texture_mod_tool_config.ini"
GAME_ROOT_DIR = ""
MOD_PROJECT_DIR = ""
STARTER_EXE_PATH = ""

# --- Helper Functions ---
def load_config():
    global GAME_ROOT_DIR, MOD_PROJECT_DIR
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        GAME_ROOT_DIR = config.get("Paths", "GameRootDir", fallback="")
        MOD_PROJECT_DIR = config.get("Paths", "ModProjectDir", fallback="")
        update_starter_exe_path()
    if 'app' in globals() and app:
        if hasattr(app, 'game_root_var'): app.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(app, 'mod_project_dir_var'): app.mod_project_dir_var.set(MOD_PROJECT_DIR)

def save_config():
    config = configparser.ConfigParser()
    config["Paths"] = {
        "GameRootDir": GAME_ROOT_DIR,
        "ModProjectDir": MOD_PROJECT_DIR,
    }
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def update_starter_exe_path():
    global STARTER_EXE_PATH
    if GAME_ROOT_DIR:
        STARTER_EXE_PATH = os.path.join(GAME_ROOT_DIR, "starter.exe")
    else:
        STARTER_EXE_PATH = ""

def run_starter_command(command_name, params_list, log_area_widget, timeout=120):
    if not STARTER_EXE_PATH or not os.path.exists(STARTER_EXE_PATH):
        log_message(log_area_widget, "Error: starter.exe not found. Set Game Root Directory.")
        return False, None
    if not GAME_ROOT_DIR or not os.path.isdir(GAME_ROOT_DIR):
        log_message(log_area_widget, "Error: Game Root Directory is not set or invalid.")
        return False, None

    cmd_string_part = f"{command_name}"
    if params_list:
        params_str = ','.join(map(lambda p: str(p) if p is not None else "", params_list))
        cmd_string_part += f",{params_str}"

    command = [STARTER_EXE_PATH, cmd_string_part]
    log_message(log_area_widget, f"Running: \"{STARTER_EXE_PATH}\" \"{cmd_string_part}\"")
    log_message(log_area_widget, f"Working directory: {GAME_ROOT_DIR}")

    process = None
    try:
        process = subprocess.Popen(command, cwd=GAME_ROOT_DIR,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        stdout, stderr = process.communicate(timeout=timeout)

        if stdout: log_message(log_area_widget, f"Output:\n{stdout}")
        if stderr: log_message(log_area_widget, f"Errors:\n{stderr}")

        out_dir_log = os.path.join(GAME_ROOT_DIR, "out")
        log_message(log_area_widget, f"Command finished. Check '{out_dir_log}' for detailed logs from starter.exe.")

        if process.returncode != 0:
            log_message(log_area_widget, f"Command failed with return code {process.returncode}")
            return False, None
        if command_name == "unflat" and len(params_list) > 1 and params_list[1]:
             return True, os.path.join(GAME_ROOT_DIR, params_list[1])
        return True, None
    except subprocess.TimeoutExpired:
        log_message(log_area_widget, "Error: Command timed out.")
        if process: process.kill()
        return False, None
    except Exception as e:
        log_message(log_area_widget, f"Error running command: {e}")
        return False, None

def log_message(log_area_widget, message):
    if log_area_widget:
        log_area_widget.config(state=tk.NORMAL)
        log_area_widget.insert(tk.END, str(message) + "\n")
        log_area_widget.see(tk.END)
        log_area_widget.config(state=tk.DISABLED)
    else:
        print(message)

class TextureModTool:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Graviteam Asset Mod Tool (GTOS) - Refactored")
        self.root.geometry("950x900")

        log_main_frame = ttk.Frame(self.root)
        log_frame = ttk.LabelFrame(log_main_frame, text="Log")
        self.log_area = tk.Text(log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        log_scroll = tk.Scrollbar(log_frame, command=self.log_area.yview)
        self.log_area.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))
        log_main_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

        load_config()

        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Set Game Root Directory", command=self.set_game_root)
        filemenu.add_command(label="Set Mod Project Directory", command=self.set_mod_project_dir)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(expand=True, fill='both', padx=10, pady=10)

        setup_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(setup_tab_frame, text='1. Project Setup')
        self.create_setup_tab(setup_tab_frame)

        asset_extractor_main_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(asset_extractor_main_frame, text='2. Asset Extractor')
        self.create_asset_extractor_tab(asset_extractor_main_frame)

        texture_conversion_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(texture_conversion_tab_frame, text='3. Mod Texture Conversion')
        self.create_texture_conversion_tab(texture_conversion_tab_frame)

        sound_modding_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(sound_modding_tab_frame, text='4. Sound Modding (SFX/Speech)')
        self.create_sound_modding_tab(sound_modding_tab_frame)

        packaging_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(packaging_tab_frame, text='5. Asset Packaging')
        self.create_packaging_tab(packaging_tab_frame)

        if hasattr(self, 'game_root_var'): self.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(self, 'mod_project_dir_var'): self.mod_project_dir_var.set(MOD_PROJECT_DIR)

        if GAME_ROOT_DIR: update_starter_exe_path()
        log_message(self.log_area, "Tool initialized. Set Game Root and Mod Project directories if not already configured.")

        # Updated flatdata_definitions for sound file extensions
        self.flatdata_definitions = {
            "textures": {
                "mkflat_type": "texture",
                "sources": [{"prefix": "[TEX]", "folder": "prepared_textures", "ext": ".texture"}]
            },
            "sounds": {
                "mkflat_type": "sound", # This is the type for the flatlist entry
                "sources": [
                    {"prefix": "[SFX]", "folder": os.path.join("prepared_sounds", "sfx"), "ext": ".loc_def.sound"},
                    {"prefix": "[SPE]", "folder": os.path.join("prepared_sounds", "speech"), "ext": ".loc_def.sound"}
                ]
            }
        }
        self.asset_types_to_scan = []
        for definition in self.flatdata_definitions.values():
            for source in definition["sources"]:
                self.asset_types_to_scan.append(source.copy())

    def create_setup_tab(self, tab_frame):
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="Game Root:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.game_root_var = tk.StringVar(value=GAME_ROOT_DIR)
        ttk.Entry(frame, textvariable=self.game_root_var, width=60).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        game_root_browse_btn = ttk.Button(frame, text="Browse", command=self.set_game_root)
        game_root_browse_btn.grid(row=0, column=2, padx=5, pady=5)
        ToolTip(game_root_browse_btn, "Select the main installation folder of your Graviteam game (e.g., where starter.exe is located).")

        ttk.Label(frame, text="Mod Project Dir:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mod_project_dir_var = tk.StringVar(value=MOD_PROJECT_DIR)
        ttk.Entry(frame, textvariable=self.mod_project_dir_var, width=60).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        mod_project_browse_btn = ttk.Button(frame, text="Browse/Create", command=self.set_mod_project_dir)
        mod_project_browse_btn.grid(row=1, column=2, padx=5, pady=5)
        ToolTip(mod_project_browse_btn, "Select an existing folder or a location to create a new folder for your mod project files.")

        frame.grid_columnconfigure(1, weight=1)

        info_frame = ttk.LabelFrame(frame, text="Mod Information (for desc.addpack & readme.txt)", padding="10")
        info_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")

        ttk.Label(info_frame, text="Mod Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.mod_name_var = tk.StringVar(value="MyMod")
        ttk.Entry(info_frame, textvariable=self.mod_name_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(ttk.Label(info_frame, text="Mod Name:"), "The display name of your mod. Used in desc.addpack and readme.txt.\nAvoid special characters that are invalid in folder names.")

        ttk.Label(info_frame, text="Author:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mod_author_var = tk.StringVar(value="Modder")
        ttk.Entry(info_frame, textvariable=self.mod_author_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(info_frame, text="Version (e.g., 100 for 1.00):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.mod_version_var = tk.StringVar(value="100")
        ttk.Entry(info_frame, textvariable=self.mod_version_var, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        info_frame.grid_columnconfigure(1, weight=1)

        init_folders_button = ttk.Button(frame, text="Initialize/Verify Mod Project Folders", command=self.initialize_mod_folders)
        init_folders_button.grid(row=4, column=0, columnspan=3, pady=10)
        ToolTip(init_folders_button,
                "Creates standard subfolders for textures, sounds (SFX/Speech), etc.,\n"
                "within your Mod Project Directory and a template readme.txt if they don't exist.")

    def create_asset_extractor_tab(self, parent_tab_frame):
        main_frame = ttk.Frame(parent_tab_frame, padding="5")
        main_frame.pack(expand=True, fill='both')

        self.asset_extractor_notebook = ttk.Notebook(main_frame)
        self.asset_extractor_notebook.pack(expand=True, fill='both', padx=5, pady=5)

        texture_extractor_sub_tab_frame = ttk.Frame(self.asset_extractor_notebook)
        self.asset_extractor_notebook.add(texture_extractor_sub_tab_frame, text='Texture Extractor')
        self._create_texture_extractor_sub_tab_content(texture_extractor_sub_tab_frame)

        sound_extractor_sub_tab_frame = ttk.Frame(self.asset_extractor_notebook)
        self.asset_extractor_notebook.add(sound_extractor_sub_tab_frame, text='Sound Extractor (SFX/Speech)')
        self._create_sound_extractor_sub_tab_content(sound_extractor_sub_tab_frame)

    def _create_texture_extractor_sub_tab_content(self, tab_frame):
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="This tool will unpack game texture archives (.flatdata) to your Mod Project Directory, \nconvert them to .dds, and generate a list of available textures.").pack(pady=(0,5))

        archive_frame = ttk.LabelFrame(frame, text="Select Game Texture Archives to Extract", padding="10")
        archive_frame.pack(fill=tk.X, pady=5)

        self.texture_archives_vars = {}
        known_texture_archives = [
            "tex_main.flatdata", "tex_main_01.flatdata", "tex_misc.flatdata", "tex_objects.flatdata",
            "tex_humans.flatdata", "tex_techns.flatdata", "tex_dummy.flatdata", "textures_loc.flatdata"
        ]
        for i, archive_name in enumerate(known_texture_archives):
            var = tk.BooleanVar(value=True if archive_name in ["tex_main.flatdata", "tex_objects.flatdata"] else False)
            chk = ttk.Checkbutton(archive_frame, text=archive_name, variable=var)
            chk.grid(row=i//2, column=i%2, padx=5, pady=2, sticky="w")
            self.texture_archives_vars[archive_name] = var

        self.delete_atf_after_extraction_var = tk.BooleanVar(value=True)
        delete_chk = ttk.Checkbutton(frame, text="Delete original .texture files from 'extracted_game_textures/atf/' after successful DDS conversion",
                        variable=self.delete_atf_after_extraction_var)
        delete_chk.pack(pady=(5,0), anchor="w", padx=20)
        ToolTip(delete_chk, "If checked, successfully converted .texture files in the 'extracted_game_textures/atf/' subfolders\nwill be deleted to save space. DDS files will remain.")

        extract_button = ttk.Button(frame, text="Unpack Selected Texture Archives & Convert to DDS", command=self.extract_and_convert_game_textures)
        extract_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(extract_button,
                "Unpacks selected game texture archives (.flatdata) using 'unflat'.\n"
                "Converts the extracted .texture files to .dds using 'atf2dds'.\n"
                "Original .texture files are saved to 'extracted_game_textures/atf/[archive_name]/'.\n"
                "Converted .dds files are saved to 'extracted_game_textures/dds/[archive_name]/'.")

        ttk.Label(frame, text="(.dds files will be in 'ModProjectDir/extracted_game_textures/dds/[archive_name]/')").pack()
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(frame, text="Extracted Texture List (relative to 'extracted_game_textures/dds/'):").pack(pady=(5,0))

        listbox_container_frame = ttk.Frame(frame)
        listbox_container_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=20)
        self.extracted_texture_listbox = tk.Listbox(listbox_container_frame, height=8, relief=tk.SUNKEN, borderwidth=1)
        list_scroll = tk.Scrollbar(listbox_container_frame, orient=tk.VERTICAL, command=self.extracted_texture_listbox.yview)
        self.extracted_texture_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.extracted_texture_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        save_list_button = ttk.Button(frame, text="Save Texture List to File", command=self.save_extracted_texture_list)
        save_list_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(save_list_button, "Saves the list of extracted .dds texture paths (shown above) to a text file.")

    def _create_sound_extractor_sub_tab_content(self, tab_frame):
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="This tool will unpack game sound archives (.flatdata) to your Mod Project Directory\nand generate a list of available sound files (e.g., .aaf, .loc_def.sound).").pack(pady=(0,5)) # Updated text

        sound_archive_frame = ttk.LabelFrame(frame, text="Select Game Sound Archives to Extract", padding="10")
        sound_archive_frame.pack(fill=tk.X, pady=5)

        self.sound_archives_vars = {}
        known_sound_archives = [
            "sounds.flatdata",
            "speech.flatdata",
            "speech_eng.flatdata",
            "speech_rus.flatdata",
            "speech_ger.flatdata",
        ]
        default_sound_archives = ["sounds.flatdata", "speech.flatdata"]

        for i, archive_name in enumerate(known_sound_archives):
            var = tk.BooleanVar(value=True if archive_name in default_sound_archives else False)
            chk = ttk.Checkbutton(sound_archive_frame, text=archive_name, variable=var)
            chk.grid(row=i, column=0, padx=5, pady=2, sticky="w")
            self.sound_archives_vars[archive_name] = var

        self.delete_temp_sound_unflat_var = tk.BooleanVar(value=True)
        delete_temp_chk = ttk.Checkbutton(frame, text="Delete temporary unpack folders after extraction",
                                          variable=self.delete_temp_sound_unflat_var)
        delete_temp_chk.pack(pady=(5,0), anchor="w", padx=20)
        ToolTip(delete_temp_chk, "If checked, the temporary folders created by 'unflat' in the game directory\nwill be deleted after sound files are copied to your mod project.")


        extract_sound_button = ttk.Button(frame, text="Unpack Selected Sound Archives", command=self.extract_and_unpack_game_sounds)
        extract_sound_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(extract_sound_button,
                "Unpacks selected game sound archives (.flatdata) using 'unflat'.\n"
                "Sound files (e.g., .loc_def.sound) are saved to 'ModProjectDir/extracted_game_sounds/[archive_name]/'.") # Updated text

        ttk.Label(frame, text="(.loc_def.sound files will be in 'ModProjectDir/extracted_game_sounds/[archive_name]/')").pack() # Updated text
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(frame, text="Extracted Sound File List (relative to 'extracted_game_sounds/'):").pack(pady=(5,0))

        sound_listbox_container_frame = ttk.Frame(frame)
        sound_listbox_container_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=20)
        self.extracted_sound_listbox = tk.Listbox(sound_listbox_container_frame, height=8, relief=tk.SUNKEN, borderwidth=1)
        sound_list_scroll = tk.Scrollbar(sound_listbox_container_frame, orient=tk.VERTICAL, command=self.extracted_sound_listbox.yview)
        self.extracted_sound_listbox.configure(yscrollcommand=sound_list_scroll.set)
        sound_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.extracted_sound_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        save_sound_list_button = ttk.Button(frame, text="Save Sound List to File", command=self.save_extracted_sound_list)
        save_sound_list_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(save_sound_list_button, "Saves the list of extracted sound file paths (shown above) to a text file.")


    def create_texture_conversion_tab(self, tab_frame):
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="Use these tools to convert textures for your mod.").pack(pady=(0,10))
        ttk.Label(frame, text="Typically, you'd copy desired .dds files from 'extracted_game_textures/dds/'\n to 'dds_work/', edit them, then convert back to .texture.").pack(pady=(0,10))

        atf_to_dds_button = ttk.Button(frame, text="Convert Game .texture (ATF) to .dds (for editing)", command=self.convert_atf_to_dds_for_modding)
        atf_to_dds_button.pack(pady=10, fill=tk.X, padx=20)
        ToolTip(atf_to_dds_button,
                "Select one or more .texture (ATF) files.\n"
                "Converts them to .dds format using 'atf2dds'.\n"
                "Output .dds files are saved in 'ModProjectDir/dds_work/'.")

        ttk.Label(frame, text="Select any .texture file. Output .dds will be in 'ModProjectDir/dds_work/'").pack(pady=(0,10))
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        dds_to_atf_button = ttk.Button(frame, text="Convert Edited .dds to Game .texture (ATF)", command=self.convert_dds_to_atf_for_modding)
        dds_to_atf_button.pack(pady=10, fill=tk.X, padx=20)
        ToolTip(dds_to_atf_button,
                "Select one or more .dds files (typically from 'dds_work/').\n"
                "Converts them to .texture (ATF) format using 'dds2atf'.\n"
                "Output .texture files are saved in 'ModProjectDir/prepared_textures/'.")
        ttk.Label(frame, text="Select .dds from 'dds_work/'. Output .texture will be in 'ModProjectDir/prepared_textures/'").pack(pady=(0,10))

    def create_sound_modding_tab(self, tab_frame):
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        aaf_frame = ttk.LabelFrame(frame, text="Convert .wav to Game Sound Format (.loc_def.sound)", padding="10") # Updated title
        aaf_frame.pack(fill=tk.X, pady=10)

        ttk.Label(aaf_frame, text="Input .wav format: 44.1kHz, 16-bit. Mono for 3D SFX, Stereo for UI/System sounds.").pack(anchor="w", pady=(0,5))

        sound_type_frame = ttk.Frame(aaf_frame)
        sound_type_frame.pack(anchor="w", pady=(0,5))
        ttk.Label(sound_type_frame, text="Output Type:").pack(side=tk.LEFT, padx=(0,5))
        self.sound_type_var = tk.StringVar(value="SFX")
        sfx_radio = ttk.Radiobutton(sound_type_frame, text="SFX (to prepared_sounds/sfx)", variable=self.sound_type_var, value="SFX")
        sfx_radio.pack(side=tk.LEFT, padx=5)
        ToolTip(sfx_radio, "Sound effects (e.g., explosions, vehicle sounds) are typically mono.")
        speech_radio = ttk.Radiobutton(sound_type_frame, text="Speech (to prepared_sounds/speech)", variable=self.sound_type_var, value="Speech")
        speech_radio.pack(side=tk.LEFT, padx=5)
        ToolTip(speech_radio, "Speech files.")

        wav_to_aaf_button = ttk.Button(aaf_frame, text="Select .wav File(s) and Convert to .loc_def.sound", command=self.convert_wav_to_aaf) # Updated button text
        wav_to_aaf_button.pack(fill=tk.X, pady=5)
        ToolTip(wav_to_aaf_button, "Uses 'starter.exe wav2aaf'.\nOutput .loc_def.sound files are saved in the selected 'prepared_sounds' subfolder.") # Updated tooltip

        info_text = (
            "General Notes for SFX/Speech:\n"
            "- Game sound files use the .loc_def.sound extension (internally AAF format).\n" # Updated text
            "- After conversion, refresh the list in the 'Asset Packaging' tab to include them in your mod."
        )
        ttk.Label(frame, text=info_text, justify=tk.LEFT, wraplength=800).pack(pady=10, anchor="w")


    def create_packaging_tab(self, tab_frame):
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        list_frame = ttk.LabelFrame(frame, text="Select asset files from 'prepared_...' folders to include in mod", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.packaged_assets_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10, relief=tk.SUNKEN, borderwidth=1)
        list_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.packaged_assets_listbox.yview)
        self.packaged_assets_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.packaged_assets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        refresh_button = ttk.Button(frame, text="Refresh List from 'prepared_...' folders", command=self.load_prepared_assets)
        refresh_button.pack(pady=(5,10), fill=tk.X, padx=20)
        ToolTip(refresh_button, "Updates the list above with recognized asset files currently in\n"
                                 "'ModProjectDir/prepared_textures/' (.texture) and\n"
                                 "'ModProjectDir/prepared_sounds/(sfx/speech)/' (.loc_def.sound).") # Updated tooltip

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        generate_files_button = ttk.Button(frame, text="1. Generate Mod Files (desc.addpack & .flatdata archives)", command=self.generate_mod_files)
        generate_files_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(generate_files_button,
                "For selected assets:\n"
                "- Creates 'desc.addpack' in 'CORE/'.\n"
                "- Creates appropriate '.!flatlist' files in a temporary staging area.\n"
                "- Copies selected asset files to the staging area.\n"
                "- Creates '.flatdata' archives (e.g., textures.flatdata, sounds.flatdata)\n"
                "  using 'mkflat' and places them in 'CORE/shared/packed_data/'.\n"
                "- Cleans up temporary staging files.")

        create_archive_button = ttk.Button(frame, text="2. Create .gt2extension Mod Archive", command=self.create_mod_archive)
        create_archive_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(create_archive_button,
                "Packages the 'CORE/' folder and 'readme.txt' from your Mod Project Directory\n"
                "into a distributable .gt2extension archive file (a renamed .zip).")

    def _validate_paths(self, check_mod_project=True, check_starter=True):
        global GAME_ROOT_DIR, MOD_PROJECT_DIR, STARTER_EXE_PATH
        GAME_ROOT_DIR = self.game_root_var.get()
        MOD_PROJECT_DIR = self.mod_project_dir_var.get()

        if not GAME_ROOT_DIR or not os.path.isdir(GAME_ROOT_DIR):
            log_message(self.log_area, "Error: Game Root Directory is not set or invalid.")
            messagebox.showerror("Error", "Game Root Directory is not set or invalid.")
            return False

        if check_starter:
            update_starter_exe_path()
            if not STARTER_EXE_PATH or not os.path.exists(STARTER_EXE_PATH):
                log_message(self.log_area, f"Error: starter.exe not found at {STARTER_EXE_PATH}. Check Game Root Directory.")
                messagebox.showerror("Error", f"starter.exe not found at {STARTER_EXE_PATH}. Check Game Root Directory.")
                return False

        if check_mod_project:
            if not MOD_PROJECT_DIR:
                log_message(self.log_area, "Error: Mod Project Directory is not set.")
                messagebox.showerror("Error", "Mod Project Directory is not set.")
                return False
            if not os.path.isdir(MOD_PROJECT_DIR):
                 log_message(self.log_area, f"Mod Project Directory '{MOD_PROJECT_DIR}' does not exist yet. It will be created if needed.")
        return True

    def set_game_root(self):
        global GAME_ROOT_DIR
        directory = filedialog.askdirectory(title="Select Game Root Directory (containing starter.exe)")
        if directory:
            self.game_root_var.set(directory)
            GAME_ROOT_DIR = directory
            update_starter_exe_path()
            save_config()
            log_message(self.log_area, f"Game Root Directory set to: {GAME_ROOT_DIR}")
            if not os.path.exists(STARTER_EXE_PATH):
                 log_message(self.log_area, f"Warning: starter.exe not found at {STARTER_EXE_PATH}")
                 messagebox.showwarning("Warning", f"starter.exe not found at {STARTER_EXE_PATH}")

    def set_mod_project_dir(self):
        global MOD_PROJECT_DIR
        initial_dir_suggestion = ""
        current_game_root = self.game_root_var.get()
        if current_game_root and os.path.isdir(current_game_root):
            initial_dir_suggestion = os.path.join(current_game_root, "users", "modwork")
            os.makedirs(initial_dir_suggestion, exist_ok=True)

        directory = filedialog.askdirectory(title="Select or Create Mod Project Directory", initialdir=initial_dir_suggestion or None)
        if directory:
            self.mod_project_dir_var.set(directory)
            MOD_PROJECT_DIR = directory
            save_config()
            log_message(self.log_area, f"Mod Project Directory set to: {MOD_PROJECT_DIR}")
            self.initialize_mod_folders(silent=True)

    def initialize_mod_folders(self, silent=False):
        if not self._validate_paths(check_mod_project=True, check_starter=False):
            if not self.mod_project_dir_var.get():
                 if not silent:
                    log_message(self.log_area, "Mod project directory not set, cannot initialize folders.")
                    messagebox.showerror("Error", "Mod Project Directory is not set. Cannot initialize folders.")
                 return False

        current_mod_project_dir = self.mod_project_dir_var.get()

        if not os.path.isdir(current_mod_project_dir):
            try:
                os.makedirs(current_mod_project_dir)
                if not silent: log_message(self.log_area, f"Created Mod Project Directory: {current_mod_project_dir}")
            except Exception as e:
                log_message(self.log_area, f"Error creating Mod Project Directory {current_mod_project_dir}: {e}")
                if not silent: messagebox.showerror("Error", f"Could not create Mod Project Directory: {e}")
                return False

        paths_to_create = {
            "dds_work": os.path.join(current_mod_project_dir, "dds_work"),
            "prepared_textures": os.path.join(current_mod_project_dir, "prepared_textures"),
            "CORE_dir": os.path.join(current_mod_project_dir, "CORE"),
            "CORE_shared_packed_data": os.path.join(current_mod_project_dir, "CORE", "shared", "packed_data"),
            "extracted_atf_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "atf"),
            "extracted_dds_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "dds"),
            "extracted_sounds_base": os.path.join(current_mod_project_dir, "extracted_game_sounds"),
            "wav_sfx_work": os.path.join(current_mod_project_dir, "wav_sfx_work"),
            "wav_speech_work": os.path.join(current_mod_project_dir, "wav_speech_work"),
            "prepared_sounds_sfx": os.path.join(current_mod_project_dir, "prepared_sounds", "sfx"),
            "prepared_sounds_speech": os.path.join(current_mod_project_dir, "prepared_sounds", "speech"),
        }

        created_any = False
        for key, p in paths_to_create.items():
            if not os.path.exists(p):
                try:
                    os.makedirs(p, exist_ok=True)
                    if not silent: log_message(self.log_area, f"Created folder: {p}")
                    created_any = True
                except Exception as e:
                    log_message(self.log_area, f"Error creating folder {p}: {e}")
                    if not silent: messagebox.showerror("Error", f"Could not create folder {p}: {e}")
                    return False
        readme_path = os.path.join(current_mod_project_dir, "readme.txt")
        if not os.path.exists(readme_path):
            try:
                with open(readme_path, "w", encoding='utf-8') as f:
                    f.write(f"Mod: {self.mod_name_var.get() or 'My Mod'}\n")
                    f.write(f"Author: {self.mod_author_var.get() or 'Unknown Author'}\n")
                    f.write(f"Version: {self.mod_version_var.get() or '100'}\n\n")
                    f.write("Description:\nReplace this with your mod's description.\n")
                if not silent: log_message(self.log_area, f"Created template readme.txt: {readme_path}")
                created_any = True
            except Exception as e:
                log_message(self.log_area, f"Error creating readme.txt {readme_path}: {e}")

        if not created_any and not silent:
            log_message(self.log_area, "Mod project folders already seem to exist or no new ones needed.")
        elif created_any and not silent:
            log_message(self.log_area, "Mod project folder structure initialized/verified.")
        return True


    def extract_and_convert_game_textures(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for texture extraction.")
            return

        selected_archives = [name for name, var in self.texture_archives_vars.items() if var.get()]
        if not selected_archives:
            messagebox.showinfo("No Selection", "No texture archives selected for extraction.")
            return

        log_message(self.log_area, f"Starting texture extraction for: {', '.join(selected_archives)}")
        self.extracted_texture_listbox.delete(0, tk.END)
        all_extracted_texture_names_for_file = []

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        final_extracted_atf_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_textures", "atf")
        final_extracted_dds_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_textures", "dds")
        current_game_root = self.game_root_var.get()

        for archive_name in selected_archives:
            archive_path_rel_to_game_root = os.path.join("data", "k43t", "shared", "packed_data", archive_name)
            archive_path_abs_in_game = os.path.join(current_game_root, archive_path_rel_to_game_root)

            if not os.path.exists(archive_path_abs_in_game):
                found_loc_archive = False
                for loc_folder in ["loc_eng", "loc_rus", "loc_ger", "loc_def"]:
                    alt_archive_path_rel = os.path.join("data", "k43t", loc_folder, "packed_data", archive_name)
                    alt_archive_path_abs = os.path.join(current_game_root, alt_archive_path_rel)
                    if os.path.exists(alt_archive_path_abs):
                        archive_path_rel_to_game_root = alt_archive_path_rel
                        archive_path_abs_in_game = alt_archive_path_abs
                        found_loc_archive = True
                        break
                if not found_loc_archive:
                    log_message(self.log_area, f"Warning: Texture archive '{archive_name}' not found in common game data paths. Skipping.")
                    continue
            
            log_message(self.log_area, f"Processing texture archive: {archive_path_rel_to_game_root}")
            archive_base_name = os.path.splitext(archive_name)[0]
            starter_unflat_output_rel = os.path.join("users", "modwork", f"_temp_unflat_tex_{archive_base_name}_{timestamp}")
            starter_unflat_output_abs = os.path.join(current_game_root, starter_unflat_output_rel)
            os.makedirs(os.path.dirname(starter_unflat_output_abs), exist_ok=True)

            success, unflat_output_actual_abs = run_starter_command("unflat", [archive_path_rel_to_game_root, starter_unflat_output_rel], self.log_area, timeout=300)

            if not success or not (unflat_output_actual_abs and os.path.isdir(unflat_output_actual_abs)):
                log_message(self.log_area, f"  Failed to unpack texture archive '{archive_name}'. Skipping.")
                if os.path.exists(starter_unflat_output_abs): shutil.rmtree(starter_unflat_output_abs)
                continue
            
            log_message(self.log_area, f"  Successfully unpacked to '{unflat_output_actual_abs}'. Now converting .texture to .dds...")
            final_atf_archive_dir_in_project = os.path.join(final_extracted_atf_base_abs, archive_base_name)
            final_dds_archive_dir_in_project = os.path.join(final_extracted_dds_base_abs, archive_base_name)
            os.makedirs(final_atf_archive_dir_in_project, exist_ok=True)
            os.makedirs(final_dds_archive_dir_in_project, exist_ok=True)

            textures_in_archive_count = 0
            successfully_converted_atf_paths_in_project = []

            for item in os.listdir(unflat_output_actual_abs):
                if item.lower().endswith(".texture"):
                    textures_in_archive_count += 1
                    src_atf_in_game_temp_abs = os.path.join(unflat_output_actual_abs, item)
                    dest_atf_in_project_abs = os.path.join(final_atf_archive_dir_in_project, item)
                    try:
                        shutil.copy2(src_atf_in_game_temp_abs, dest_atf_in_project_abs)
                    except Exception as e:
                        log_message(self.log_area, f"    Error copying {item} to project ATF archive: {e}")
                        continue

                    dds_filename = item.replace(".texture", ".dds")
                    temp_dds_output_in_game_temp_abs = os.path.join(unflat_output_actual_abs, dds_filename)
                    param_src_atf_rel = os.path.relpath(src_atf_in_game_temp_abs, current_game_root)
                    param_dest_dds_rel = os.path.relpath(temp_dds_output_in_game_temp_abs, current_game_root)
                    conv_success, _ = run_starter_command("atf2dds", [param_src_atf_rel, param_dest_dds_rel], self.log_area)

                    if conv_success and os.path.exists(temp_dds_output_in_game_temp_abs):
                        dest_dds_in_project_abs = os.path.join(final_dds_archive_dir_in_project, dds_filename)
                        try:
                            shutil.copy2(temp_dds_output_in_game_temp_abs, dest_dds_in_project_abs)
                            listbox_entry = os.path.join(archive_base_name, dds_filename)
                            all_extracted_texture_names_for_file.append(listbox_entry)
                            self.extracted_texture_listbox.insert(tk.END, listbox_entry)
                            self.extracted_texture_listbox.see(tk.END)
                            successfully_converted_atf_paths_in_project.append(dest_atf_in_project_abs)
                        except Exception as e:
                            log_message(self.log_area, f"    Error copying converted DDS {dds_filename} to project: {e}")
                    else:
                        log_message(self.log_area, f"    Failed to convert {item} from {archive_name}.")
            
            if self.delete_atf_after_extraction_var.get() and successfully_converted_atf_paths_in_project:
                log_message(self.log_area, f"  Deleting original .texture files from {final_atf_archive_dir_in_project}...")
                deleted_count = 0
                for atf_to_delete in successfully_converted_atf_paths_in_project:
                    try:
                        if os.path.exists(atf_to_delete): 
                           os.remove(atf_to_delete)
                           deleted_count +=1
                    except Exception as e:
                        log_message(self.log_area, f"    Error deleting {os.path.basename(atf_to_delete)}: {e}")
                if deleted_count > 0:
                    log_message(self.log_area, f"    Successfully deleted {deleted_count} .texture files from project's ATF backup.")
                if os.path.exists(final_atf_archive_dir_in_project) and not os.listdir(final_atf_archive_dir_in_project):
                    try:
                        os.rmdir(final_atf_archive_dir_in_project)
                        log_message(self.log_area, f"    Removed empty ATF subfolder: {final_atf_archive_dir_in_project}")
                    except Exception as e:
                        log_message(self.log_area, f"    Could not remove empty ATF subfolder {final_atf_archive_dir_in_project}: {e}")
            elif not self.delete_atf_after_extraction_var.get():
                 log_message(self.log_area, f"  Kept original .texture files in {final_atf_archive_dir_in_project}")

            if textures_in_archive_count == 0:
                log_message(self.log_area, f"  No .texture files found in unpacked '{unflat_output_actual_abs}'.")
            if os.path.exists(starter_unflat_output_abs):
                try:
                    shutil.rmtree(starter_unflat_output_abs)
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove game temp unpack dir {starter_unflat_output_abs}: {e}")
            self.root.update_idletasks()

        log_message(self.log_area, "Game texture extraction and conversion process finished.")
        if not all_extracted_texture_names_for_file:
            log_message(self.log_area, "No textures were successfully extracted and converted.")
        else:
            messagebox.showinfo("Extraction Complete", f"Texture extraction and conversion complete. Check 'extracted_game_textures' and list.")


    def extract_and_unpack_game_sounds(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for sound extraction.")
            return

        selected_sound_archives = [name for name, var in self.sound_archives_vars.items() if var.get()]
        if not selected_sound_archives:
            messagebox.showinfo("No Selection", "No sound archives selected for extraction.")
            return

        log_message(self.log_area, f"Starting sound archive extraction for: {', '.join(selected_sound_archives)}")
        self.extracted_sound_listbox.delete(0, tk.END)
        all_extracted_sound_files_for_list = []

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        final_extracted_sounds_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_sounds")
        os.makedirs(final_extracted_sounds_base_abs, exist_ok=True)

        current_game_root = self.game_root_var.get()
        # Expecting .loc_def.sound files primarily based on user feedback and PDF example for wav2aaf output
        sound_file_extensions = (".loc_def.sound", ".sound", ".aaf") # Prioritize .loc_def.sound

        for archive_name in selected_sound_archives:
            archive_path_rel_to_game_root = os.path.join("data", "k43t", "shared", "packed_data", archive_name)
            archive_path_abs_in_game = os.path.join(current_game_root, archive_path_rel_to_game_root)

            if not os.path.exists(archive_path_abs_in_game):
                found_loc_archive = False
                if "speech" in archive_name.lower():
                    loc_folder_guess = archive_name.lower().replace(".flatdata","").replace("speech_","loc_")
                    if loc_folder_guess.startswith("loc_"):
                         loc_folders_to_try = [loc_folder_guess, "loc_def"]
                    else:
                         loc_folders_to_try = ["loc_eng", "loc_rus", "loc_ger", "loc_def"]

                    for loc_folder in loc_folders_to_try:
                        alt_archive_path_rel = os.path.join("data", "k43t", loc_folder, "packed_data", archive_name)
                        alt_archive_path_abs = os.path.join(current_game_root, alt_archive_path_rel)
                        if os.path.exists(alt_archive_path_abs):
                            archive_path_rel_to_game_root = alt_archive_path_rel
                            archive_path_abs_in_game = alt_archive_path_abs
                            found_loc_archive = True
                            log_message(self.log_area, f"Found localized sound archive at: {alt_archive_path_rel}")
                            break
                if not found_loc_archive:
                    log_message(self.log_area, f"Warning: Sound archive '{archive_name}' not found in common game data paths. Skipping.")
                    continue

            log_message(self.log_area, f"Processing sound archive: {archive_path_rel_to_game_root}")
            archive_base_name = os.path.splitext(archive_name)[0]

            starter_unflat_output_rel = os.path.join("users", "modwork", f"_temp_unflat_sound_{archive_base_name}_{timestamp}")
            starter_unflat_output_abs = os.path.join(current_game_root, starter_unflat_output_rel)
            os.makedirs(os.path.dirname(starter_unflat_output_abs), exist_ok=True)

            log_message(self.log_area, f"  Unpacking '{archive_path_rel_to_game_root}' to game's temp '{starter_unflat_output_rel}'...")
            success, unflat_output_actual_abs = run_starter_command("unflat", [archive_path_rel_to_game_root, starter_unflat_output_rel], self.log_area, timeout=300)

            if not success or not (unflat_output_actual_abs and os.path.isdir(unflat_output_actual_abs)):
                log_message(self.log_area, f"  Failed to unpack sound archive '{archive_name}' or output dir '{unflat_output_actual_abs}' not found. Skipping.")
                if os.path.exists(starter_unflat_output_abs) and self.delete_temp_sound_unflat_var.get():
                    shutil.rmtree(starter_unflat_output_abs)
                continue

            log_message(self.log_area, f"  Successfully unpacked to '{unflat_output_actual_abs}'. Copying sound files to mod project...")
            final_sound_archive_dir_in_project = os.path.join(final_extracted_sounds_base_abs, archive_base_name)
            os.makedirs(final_sound_archive_dir_in_project, exist_ok=True)

            sounds_found_in_archive_count = 0
            for item_name in os.listdir(unflat_output_actual_abs):
                item_path_abs = os.path.join(unflat_output_actual_abs, item_name)
                # Check if the item_name ends with any of the specified sound file extensions
                if os.path.isfile(item_path_abs) and any(item_name.lower().endswith(ext) for ext in sound_file_extensions):
                    sounds_found_in_archive_count += 1
                    dest_sound_file_in_project_abs = os.path.join(final_sound_archive_dir_in_project, item_name)
                    try:
                        shutil.copy2(item_path_abs, dest_sound_file_in_project_abs)
                        listbox_entry = os.path.join(archive_base_name, item_name)
                        all_extracted_sound_files_for_list.append(listbox_entry)
                        self.extracted_sound_listbox.insert(tk.END, listbox_entry)
                        self.extracted_sound_listbox.see(tk.END)
                    except Exception as e:
                        log_message(self.log_area, f"    Error copying sound file {item_name} to project: {e}")

            if sounds_found_in_archive_count == 0:
                log_message(self.log_area, f"  No recognized sound files (e.g., {', '.join(sound_file_extensions)}) found in unpacked '{unflat_output_actual_abs}'.")
            else:
                log_message(self.log_area, f"  Finished processing {sounds_found_in_archive_count} sound files from '{archive_name}'. Copied to '{final_sound_archive_dir_in_project}'.")

            if os.path.exists(starter_unflat_output_abs) and self.delete_temp_sound_unflat_var.get():
                try:
                    shutil.rmtree(starter_unflat_output_abs)
                    log_message(self.log_area, f"  Cleaned up temporary unpack directory: {starter_unflat_output_abs}")
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove game temp unpack dir {starter_unflat_output_abs}: {e}")
            elif os.path.exists(starter_unflat_output_abs):
                 log_message(self.log_area, f"  Kept temporary unpack directory: {starter_unflat_output_abs}")

            self.root.update_idletasks()

        log_message(self.log_area, "Game sound archive extraction process finished.")
        if not all_extracted_sound_files_for_list:
            log_message(self.log_area, "No sound files were successfully extracted from the selected archives.")
        else:
            messagebox.showinfo("Extraction Complete", f"Sound archive extraction complete. Check the 'extracted_game_sounds' folder in your Mod Project Directory and the list.")


    def save_extracted_texture_list(self):
        if self.extracted_texture_listbox.size() == 0:
            messagebox.showinfo("No List", "Texture list is empty. Extract some textures first.")
            return
        current_mod_project_dir = self.mod_project_dir_var.get()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Extracted Texture List As",
            initialdir=current_mod_project_dir or os.getcwd()
        )
        if not filepath: return
        try:
            with open(filepath, "w", encoding='utf-8') as f:
                for i in range(self.extracted_texture_listbox.size()):
                    f.write(self.extracted_texture_listbox.get(i) + "\n")
            log_message(self.log_area, f"Extracted texture list saved to: {filepath}")
            messagebox.showinfo("Saved", f"List saved to {filepath}")
        except Exception as e:
            log_message(self.log_area, f"Error saving texture list: {e}")
            messagebox.showerror("Error", f"Could not save list: {e}")

    def save_extracted_sound_list(self):
        if self.extracted_sound_listbox.size() == 0:
            messagebox.showinfo("No List", "Sound file list is empty. Extract some sound archives first.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Extracted Sound File List As",
            initialdir=current_mod_project_dir or os.getcwd()
        )
        if not filepath: return

        try:
            with open(filepath, "w", encoding='utf-8') as f:
                for i in range(self.extracted_sound_listbox.size()):
                    f.write(self.extracted_sound_listbox.get(i) + "\n")
            log_message(self.log_area, f"Extracted sound file list saved to: {filepath}")
            messagebox.showinfo("Saved", f"List saved to {filepath}")
        except Exception as e:
            log_message(self.log_area, f"Error saving sound file list: {e}")
            messagebox.showerror("Error", f"Could not save list: {e}")

    def convert_atf_to_dds_for_modding(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for ATF to DDS conversion.")
            return
        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        suggested_atf_dir = os.path.join(current_mod_project_dir, "extracted_game_textures", "atf")
        if not os.path.isdir(suggested_atf_dir):
            suggested_atf_dir = os.path.join(current_game_root, "data")
        if not os.path.isdir(suggested_atf_dir):
            suggested_atf_dir = current_game_root
        source_atf_files_abs = filedialog.askopenfilenames(
            title="Select .texture (ATF) files to convert for modding",
            initialdir=suggested_atf_dir,
            filetypes=[("Texture files", "*.texture"), ("All files", "*.*")]
        )
        if not source_atf_files_abs: return
        output_dds_dir_abs = os.path.join(current_mod_project_dir, "dds_work")
        log_message(self.log_area, f"Starting ATF to DDS conversion for {len(source_atf_files_abs)} file(s)...")
        success_count = 0
        for atf_path_abs in source_atf_files_abs:
            filename = os.path.basename(atf_path_abs)
            base, _ = os.path.splitext(filename)
            dds_filename = base + ".dds"
            temp_dds_output_base_dir_rel = os.path.join("users", "modwork")
            temp_dds_output_rel = os.path.join(temp_dds_output_base_dir_rel, f"_temp_modding_{dds_filename}")
            temp_dds_output_abs = os.path.join(current_game_root, temp_dds_output_rel)
            os.makedirs(os.path.dirname(temp_dds_output_abs), exist_ok=True)
            final_dds_path_abs = os.path.join(output_dds_dir_abs, dds_filename)
            param_atf_path_rel = os.path.relpath(atf_path_abs, current_game_root)
            log_message(self.log_area, f"Converting: {param_atf_path_rel} -> temp {temp_dds_output_rel}")
            conv_success, _ = run_starter_command("atf2dds", [param_atf_path_rel, temp_dds_output_rel], self.log_area)
            if conv_success and os.path.exists(temp_dds_output_abs):
                try:
                    shutil.move(temp_dds_output_abs, final_dds_path_abs)
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_dds_path_abs}")
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted DDS {dds_filename} to {output_dds_dir_abs}: {e}")
                    if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp DDS not found at {temp_dds_output_abs}.")
                if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs)
        log_message(self.log_area, f"ATF to DDS conversion finished. {success_count}/{len(source_atf_files_abs)} successful. DDS files in '{output_dds_dir_abs}'")

    def convert_dds_to_atf_for_modding(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for DDS to ATF conversion.")
            return
        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        source_dds_dir_abs = os.path.join(current_mod_project_dir, "dds_work")
        source_dds_files_abs = filedialog.askopenfilenames(
            title="Select .dds files from 'dds_work' to convert",
            initialdir=source_dds_dir_abs,
            filetypes=[("DDS files", "*.dds"), ("All files", "*.*")]
        )
        if not source_dds_files_abs: return
        output_atf_dir_abs = os.path.join(current_mod_project_dir, "prepared_textures")
        log_message(self.log_area, f"Starting DDS to ATF conversion for {len(source_dds_files_abs)} file(s)...")
        success_count = 0
        for dds_path_abs in source_dds_files_abs:
            filename = os.path.basename(dds_path_abs)
            base, _ = os.path.splitext(filename)
            atf_filename = base + ".texture"
            temp_atf_output_base_dir_rel = os.path.join("users", "modwork")
            temp_atf_output_rel = os.path.join(temp_atf_output_base_dir_rel, f"_temp_modding_{atf_filename}")
            temp_atf_output_abs = os.path.join(current_game_root, temp_atf_output_rel)
            os.makedirs(os.path.dirname(temp_atf_output_abs), exist_ok=True)
            final_atf_path_abs = os.path.join(output_atf_dir_abs, atf_filename)
            param_dds_path_rel = os.path.relpath(dds_path_abs, current_game_root)
            log_message(self.log_area, f"Converting: {param_dds_path_rel} -> temp {temp_atf_output_rel}")
            conv_success, _ = run_starter_command("dds2atf", [param_dds_path_rel, temp_atf_output_rel], self.log_area)
            if conv_success and os.path.exists(temp_atf_output_abs):
                try:
                    shutil.move(temp_atf_output_abs, final_atf_path_abs)
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_atf_path_abs}")
                    success_count +=1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted ATF {atf_filename} to {output_atf_dir_abs}: {e}")
                    if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp ATF not found at {temp_atf_output_abs}.")
                if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)
        log_message(self.log_area, f"DDS to ATF conversion finished. {success_count}/{len(source_dds_files_abs)} successful. Texture files in '{output_atf_dir_abs}'")
        self.load_prepared_assets()

    def convert_wav_to_aaf(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for WAV to game sound conversion.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        sound_category = self.sound_type_var.get()

        output_subfolder = "sfx" if sound_category == "SFX" else "speech"
        final_output_dir_abs = os.path.join(current_mod_project_dir, "prepared_sounds", output_subfolder)

        suggested_wav_dir = os.path.join(current_mod_project_dir, f"wav_{output_subfolder}_work")
        if not os.path.isdir(suggested_wav_dir):
            suggested_wav_dir = current_mod_project_dir

        source_wav_files_abs = filedialog.askopenfilenames(
            title=f"Select .wav files for {sound_category} to .loc_def.sound conversion", # Updated title
            initialdir=suggested_wav_dir,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if not source_wav_files_abs: return

        log_message(self.log_area, f"Starting WAV to .loc_def.sound ({sound_category}) conversion for {len(source_wav_files_abs)} file(s)...") # Updated log
        success_count = 0
        for wav_path_abs in source_wav_files_abs:
            filename = os.path.basename(wav_path_abs)
            base, _ = os.path.splitext(filename)
            # New target filename format
            target_sound_filename = base + ".loc_def.sound"

            # Temporary output location for starter.exe, using the new target format
            temp_output_base_dir_rel = os.path.join("users", "modwork")
            temp_output_filename_rel = os.path.join(temp_output_base_dir_rel, f"_temp_conv_{target_sound_filename}") # Use full target name for temp
            temp_output_path_abs = os.path.join(current_game_root, temp_output_filename_rel)
            os.makedirs(os.path.dirname(temp_output_path_abs), exist_ok=True)

            # Final destination in the mod project's prepared_sounds subfolder
            final_sound_path_abs = os.path.join(final_output_dir_abs, target_sound_filename)

            param_wav_path_rel = os.path.relpath(wav_path_abs, current_game_root)
            # starter.exe wav2aaf, <input.wav>, <output.loc_def.sound> (as per PDF example for output extension)
            log_message(self.log_area, f"Converting: {param_wav_path_rel} -> temp {temp_output_filename_rel}")
            conv_success, _ = run_starter_command("wav2aaf", [param_wav_path_rel, temp_output_filename_rel], self.log_area)

            if conv_success and os.path.exists(temp_output_path_abs):
                try:
                    shutil.move(temp_output_path_abs, final_sound_path_abs)
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_sound_path_abs}")
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted sound file {target_sound_filename} to {final_output_dir_abs}: {e}")
                    if os.path.exists(temp_output_path_abs): os.remove(temp_output_path_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp sound file not found at {temp_output_path_abs}.")
                if os.path.exists(temp_output_path_abs): os.remove(temp_output_path_abs)
        
        log_message(self.log_area, f"WAV to .loc_def.sound ({sound_category}) conversion finished. {success_count}/{len(source_wav_files_abs)} successful. Files in '{final_output_dir_abs}'") # Updated log
        self.load_prepared_assets()

    def load_prepared_assets(self):
        self.packaged_assets_listbox.delete(0, tk.END)
        current_mod_project_dir = self.mod_project_dir_var.get()
        if not current_mod_project_dir:
            log_message(self.log_area, "Mod Project Directory not set. Cannot load assets.")
            return
        total_found = 0
        # self.asset_types_to_scan is now updated via self.flatdata_definitions to look for .loc_def.sound
        for asset_type_info in self.asset_types_to_scan:
            asset_dir = os.path.join(current_mod_project_dir, asset_type_info["folder"])
            if os.path.isdir(asset_dir):
                count_this_type = 0
                for item in sorted(os.listdir(asset_dir)):
                    if item.lower().endswith(asset_type_info["ext"]): # ext is now .loc_def.sound for sounds
                        self.packaged_assets_listbox.insert(tk.END, f"{asset_type_info['prefix']} {item}")
                        count_this_type += 1
                        total_found +=1
                if count_this_type > 0:
                    log_message(self.log_area, f"Found {count_this_type} {asset_type_info['ext']} files in '{asset_type_info['folder']}'.")
        if total_found == 0:
            log_message(self.log_area, "No prepared asset files found in expected 'prepared_...' subfolders (textures, sfx, speech).")
        else:
            log_message(self.log_area, f"Total {total_found} prepared asset files loaded. Select files to include in the mod package.")

    def _generate_desc_addpack_file(self, mod_name, author, version, core_dir_abs, game_root_dir):
        stencil_dir_abs = os.path.join(game_root_dir, "docs", "modwork", "stencil")
        template_filename = "desc_example.addpack.engcfg2"
        template_path_abs = os.path.join(stencil_dir_abs, template_filename)
        if not os.path.exists(template_path_abs):
            log_message(self.log_area, f"Error: Template '{template_filename}' not found at {template_path_abs}")
            messagebox.showerror("Template Missing", f"Addon template '{template_filename}' not found in game docs: {template_path_abs}")
            return False
        desc_engcfg2_content = None
        encodings_to_try = ['utf-8-sig', 'utf-8', 'windows-1251', 'latin-1']
        for enc in encodings_to_try:
            try:
                with open(template_path_abs, "r", encoding=enc) as f:
                    desc_engcfg2_content = f.read()
                log_message(self.log_area, f"Successfully read template '{template_filename}' with {enc} encoding.")
                break
            except UnicodeDecodeError:
                log_message(self.log_area, f"Warning: Failed to decode template '{template_filename}' with {enc} (UnicodeDecodeError).")
            except Exception as e:
                log_message(self.log_area, f"Warning: Failed to read template '{template_filename}' with {enc}: {e}")
        if desc_engcfg2_content is None:
            log_message(self.log_area, f"Critical Error: Could not read/decode template file '{template_filename}'. Please check the file encoding.")
            messagebox.showerror("Template Read Error", f"Could not read/decode addon template '{template_filename}'.")
            return False
        sanitized_mod_name_for_path = re.sub(r'[^\w\s_-]', '_', mod_name).strip()
        sanitized_mod_name_for_path = re.sub(r'\s+', '_', sanitized_mod_name_for_path)
        if not sanitized_mod_name_for_path: sanitized_mod_name_for_path = "MyMod"
        installer_mod_path = f"mods/{sanitized_mod_name_for_path}"
        log_message(self.log_area, f"Setting installer path in desc.addpack to: {installer_mod_path}")
        desc_engcfg2_content = desc_engcfg2_content.replace("<my_updates>", installer_mod_path)
        desc_engcfg2_content = desc_engcfg2_content.replace("<My Addon>", mod_name)
        desc_engcfg2_content = desc_engcfg2_content.replace("<Vasya Pupkin>", author)
        desc_engcfg2_content = re.sub(r"version\[u\]\s*=\s*\d+", f"version[u] = {version}", desc_engcfg2_content)
        if "type[*]=" not in desc_engcfg2_content:
             desc_engcfg2_content += "\ntype[*]= RES;\n"
        elif "type[*] = ADDN" in desc_engcfg2_content or "type[*] = CAMP" in desc_engcfg2_content:
            pass
        else:
            desc_engcfg2_content = re.sub(r"type\[\*\]\s*=\s*\w+;", "type[*]= RES;", desc_engcfg2_content)
        temp_desc_engcfg2_name = "_temp_desc.addpack.engcfg2"
        temp_desc_engcfg2_path_rel = os.path.join("users", "modwork", temp_desc_engcfg2_name)
        temp_desc_engcfg2_path_abs = os.path.join(game_root_dir, temp_desc_engcfg2_path_rel)
        os.makedirs(os.path.dirname(temp_desc_engcfg2_path_abs), exist_ok=True)
        try:
            with open(temp_desc_engcfg2_path_abs, "w", encoding='utf-8') as f:
                f.write(desc_engcfg2_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing temporary desc file '{temp_desc_engcfg2_path_abs}': {e}")
            return False
        final_desc_addpack_path_abs = os.path.join(core_dir_abs, "desc.addpack")
        temp_desc_addpack_output_name = "_temp_desc.addpack"
        temp_desc_addpack_output_rel = os.path.join("users", "modwork", temp_desc_addpack_output_name)
        temp_desc_addpack_output_abs = os.path.join(game_root_dir, temp_desc_addpack_output_rel)
        log_message(self.log_area, "Generating desc.addpack...")
        gen_success, _ = run_starter_command("pd2cfgp", [temp_desc_engcfg2_path_rel, temp_desc_addpack_output_rel], self.log_area)
        if os.path.exists(temp_desc_engcfg2_path_abs):
            try: os.remove(temp_desc_engcfg2_path_abs)
            except: pass
        if not gen_success or not os.path.exists(temp_desc_addpack_output_abs):
            log_message(self.log_area, "Error generating desc.addpack or temp output not found.")
            if os.path.exists(temp_desc_addpack_output_abs): os.remove(temp_desc_addpack_output_abs)
            return False
        try:
            shutil.move(temp_desc_addpack_output_abs, final_desc_addpack_path_abs)
            log_message(self.log_area, f"desc.addpack created at {final_desc_addpack_path_abs}")
            return True
        except Exception as e:
            log_message(self.log_area, f"Error moving generated desc.addpack to project: {e}")
            if os.path.exists(temp_desc_addpack_output_abs): os.remove(temp_desc_addpack_output_abs)
            return False

    def _package_asset_archive(self, flatlist_name_stem, mkflat_file_type,
                               files_to_package, game_root_dir, core_dir_abs):
        if not files_to_package:
            log_message(self.log_area, f"No files provided for packaging into {flatlist_name_stem}.flatdata. Skipping.")
            return True
        log_message(self.log_area, f"Packaging {len(files_to_package)} assets into {flatlist_name_stem}.flatdata...")
        mkflat_staging_dir_name = f"_mkflat_stage_{flatlist_name_stem}_{time.strftime('%Y%m%d%H%M%S')}"
        mkflat_staging_dir_rel = os.path.join("users", "modwork", mkflat_staging_dir_name)
        mkflat_staging_dir_abs = os.path.join(game_root_dir, mkflat_staging_dir_rel)
        os.makedirs(mkflat_staging_dir_abs, exist_ok=True)
        flatlist_content = "i_unflat:unflat()\n{\n"
        for abs_src_path_in_project, staging_filename in files_to_package:
            # staging_filename is now like "my_sound.loc_def.sound" or "my_texture.texture"
            # We need the base name for the flatlist entry, e.g., "my_sound" or "my_texture"
            flatlist_entry_name = staging_filename
            if flatlist_entry_name.lower().endswith(".loc_def.sound"):
                flatlist_entry_name = flatlist_entry_name[:-len(".loc_def.sound")]
            elif flatlist_entry_name.lower().endswith(".texture"): # Handle textures too
                flatlist_entry_name = flatlist_entry_name[:-len(".texture")]
            # Add other specific known extensions if necessary, or a more generic splitext
            # For now, this covers the current asset types.

            flatlist_content += f"    {flatlist_entry_name}\t, {mkflat_file_type}\t, loc_def ;\n" # mkflat_file_type is 'sound' or 'texture'
            
            dst_asset_for_mkflat_path_abs = os.path.join(mkflat_staging_dir_abs, staging_filename)
            if os.path.exists(abs_src_path_in_project):
                try:
                    shutil.copy2(abs_src_path_in_project, dst_asset_for_mkflat_path_abs)
                except Exception as e:
                    log_message(self.log_area, f"Error copying {staging_filename} from {abs_src_path_in_project} to mkflat staging {dst_asset_for_mkflat_path_abs}: {e}")
                    if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
                    return False
            else:
                log_message(self.log_area, f"Warning: Source asset {abs_src_path_in_project} not found for copying. Skipping this file for {flatlist_name_stem}.flatdata.")
                if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
                return False
        flatlist_content += "}\n"
        flatlist_filename_for_mkflat = f"{flatlist_name_stem}.!flatlist"
        flatlist_path_in_staging_abs = os.path.join(mkflat_staging_dir_abs, flatlist_filename_for_mkflat)
        flatlist_path_in_staging_rel = os.path.relpath(flatlist_path_in_staging_abs, game_root_dir)
        try:
            with open(flatlist_path_in_staging_abs, "w", encoding='utf-8') as f:
                f.write(flatlist_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing {flatlist_filename_for_mkflat} to staging: {e}")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return False
        flatdata_output_in_staging_rel = os.path.join(mkflat_staging_dir_rel, f"{flatlist_name_stem}.flatdata")
        flatdata_output_in_staging_abs = os.path.join(game_root_dir, flatdata_output_in_staging_rel)
        final_flatdata_target_in_project_abs = os.path.join(core_dir_abs, "shared", "packed_data", f"{flatlist_name_stem}.flatdata")
        mk_success, _ = run_starter_command("mkflat", [flatdata_output_in_staging_rel, flatlist_path_in_staging_rel], self.log_area)
        if not mk_success or not os.path.exists(flatdata_output_in_staging_abs):
            log_message(self.log_area, f"Error generating {flatlist_name_stem}.flatdata or output not found in staging at {flatdata_output_in_staging_abs}.")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return False
        try:
            os.makedirs(os.path.dirname(final_flatdata_target_in_project_abs), exist_ok=True)
            shutil.move(flatdata_output_in_staging_abs, final_flatdata_target_in_project_abs)
            log_message(self.log_area, f"{flatlist_name_stem}.flatdata created at {final_flatdata_target_in_project_abs}")
            return True
        except Exception as e:
            log_message(self.log_area, f"Error moving generated {flatlist_name_stem}.flatdata to project: {e}")
            return False
        finally:
            if os.path.exists(mkflat_staging_dir_abs):
                try:
                    shutil.rmtree(mkflat_staging_dir_abs)
                except Exception as e:
                    log_message(self.log_area, f"Warning: Could not remove mkflat staging for {flatlist_name_stem}: {e}")

    def generate_mod_files(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for packaging.")
            return
        mod_name_val = self.mod_name_var.get()
        mod_author_val = self.mod_author_var.get()
        mod_version_val = self.mod_version_var.get()
        if not all([mod_name_val, mod_author_val, mod_version_val]):
            messagebox.showerror("Error", "Mod Name, Author, and Version must be set in the 'Project Setup' tab.")
            return
        selected_indices = self.packaged_assets_listbox.curselection()
        if not selected_indices:
            messagebox.showerror("No Selection", "No asset files selected from the list to package.")
            log_message(self.log_area, "Error: No assets selected to package.")
            return
        selected_asset_filenames_with_prefix = [self.packaged_assets_listbox.get(i) for i in selected_indices]
        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        core_dir_abs = os.path.join(current_mod_project_dir, "CORE")
        if not self._generate_desc_addpack_file(mod_name_val, mod_author_val, mod_version_val, core_dir_abs, current_game_root):
            messagebox.showerror("Error", "Failed to generate desc.addpack. Check log.")
            return
        all_archives_successful = True
        archives_packaged_count = 0
        for flatlist_stem, definition in self.flatdata_definitions.items():
            mkflat_type = definition["mkflat_type"]
            files_for_this_flatdata_archive = []
            for source_config in definition["sources"]:
                prefix_to_match = source_config["prefix"] + " "
                source_folder_abs_in_project = os.path.join(current_mod_project_dir, source_config["folder"])
                for selected_file_with_prefix in selected_asset_filenames_with_prefix:
                    if selected_file_with_prefix.startswith(prefix_to_match):
                        asset_filename = selected_file_with_prefix.replace(prefix_to_match, "")
                        original_asset_path_abs_in_project = os.path.join(source_folder_abs_in_project, asset_filename)
                        files_for_this_flatdata_archive.append(
                            (original_asset_path_abs_in_project, asset_filename)
                        )
            if files_for_this_flatdata_archive:
                success = self._package_asset_archive(
                    flatlist_name_stem=flatlist_stem,
                    mkflat_file_type=mkflat_type,
                    files_to_package=files_for_this_flatdata_archive,
                    game_root_dir=current_game_root,
                    core_dir_abs=core_dir_abs
                )
                if success:
                    archives_packaged_count +=1
                else:
                    all_archives_successful = False
                    log_message(self.log_area, f"Failed to package {flatlist_stem}.flatdata.")
        if archives_packaged_count == 0 and any(selected_asset_filenames_with_prefix):
             log_message(self.log_area, "No asset archives were generated. Ensure selected files match defined types (e.g., [TEX], [SFX], [SPE]) and their 'prepared_...' folders exist.")
             messagebox.showwarning("Packaging Skipped", "No asset archives were generated. Check prefixes and file locations of selected items.")
             return
        if all_archives_successful and archives_packaged_count > 0:
            log_message(self.log_area, "All selected mod files generated successfully in CORE directory.")
            messagebox.showinfo("Success", "Mod files (desc.addpack and selected .flatdata archives) generated successfully!")
        elif archives_packaged_count > 0 :
            log_message(self.log_area, "Some mod files generated, but errors occurred with others. Check log.")
            messagebox.showwarning("Partial Success", "Some mod files generated, but errors occurred. Check log.")
        elif archives_packaged_count == 0 and not any(selected_asset_filenames_with_prefix) :
            log_message(self.log_area, "desc.addpack generated, but no assets were selected for packaging.")
            messagebox.showinfo("desc.addpack Generated", "desc.addpack generated. No assets were selected to package into .flatdata archives.")
        else:
            log_message(self.log_area, "Failed to generate mod asset files. desc.addpack might have been created. Check log.")
            messagebox.showerror("Error", "Failed to generate mod asset files. Check log for details.")

    def create_mod_archive(self):
        if not self._validate_paths(check_mod_project=True, check_starter=False): return
        mod_name_val = self.mod_name_var.get()
        mod_name_for_archive = self.mod_name_var.get()
        mod_name_for_archive = re.sub(r'[^\w\s_-]', '_', mod_name_for_archive).strip()
        mod_name_for_archive = re.sub(r'\s+', '_', mod_name_for_archive)
        if not mod_name_for_archive: mod_name_for_archive = "MyMod"
        if not mod_name_val:
            messagebox.showerror("Error", "Mod Name (from Project Setup tab) must be set to create an archive.")
            log_message(self.log_area, "Error: Mod Name must be set for archive creation.")
            return
        current_mod_project_dir = self.mod_project_dir_var.get()
        core_dir_to_archive = os.path.join(current_mod_project_dir, "CORE")
        readme_file_to_archive = os.path.join(current_mod_project_dir, "readme.txt")
        if not os.path.isdir(core_dir_to_archive) or not os.path.exists(os.path.join(core_dir_to_archive,"desc.addpack")):
            messagebox.showerror("Error", "CORE directory or desc.addpack not found. Generate mod files first (Step 1 on this tab).")
            log_message(self.log_area, "Error: CORE/desc.addpack not found. Generate mod files first.")
            return
        if not os.path.exists(readme_file_to_archive):
            log_message(self.log_area, f"readme.txt not found at {readme_file_to_archive}. Creating a basic one.")
            try:
                with open(readme_file_to_archive, "w", encoding='utf-8') as f:
                    f.write(f"Mod: {mod_name_val}\n")
                    f.write(f"Author: {self.mod_author_var.get() or 'Unknown'}\n")
                    f.write(f"Version: {self.mod_version_var.get() or '100'}\n\n")
                    f.write("Basic mod description. Please edit this readme.txt in your Mod Project Directory.")
            except Exception as e:
                log_message(self.log_area, f"Warning: Could not create readme.txt: {e}")
        initial_save_dir = os.path.dirname(current_mod_project_dir) if os.path.dirname(current_mod_project_dir) else current_mod_project_dir
        archive_save_path = filedialog.asksaveasfilename(
            title="Save Mod Archive As",
            initialdir=initial_save_dir,
            initialfile=f"{mod_name_for_archive}.gt2extension",
            defaultextension=".gt2extension",
            filetypes=[("Graviteam Mod Archive", "*.gt2extension"), ("Zip files", "*.zip")]
        )
        if not archive_save_path:
            log_message(self.log_area, "Mod archive creation cancelled.")
            return
        if not archive_save_path.lower().endswith(".gt2extension"):
            archive_save_path = os.path.splitext(archive_save_path)[0] + ".gt2extension"
        temp_zip_base_name = os.path.splitext(archive_save_path)[0] + "_temp_zip_for_gt2ext"
        staging_dir = None
        try:
            staging_dir = os.path.join(current_mod_project_dir, "_archive_staging_temp")
            if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
            os.makedirs(staging_dir)
            shutil.copytree(core_dir_to_archive, os.path.join(staging_dir, "CORE"))
            if os.path.exists(readme_file_to_archive):
                shutil.copy2(readme_file_to_archive, os.path.join(staging_dir, "readme.txt"))
            shutil.make_archive(base_name=temp_zip_base_name,
                                format='zip',
                                root_dir=staging_dir)
            created_zip_file = temp_zip_base_name + ".zip"
            if os.path.exists(archive_save_path):
                os.remove(archive_save_path)
            shutil.move(created_zip_file, archive_save_path)
            log_message(self.log_area, f"Mod archive created: {archive_save_path}")
            messagebox.showinfo("Success", f"Mod archive (.gt2extension) created: {archive_save_path}")
        except Exception as e:
            log_message(self.log_area, f"Error creating mod archive: {e}")
            messagebox.showerror("Error", f"Error creating mod archive: {e}")
        finally:
            if staging_dir and os.path.exists(staging_dir):
                try:
                    shutil.rmtree(staging_dir)
                except Exception as e_rm:
                    log_message(self.log_area, f"Warning: Could not remove staging directory {staging_dir}: {e_rm}")
            if 'created_zip_file' in locals() and os.path.exists(created_zip_file) and created_zip_file != archive_save_path :
                try:
                    os.remove(created_zip_file)
                except Exception as e_rm_zip:
                    log_message(self.log_area, f"Warning: Could not remove temporary zip file {created_zip_file}: {e_rm_zip}")

app = None
if __name__ == "__main__":
    root = tk.Tk()
    app = TextureModTool(root)
    root.mainloop()
