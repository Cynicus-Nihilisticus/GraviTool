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
        # Position tooltip below the widget
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
XWMA_ENCODE_PATH_CONFIG = "" # Path to xWMAEncode.exe

# --- Helper Functions ---
def load_config():
    global GAME_ROOT_DIR, MOD_PROJECT_DIR, XWMA_ENCODE_PATH_CONFIG
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        GAME_ROOT_DIR = config.get("Paths", "GameRootDir", fallback="")
        MOD_PROJECT_DIR = config.get("Paths", "ModProjectDir", fallback="")
        XWMA_ENCODE_PATH_CONFIG = config.get("Paths", "XWMAEncodePath", fallback="")
        update_starter_exe_path()
    if 'app' in globals() and app:
        if hasattr(app, 'game_root_var'): app.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(app, 'mod_project_dir_var'): app.mod_project_dir_var.set(MOD_PROJECT_DIR)
        if hasattr(app, 'xwma_encode_path_var'): app.xwma_encode_path_var.set(XWMA_ENCODE_PATH_CONFIG)


def save_config():
    config = configparser.ConfigParser()
    config["Paths"] = {
        "GameRootDir": GAME_ROOT_DIR,
        "ModProjectDir": MOD_PROJECT_DIR,
        "XWMAEncodePath": XWMA_ENCODE_PATH_CONFIG
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
        # Ensure all params are strings, handle None by converting to empty string
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
        # Specific handling for unflat to return the output directory
        if command_name == "unflat" and len(params_list) > 1 and params_list[1]:
             return True, os.path.join(GAME_ROOT_DIR, params_list[1])
        return True, None # General success
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
        self.root.title("Graviteam Asset Mod Tool (GTOS)")
        self.root.geometry("950x900") # Increased height for new tab

        # --- Log Area ---
        log_main_frame = ttk.Frame(self.root)
        log_frame = ttk.LabelFrame(log_main_frame, text="Log")
        self.log_area = tk.Text(log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1) # Adjusted height
        log_scroll = tk.Scrollbar(log_frame, command=self.log_area.yview)
        self.log_area.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))
        log_main_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

        load_config()

        # --- Menubar ---
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Set Game Root Directory", command=self.set_game_root)
        filemenu.add_command(label="Set Mod Project Directory", command=self.set_mod_project_dir)
        filemenu.add_command(label="Set xWMAEncode.exe Path", command=self.set_xwma_encode_path)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        # --- Notebook (Tabs) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        setup_tab = ttk.Frame(self.notebook)
        self.notebook.add(setup_tab, text='1. Project Setup')
        self.create_setup_tab(setup_tab)

        extractor_tab = ttk.Frame(self.notebook)
        self.notebook.add(extractor_tab, text='2. Game Texture Extractor')
        self.create_extractor_tab(extractor_tab)

        conversion_tab = ttk.Frame(self.notebook)
        self.notebook.add(conversion_tab, text='3. Mod Texture Conversion')
        self.create_conversion_tab(conversion_tab)
        
        sound_modding_tab = ttk.Frame(self.notebook)
        self.notebook.add(sound_modding_tab, text='4. Sound & Music Modding') 
        self.create_sound_modding_tab(sound_modding_tab)

        packaging_tab = ttk.Frame(self.notebook)
        self.notebook.add(packaging_tab, text='5. Asset Packaging')
        self.create_packaging_tab(packaging_tab)
        
        # Set initial values from loaded config
        if hasattr(self, 'game_root_var'): self.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(self, 'mod_project_dir_var'): self.mod_project_dir_var.set(MOD_PROJECT_DIR)
        if hasattr(self, 'xwma_encode_path_var'): self.xwma_encode_path_var.set(XWMA_ENCODE_PATH_CONFIG) # For display if field exists
        
        if GAME_ROOT_DIR: update_starter_exe_path()
        log_message(self.log_area, "Tool initialized. Set Game Root, Mod Project directories, and xWMAEncode.exe path if not already configured.")

        # Define asset packaging structure
        # This structure will be used by generate_mod_files and _package_asset_archive_new
        self.flatdata_definitions = {
            "textures": {
                "mkflat_type": "texture",
                "sources": [
                    {"prefix": "[TEX]", "folder": "prepared_textures", "ext": ".texture"}
                ]
            },
            "sounds": { # Combines SFX and Speech into sounds.flatdata
                "mkflat_type": "sound",
                "sources": [
                    {"prefix": "[SFX]", "folder": os.path.join("prepared_sounds", "sfx"), "ext": ".aaf"},
                    {"prefix": "[SPE]", "folder": os.path.join("prepared_sounds", "speech"), "ext": ".aaf"}
                ]
            },
            "music": {
                "mkflat_type": "sound", # Music also uses 'sound' type in flatlist
                "sources": [
                    {"prefix": "[MUS]", "folder": os.path.join("prepared_sounds", "music"), "ext": ".xWMA"}
                ]
            }
        }
        # This list is used by load_prepared_assets to populate the listbox
        self.asset_types_to_scan = []
        for definition in self.flatdata_definitions.values():
            for source in definition["sources"]:
                self.asset_types_to_scan.append(source.copy())


    def create_setup_tab(self, tab):
        frame = ttk.Frame(tab, padding="10")
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
        
        # xWMAEncode.exe path display (optional, mainly set via menu)
        ttk.Label(frame, text="xWMAEncode.exe Path:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.xwma_encode_path_var = tk.StringVar(value=XWMA_ENCODE_PATH_CONFIG)
        xwma_entry = ttk.Entry(frame, textvariable=self.xwma_encode_path_var, width=60, state="readonly")
        xwma_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(xwma_entry, "Path to xWMAEncode.exe. Set via File > Set xWMAEncode.exe Path.")
        xwma_set_btn = ttk.Button(frame, text="Set Path", command=self.set_xwma_encode_path)
        xwma_set_btn.grid(row=2, column=2, padx=5, pady=5)
        ToolTip(xwma_set_btn, "Set the path to xWMAEncode.exe (from DirectX SDK).\nNeeded for .wav to .xWMA music conversion.")


        frame.grid_columnconfigure(1, weight=1)

        info_frame = ttk.LabelFrame(frame, text="Mod Information (for desc.addpack & readme.txt)", padding="10")
        info_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky="ew") # Adjusted row

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
        init_folders_button.grid(row=4, column=0, columnspan=3, pady=10) # Adjusted row
        ToolTip(init_folders_button, 
                "Creates standard subfolders for textures, sounds, etc.,\n"
                "within your Mod Project Directory and a template readme.txt if they don't exist.")

    def create_extractor_tab(self, tab):
        frame = ttk.Frame(tab, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="This tool will unpack game texture archives (.flatdata) to your Mod Project Directory, \nconvert them to .dds, and generate a list of available textures.").pack(pady=(0,5))
        
        archive_frame = ttk.LabelFrame(frame, text="Select Game Texture Archives to Extract", padding="10")
        archive_frame.pack(fill=tk.X, pady=5)

        self.texture_archives_vars = {}
        known_texture_archives = [ 
            "tex_main.flatdata", "tex_main_01.flatdata", "tex_misc.flatdata", "tex_objects.flatdata",
            "tex_humans.flatdata", "tex_techns.flatdata", "tex_dummy.flatdata", "textures_loc.flatdata" # Added more common ones
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

        extract_button = ttk.Button(frame, text="1. Unpack Selected Archives & Convert to DDS", command=self.extract_and_convert_game_textures)
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
        self.extracted_texture_listbox = tk.Listbox(listbox_container_frame, height=10, relief=tk.SUNKEN, borderwidth=1)
        list_scroll = tk.Scrollbar(listbox_container_frame, orient=tk.VERTICAL, command=self.extracted_texture_listbox.yview)
        self.extracted_texture_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.extracted_texture_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        save_list_button = ttk.Button(frame, text="Save List to File", command=self.save_extracted_texture_list)
        save_list_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(save_list_button, "Saves the list of extracted .dds texture paths (shown above) to a text file.")

    def create_conversion_tab(self, tab):
        frame = ttk.Frame(tab, padding="10")
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

    def create_sound_modding_tab(self, tab):
        frame = ttk.Frame(tab, padding="10")
        frame.pack(expand=True, fill='both')

        # --- WAV to AAF (SFX/Speech) ---
        aaf_frame = ttk.LabelFrame(frame, text="Convert .wav to .aaf (Game Sound Effects / Speech)", padding="10")
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

        wav_to_aaf_button = ttk.Button(aaf_frame, text="Select .wav File(s) and Convert to .aaf", command=self.convert_wav_to_aaf)
        wav_to_aaf_button.pack(fill=tk.X, pady=5)
        ToolTip(wav_to_aaf_button, "Uses 'starter.exe wav2aaf'.\nOutput .aaf files are saved in the selected 'prepared_sounds' subfolder.")

        # --- WAV to xWMA (Music) ---
        xwma_frame = ttk.LabelFrame(frame, text="Convert .wav to .xWMA (Game Music)", padding="10")
        xwma_frame.pack(fill=tk.X, pady=10)

        ttk.Label(xwma_frame, text="Input .wav format: 44.1kHz, 16-bit Stereo recommended.").pack(anchor="w", pady=(0,5))
        ttk.Label(xwma_frame, text="Requires xWMAEncode.exe (from DirectX SDK).").pack(anchor="w", pady=(0,2))
        ttk.Label(xwma_frame, text="Ensure xWMAEncode.exe is in your Game Root, system PATH, or set its path via File menu.").pack(anchor="w", pady=(0,5))

        wav_to_xwma_button = ttk.Button(xwma_frame, text="Select .wav File(s) and Convert to .xWMA", command=self.convert_wav_to_xwma)
        wav_to_xwma_button.pack(fill=tk.X, pady=5)
        ToolTip(wav_to_xwma_button, "Uses 'xWMAEncode.exe'.\nOutput .xWMA files are saved in 'ModProjectDir/prepared_sounds/music/'.")

        # --- Info Area ---
        info_text = (
            "General Notes:\n"
            "- .aaf files are used for sound effects and speech.\n"
            "- .xWMA files are used for music.\n"
            "- After conversion, refresh the list in the 'Asset Packaging' tab to include them in your mod."
        )
        ttk.Label(frame, text=info_text, justify=tk.LEFT, wraplength=frame.winfo_width()-40).pack(pady=10, anchor="w")


    def create_packaging_tab(self, tab):
        frame = ttk.Frame(tab, padding="10")
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
                                 "'ModProjectDir/prepared_textures/' and 'ModProjectDir/prepared_sounds/...'.")
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        generate_files_button = ttk.Button(frame, text="1. Generate Mod Files (desc.addpack & .flatdata archives)", command=self.generate_mod_files)
        generate_files_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(generate_files_button,
                "For selected assets:\n"
                "- Creates 'desc.addpack' in 'CORE/'.\n"
                "- Creates appropriate '.!flatlist' files in a temporary staging area.\n"
                "- Copies selected asset files to the staging area.\n"
                "- Creates '.flatdata' archives (e.g., textures.flatdata, sounds.flatdata, music.flatdata)\n"
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
            update_starter_exe_path() # Ensures STARTER_EXE_PATH is current
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
            update_starter_exe_path() # Update starter.exe path when game root changes
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
            self.initialize_mod_folders(silent=True) # Attempt to initialize/verify folders

    def set_xwma_encode_path(self):
        global XWMA_ENCODE_PATH_CONFIG
        filepath = filedialog.askopenfilename(
            title="Select xWMAEncode.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filepath:
            self.xwma_encode_path_var.set(filepath)
            XWMA_ENCODE_PATH_CONFIG = filepath
            save_config()
            log_message(self.log_area, f"xWMAEncode.exe path set to: {XWMA_ENCODE_PATH_CONFIG}")

    def _get_xwma_encoder_path(self):
        """Attempts to find xWMAEncode.exe."""
        # 1. From config (set via UI)
        if XWMA_ENCODE_PATH_CONFIG and os.path.exists(XWMA_ENCODE_PATH_CONFIG):
            return XWMA_ENCODE_PATH_CONFIG
        
        # 2. In Game Root Directory
        if GAME_ROOT_DIR:
            path_in_game_root = os.path.join(GAME_ROOT_DIR, "xWMAEncode.exe")
            if os.path.exists(path_in_game_root):
                log_message(self.log_area, f"Found xWMAEncode.exe in Game Root: {path_in_game_root}")
                return path_in_game_root
        
        # 3. In system PATH
        path_in_system = shutil.which("xWMAEncode.exe")
        if path_in_system:
            log_message(self.log_area, f"Found xWMAEncode.exe in system PATH: {path_in_system}")
            return path_in_system
            
        log_message(self.log_area, "Error: xWMAEncode.exe not found. Please set its path via File > Set xWMAEncode.exe Path, or place it in the Game Root directory.")
        messagebox.showerror("xWMAEncode.exe Not Found",
                             "xWMAEncode.exe could not be located. Please set its path via the File menu "
                             "or ensure it's in your Game Root directory or system PATH.")
        return None

    def initialize_mod_folders(self, silent=False):
        if not self._validate_paths(check_mod_project=True, check_starter=False): # Starter not strictly needed for folder creation
            # If mod project dir is not set, _validate_paths will show error and return False.
            # If it is set but doesn't exist, _validate_paths logs it but returns True.
            # We need to ensure mod_project_dir_var is not empty.
            if not self.mod_project_dir_var.get():
                 if not silent:
                    log_message(self.log_area, "Mod project directory not set, cannot initialize folders.")
                    messagebox.showerror("Error", "Mod Project Directory is not set. Cannot initialize folders.")
                 return False
        
        current_mod_project_dir = self.mod_project_dir_var.get()
        # At this point, current_mod_project_dir should be set.

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
            "CORE_dir": os.path.join(current_mod_project_dir, "CORE"), # For desc.addpack
            "CORE_shared_packed_data": os.path.join(current_mod_project_dir, "CORE", "shared", "packed_data"),
            "extracted_atf_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "atf"),
            "extracted_dds_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "dds"),
            # Sound related folders
            "wav_sfx_work": os.path.join(current_mod_project_dir, "wav_sfx_work"), # Optional for user's raw wavs
            "wav_speech_work": os.path.join(current_mod_project_dir, "wav_speech_work"), # Optional
            "wav_music_work": os.path.join(current_mod_project_dir, "wav_music_work"), # Optional
            "prepared_sounds_sfx": os.path.join(current_mod_project_dir, "prepared_sounds", "sfx"),
            "prepared_sounds_speech": os.path.join(current_mod_project_dir, "prepared_sounds", "speech"),
            "prepared_sounds_music": os.path.join(current_mod_project_dir, "prepared_sounds", "music"),
        }
        
        created_any = False
        for key, p in paths_to_create.items():
            if not os.path.exists(p):
                try:
                    os.makedirs(p, exist_ok=True) # exist_ok=True is important
                    if not silent: log_message(self.log_area, f"Created folder: {p}")
                    created_any = True
                except Exception as e:
                    log_message(self.log_area, f"Error creating folder {p}: {e}")
                    if not silent: messagebox.showerror("Error", f"Could not create folder {p}: {e}")
                    return False # Stop if a critical folder fails
            
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
                # Not returning False here, as readme is less critical than folders

        if not created_any and not silent:
            log_message(self.log_area, "Mod project folders already seem to exist or no new ones needed.")
        elif created_any and not silent:
            log_message(self.log_area, "Mod project folder structure initialized/verified.")
        return True

    def extract_and_convert_game_textures(self):
        if not self._validate_paths(check_mod_project=True): return # Checks starter too
        if not self.initialize_mod_folders(silent=True): 
            log_message(self.log_area, "Failed to initialize mod project folders for extraction.")
            return

        selected_archives = [name for name, var in self.texture_archives_vars.items() if var.get()]
        if not selected_archives:
            messagebox.showinfo("No Selection", "No texture archives selected for extraction.")
            return

        log_message(self.log_area, f"Starting extraction for: {', '.join(selected_archives)}")
        self.extracted_texture_listbox.delete(0, tk.END)
        all_extracted_texture_names_for_file = [] 

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        
        final_extracted_atf_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_textures", "atf")
        final_extracted_dds_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_textures", "dds")
        # Folders are created by initialize_mod_folders

        current_game_root = self.game_root_var.get()

        for archive_name in selected_archives:
            # Path to archive within game's data structure
            archive_path_rel_to_game_root = os.path.join("data", "k43t", "shared", "packed_data", archive_name)
            # Some archives might be in loc_... folders too, but this covers most common texture archives.
            # A more robust solution would check multiple potential game data paths or allow user input for archive location.
            # For now, assume shared/packed_data for textures.
            archive_path_abs_in_game = os.path.join(current_game_root, archive_path_rel_to_game_root)
            
            if not os.path.exists(archive_path_abs_in_game):
                # Try alternative common path for localized textures like textures_loc.flatdata
                alt_archive_path_rel = os.path.join("data", "k43t", "loc_eng", "packed_data", archive_name) # Assuming English for now
                alt_archive_path_abs = os.path.join(current_game_root, alt_archive_path_rel)
                if os.path.exists(alt_archive_path_abs):
                    archive_path_rel_to_game_root = alt_archive_path_rel
                    archive_path_abs_in_game = alt_archive_path_abs
                else:
                    log_message(self.log_area, f"Warning: Archive '{archive_name}' not found in common game data paths. Skipping.")
                    continue

            log_message(self.log_area, f"Processing archive: {archive_path_rel_to_game_root}")
            archive_base_name = os.path.splitext(archive_name)[0] # e.g., "tex_main"

            # Define where starter.exe will unpack: relative to game root, inside users/modwork
            starter_unflat_output_rel = os.path.join("users", "modwork", f"_temp_unflat_{archive_base_name}_{timestamp}")
            # Absolute path to where starter.exe unpacks (within game's dir structure)
            starter_unflat_output_abs = os.path.join(current_game_root, starter_unflat_output_rel)
            os.makedirs(os.path.dirname(starter_unflat_output_abs), exist_ok=True)


            log_message(self.log_area, f"  Unpacking '{archive_path_rel_to_game_root}' to game's temp '{starter_unflat_output_rel}'...")
            # unflat command: unflat, <archive_path_relative_to_game_root>, <output_dir_relative_to_game_root>
            success, unflat_output_actual_abs = run_starter_command("unflat", [archive_path_rel_to_game_root, starter_unflat_output_rel], self.log_area, timeout=300)
            
            if not success or not (unflat_output_actual_abs and os.path.isdir(unflat_output_actual_abs)):
                log_message(self.log_area, f"  Failed to unpack '{archive_name}' or output dir '{unflat_output_actual_abs}' not found. Skipping.")
                if os.path.exists(starter_unflat_output_abs): shutil.rmtree(starter_unflat_output_abs) # Clean up temp
                continue
            
            log_message(self.log_area, f"  Successfully unpacked to '{unflat_output_actual_abs}'. Now converting .texture to .dds...")

            # Define final destination for .texture files (in Mod Project Dir)
            final_atf_archive_dir_in_project = os.path.join(final_extracted_atf_base_abs, archive_base_name)
            # Define final destination for .dds files (in Mod Project Dir)
            final_dds_archive_dir_in_project = os.path.join(final_extracted_dds_base_abs, archive_base_name)
            os.makedirs(final_atf_archive_dir_in_project, exist_ok=True)
            os.makedirs(final_dds_archive_dir_in_project, exist_ok=True)

            textures_in_archive_count = 0
            successfully_converted_atf_paths_in_project = []

            # Iterate over files unpacked by starter.exe (in starter_unflat_output_abs)
            for item in os.listdir(unflat_output_actual_abs):
                if item.lower().endswith(".texture"):
                    textures_in_archive_count += 1
                    # Path to the .texture file in the game's temporary unpack location
                    src_atf_in_game_temp_abs = os.path.join(unflat_output_actual_abs, item)
                    
                    # Path to copy the original .texture file to within the Mod Project (for backup/reference)
                    dest_atf_in_project_abs = os.path.join(final_atf_archive_dir_in_project, item)
                    try:
                        shutil.copy2(src_atf_in_game_temp_abs, dest_atf_in_project_abs)
                    except Exception as e:
                        log_message(self.log_area, f"    Error copying {item} to project ATF archive: {e}")
                        continue # Skip this file if copy fails

                    # Prepare for atf2dds conversion
                    dds_filename = item.replace(".texture", ".dds")
                    # Temporary location for the converted .dds file (within game's temp unpack dir)
                    temp_dds_output_in_game_temp_abs = os.path.join(unflat_output_actual_abs, dds_filename)
                    
                    # starter.exe needs paths relative to Game Root Directory
                    param_src_atf_rel = os.path.relpath(src_atf_in_game_temp_abs, current_game_root)
                    param_dest_dds_rel = os.path.relpath(temp_dds_output_in_game_temp_abs, current_game_root)

                    # atf2dds command: atf2dds, <source_atf_relative>, <dest_dds_relative>
                    conv_success, _ = run_starter_command("atf2dds", [param_src_atf_rel, param_dest_dds_rel], self.log_area)
                    
                    if conv_success and os.path.exists(temp_dds_output_in_game_temp_abs):
                        # Path to move the final .dds file to within the Mod Project
                        dest_dds_in_project_abs = os.path.join(final_dds_archive_dir_in_project, dds_filename)
                        try:
                            shutil.copy2(temp_dds_output_in_game_temp_abs, dest_dds_in_project_abs) # Use copy2 to preserve metadata
                            # Add to listbox: relative path within extracted_game_textures/dds/
                            listbox_entry = os.path.join(archive_base_name, dds_filename)
                            all_extracted_texture_names_for_file.append(listbox_entry)
                            self.extracted_texture_listbox.insert(tk.END, listbox_entry)
                            self.extracted_texture_listbox.see(tk.END)
                            successfully_converted_atf_paths_in_project.append(dest_atf_in_project_abs)
                        except Exception as e:
                            log_message(self.log_area, f"    Error copying converted DDS {dds_filename} to project: {e}")
                    else:
                        log_message(self.log_area, f"    Failed to convert {item} from {archive_name} or temp DDS not found at {temp_dds_output_in_game_temp_abs}.")
            
            # Optional: Delete original .texture files from the Mod Project's 'atf' backup dir
            if self.delete_atf_after_extraction_var.get() and successfully_converted_atf_paths_in_project:
                log_message(self.log_area, f"  Deleting original .texture files from {final_atf_archive_dir_in_project} for successfully converted files...")
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
                # Attempt to remove the ATF subfolder if it's now empty
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
            else:
                log_message(self.log_area, f"  Finished processing {textures_in_archive_count} textures from '{archive_name}'.")
            
            # Clean up the temporary unpack directory created by starter.exe
            if os.path.exists(starter_unflat_output_abs):
                try:
                    shutil.rmtree(starter_unflat_output_abs)
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove game temp unpack dir {starter_unflat_output_abs}: {e}")
            self.root.update_idletasks() # Keep UI responsive

        log_message(self.log_area, "Game texture extraction and conversion process finished.")
        if not all_extracted_texture_names_for_file:
            log_message(self.log_area, "No textures were successfully extracted and converted.")
        else:
            messagebox.showinfo("Extraction Complete", f"Extraction and conversion complete. Check the 'extracted_game_textures' folder in your Mod Project Directory and the list.")

    def save_extracted_texture_list(self):
        if self.extracted_texture_listbox.size() == 0:
            messagebox.showinfo("No List", "Texture list is empty. Extract some textures first.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Extracted Texture List As",
            initialdir=current_mod_project_dir or os.getcwd() # Default to mod project dir
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

    def convert_atf_to_dds_for_modding(self):
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for ATF to DDS conversion.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()

        # Suggest starting directory for file dialog
        suggested_atf_dir = os.path.join(current_mod_project_dir, "extracted_game_textures", "atf") 
        if not os.path.isdir(suggested_atf_dir): # Fallback if not extracted yet
            suggested_atf_dir = os.path.join(current_game_root, "data") 
        if not os.path.isdir(suggested_atf_dir): # Further fallback
            suggested_atf_dir = current_game_root

        source_atf_files_abs = filedialog.askopenfilenames(
            title="Select .texture (ATF) files to convert for modding",
            initialdir=suggested_atf_dir,
            filetypes=[("Texture files", "*.texture"), ("All files", "*.*")]
        )
        if not source_atf_files_abs: return

        output_dds_dir_abs = os.path.join(current_mod_project_dir, "dds_work")
        # Folder is created by initialize_mod_folders
        
        log_message(self.log_area, f"Starting ATF to DDS conversion for {len(source_atf_files_abs)} file(s)...")
        success_count = 0
        for atf_path_abs in source_atf_files_abs:
            filename = os.path.basename(atf_path_abs)
            base, _ = os.path.splitext(filename) 
            dds_filename = base + ".dds"
            
            # Temporary DDS output location (relative to game root for starter.exe)
            # Needs to be in a place starter.exe can write, typically users/modwork
            temp_dds_output_base_dir_rel = os.path.join("users", "modwork")
            temp_dds_output_rel = os.path.join(temp_dds_output_base_dir_rel, f"_temp_modding_{dds_filename}")
            temp_dds_output_abs = os.path.join(current_game_root, temp_dds_output_rel)
            os.makedirs(os.path.dirname(temp_dds_output_abs), exist_ok=True)


            # Final destination for the DDS file in the mod project
            final_dds_path_abs = os.path.join(output_dds_dir_abs, dds_filename)
            
            # starter.exe needs paths relative to Game Root Directory
            param_atf_path_rel = os.path.relpath(atf_path_abs, current_game_root)
            # param_dds_path_rel is already relative (temp_dds_output_rel)

            log_message(self.log_area, f"Converting: {param_atf_path_rel} -> temp {temp_dds_output_rel}")
            conv_success, _ = run_starter_command("atf2dds", [param_atf_path_rel, temp_dds_output_rel], self.log_area)
            
            if conv_success and os.path.exists(temp_dds_output_abs):
                try:
                    shutil.move(temp_dds_output_abs, final_dds_path_abs) # Move from temp to mod project
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_dds_path_abs}")
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted DDS {dds_filename} to {output_dds_dir_abs}: {e}")
                    if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs) # Clean up temp if move fails
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp DDS not found at {temp_dds_output_abs}.")
                if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs) # Clean up temp
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
            initialdir=source_dds_dir_abs, # Default to dds_work
            filetypes=[("DDS files", "*.dds"), ("All files", "*.*")]
        )
        if not source_dds_files_abs: return

        output_atf_dir_abs = os.path.join(current_mod_project_dir, "prepared_textures")
        # Folder is created by initialize_mod_folders

        log_message(self.log_area, f"Starting DDS to ATF conversion for {len(source_dds_files_abs)} file(s)...")
        success_count = 0
        for dds_path_abs in source_dds_files_abs:
            filename = os.path.basename(dds_path_abs)
            base, _ = os.path.splitext(filename)
            atf_filename = base + ".texture"
            
            # Temporary ATF output location (relative to game root for starter.exe)
            temp_atf_output_base_dir_rel = os.path.join("users", "modwork")
            temp_atf_output_rel = os.path.join(temp_atf_output_base_dir_rel, f"_temp_modding_{atf_filename}")
            temp_atf_output_abs = os.path.join(current_game_root, temp_atf_output_rel)
            os.makedirs(os.path.dirname(temp_atf_output_abs), exist_ok=True)


            # Final destination for the ATF file in the mod project
            final_atf_path_abs = os.path.join(output_atf_dir_abs, atf_filename)

            # starter.exe needs paths relative to Game Root Directory
            param_dds_path_rel = os.path.relpath(dds_path_abs, current_game_root)
            # param_atf_path_rel is already relative (temp_atf_output_rel)
            
            log_message(self.log_area, f"Converting: {param_dds_path_rel} -> temp {temp_atf_output_rel}")
            conv_success, _ = run_starter_command("dds2atf", [param_dds_path_rel, temp_atf_output_rel], self.log_area)
            
            if conv_success and os.path.exists(temp_atf_output_abs):
                try:
                    shutil.move(temp_atf_output_abs, final_atf_path_abs) # Move from temp to mod project
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_atf_path_abs}")
                    success_count +=1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted ATF {atf_filename} to {output_atf_dir_abs}: {e}")
                    if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp ATF not found at {temp_atf_output_abs}.")
                if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)

        log_message(self.log_area, f"DDS to ATF conversion finished. {success_count}/{len(source_dds_files_abs)} successful. Texture files in '{output_atf_dir_abs}'")
        self.load_prepared_assets() # Refresh list in packaging tab

    def convert_wav_to_aaf(self):
        if not self._validate_paths(check_mod_project=True): return # Validates starter.exe too
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for WAV to AAF conversion.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        sound_category = self.sound_type_var.get() # "SFX" or "Speech"

        output_subfolder = "sfx" if sound_category == "SFX" else "speech"
        final_output_dir_abs = os.path.join(current_mod_project_dir, "prepared_sounds", output_subfolder)
        # Folders are created by initialize_mod_folders

        # Suggest starting directory for file dialog (user's WAV work folder or project root)
        suggested_wav_dir = os.path.join(current_mod_project_dir, f"wav_{output_subfolder}_work")
        if not os.path.isdir(suggested_wav_dir):
            suggested_wav_dir = current_mod_project_dir

        source_wav_files_abs = filedialog.askopenfilenames(
            title=f"Select .wav files for {sound_category} to .aaf conversion",
            initialdir=suggested_wav_dir,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if not source_wav_files_abs: return

        log_message(self.log_area, f"Starting WAV to AAF ({sound_category}) conversion for {len(source_wav_files_abs)} file(s)...")
        success_count = 0
        for wav_path_abs in source_wav_files_abs:
            filename = os.path.basename(wav_path_abs)
            base, _ = os.path.splitext(filename)
            aaf_filename = base + ".aaf" # Output as .aaf

            # Temporary AAF output location (relative to game root for starter.exe)
            temp_aaf_output_base_dir_rel = os.path.join("users", "modwork")
            temp_aaf_output_rel = os.path.join(temp_aaf_output_base_dir_rel, f"_temp_sound_{aaf_filename}")
            temp_aaf_output_abs = os.path.join(current_game_root, temp_aaf_output_rel)
            os.makedirs(os.path.dirname(temp_aaf_output_abs), exist_ok=True)

            final_aaf_path_abs = os.path.join(final_output_dir_abs, aaf_filename)

            param_wav_path_rel = os.path.relpath(wav_path_abs, current_game_root)
            # param_aaf_path_rel is temp_aaf_output_rel

            log_message(self.log_area, f"Converting: {param_wav_path_rel} -> temp {temp_aaf_output_rel}")
            # starter.exe wav2aaf, <input.wav>, <output.aaf_or_sound_file>
            # PDF example output is .sound, but type is AAF. Let's assume .aaf is fine for starter.exe output name.
            conv_success, _ = run_starter_command("wav2aaf", [param_wav_path_rel, temp_aaf_output_rel], self.log_area)

            if conv_success and os.path.exists(temp_aaf_output_abs):
                try:
                    shutil.move(temp_aaf_output_abs, final_aaf_path_abs)
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_aaf_path_abs}")
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted AAF {aaf_filename} to {final_output_dir_abs}: {e}")
                    if os.path.exists(temp_aaf_output_abs): os.remove(temp_aaf_output_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp AAF not found at {temp_aaf_output_abs}.")
                if os.path.exists(temp_aaf_output_abs): os.remove(temp_aaf_output_abs)
        
        log_message(self.log_area, f"WAV to AAF ({sound_category}) conversion finished. {success_count}/{len(source_wav_files_abs)} successful. AAF files in '{final_output_dir_abs}'")
        self.load_prepared_assets()

    def convert_wav_to_xwma(self):
        if not self._validate_paths(check_mod_project=True, check_starter=False): # Starter not needed for xWMA
            return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for WAV to xWMA conversion.")
            return

        xwma_encoder = self._get_xwma_encoder_path()
        if not xwma_encoder:
            return # Error message already shown by _get_xwma_encoder_path

        current_mod_project_dir = self.mod_project_dir_var.get()
        final_output_dir_abs = os.path.join(current_mod_project_dir, "prepared_sounds", "music")
        # Folder is created by initialize_mod_folders

        suggested_wav_dir = os.path.join(current_mod_project_dir, "wav_music_work")
        if not os.path.isdir(suggested_wav_dir):
            suggested_wav_dir = current_mod_project_dir
            
        source_wav_files_abs = filedialog.askopenfilenames(
            title="Select .wav files for Music to .xWMA conversion",
            initialdir=suggested_wav_dir,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if not source_wav_files_abs: return

        log_message(self.log_area, f"Starting WAV to xWMA (Music) conversion for {len(source_wav_files_abs)} file(s)...")
        success_count = 0
        for wav_path_abs in source_wav_files_abs:
            filename = os.path.basename(wav_path_abs)
            base, _ = os.path.splitext(filename)
            xwma_filename = base + ".xWMA" # Explicitly .xWMA extension
            final_xwma_path_abs = os.path.join(final_output_dir_abs, xwma_filename)

            # Command: xWMAEncode.exe <input.wav> <output.xWMA> -b <bitrate>
            # PDF example bitrate is 160000
            command = [xwma_encoder, wav_path_abs, final_xwma_path_abs, "-b", "160000"]
            log_message(self.log_area, f"Running: {' '.join(command)}")

            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                stdout, stderr = process.communicate(timeout=120)
                
                if stdout: log_message(self.log_area, f"xWMAEncode Output:\n{stdout}")
                if stderr: log_message(self.log_area, f"xWMAEncode Errors:\n{stderr}")

                if process.returncode == 0 and os.path.exists(final_xwma_path_abs):
                    log_message(self.log_area, f"  Successfully converted to: {final_xwma_path_abs}")
                    success_count += 1
                else:
                    log_message(self.log_area, f"  Failed to convert {filename}. Return code: {process.returncode}. Check xWMAEncode output.")
                    if os.path.exists(final_xwma_path_abs): # Remove partially created file if any
                        try: os.remove(final_xwma_path_abs)
                        except: pass
            except subprocess.TimeoutExpired:
                log_message(self.log_area, f"Error: xWMAEncode command timed out for {filename}.")
                if process: process.kill()
            except Exception as e:
                log_message(self.log_area, f"Error running xWMAEncode for {filename}: {e}")

        log_message(self.log_area, f"WAV to xWMA (Music) conversion finished. {success_count}/{len(source_wav_files_abs)} successful. xWMA files in '{final_output_dir_abs}'")
        self.load_prepared_assets()


    def load_prepared_assets(self):
        self.packaged_assets_listbox.delete(0, tk.END)
        current_mod_project_dir = self.mod_project_dir_var.get()
        if not current_mod_project_dir:
            log_message(self.log_area, "Mod Project Directory not set. Cannot load assets.")
            return

        total_found = 0
        # self.asset_types_to_scan is now populated from self.flatdata_definitions
        for asset_type_info in self.asset_types_to_scan:
            asset_dir = os.path.join(current_mod_project_dir, asset_type_info["folder"])
            if os.path.isdir(asset_dir):
                count_this_type = 0
                for item in sorted(os.listdir(asset_dir)):
                    if item.lower().endswith(asset_type_info["ext"]):
                        self.packaged_assets_listbox.insert(tk.END, f"{asset_type_info['prefix']} {item}")
                        count_this_type += 1
                        total_found +=1
                if count_this_type > 0:
                    log_message(self.log_area, f"Found {count_this_type} {asset_type_info['ext']} files in '{asset_type_info['folder']}'.")
        
        if total_found == 0:
            log_message(self.log_area, "No prepared asset files found in expected 'prepared_...' subfolders.")
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
        encodings_to_try = ['utf-8-sig', 'utf-8', 'windows-1251', 'latin-1'] # Added more encodings
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

        # Use regex for safer replacements, especially for version
        desc_engcfg2_content = desc_engcfg2_content.replace("<my_updates>", installer_mod_path)
        desc_engcfg2_content = desc_engcfg2_content.replace("<My Addon>", mod_name) 
        desc_engcfg2_content = desc_engcfg2_content.replace("<Vasya Pupkin>", author)
        desc_engcfg2_content = re.sub(r"version\[u\]\s*=\s*\d+", f"version[u] = {version}", desc_engcfg2_content)
        # Ensure type is RES if not already something else specific
        if "type[*]=" not in desc_engcfg2_content:
             desc_engcfg2_content += "\ntype[*]= RES;\n" # Add if missing
        elif "type[*] = ADDN" in desc_engcfg2_content or "type[*] = CAMP" in desc_engcfg2_content:
            pass # Keep existing valid type
        else: # Default to RES if type exists but is not ADDN or CAMP
            desc_engcfg2_content = re.sub(r"type\[\*\]\s*=\s*\w+;", "type[*]= RES;", desc_engcfg2_content)


        temp_desc_engcfg2_name = "_temp_desc.addpack.engcfg2"
        # Place temp file in users/modwork relative to game root
        temp_desc_engcfg2_path_rel = os.path.join("users", "modwork", temp_desc_engcfg2_name)
        temp_desc_engcfg2_path_abs = os.path.join(game_root_dir, temp_desc_engcfg2_path_rel)
        os.makedirs(os.path.dirname(temp_desc_engcfg2_path_abs), exist_ok=True)


        try:
            with open(temp_desc_engcfg2_path_abs, "w", encoding='utf-8') as f: # Save temp as UTF-8
                f.write(desc_engcfg2_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing temporary desc file '{temp_desc_engcfg2_path_abs}': {e}")
            return False
        
        final_desc_addpack_path_abs = os.path.join(core_dir_abs, "desc.addpack")
        # Output of pd2cfgp, also relative to game root in users/modwork
        temp_desc_addpack_output_name = "_temp_desc.addpack"
        temp_desc_addpack_output_rel = os.path.join("users", "modwork", temp_desc_addpack_output_name)
        temp_desc_addpack_output_abs = os.path.join(game_root_dir, temp_desc_addpack_output_rel)


        log_message(self.log_area, "Generating desc.addpack...")
        # pd2cfgp command: pd2cfgp, <input_engcfg2_relative>, <output_addpack_relative>
        gen_success, _ = run_starter_command("pd2cfgp", [temp_desc_engcfg2_path_rel, temp_desc_addpack_output_rel], self.log_area)
        
        if os.path.exists(temp_desc_engcfg2_path_abs):
            try: os.remove(temp_desc_engcfg2_path_abs)
            except: pass # Non-critical if temp removal fails

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
                               files_to_package, # List of (abs_src_path_in_project, staging_filename)
                               game_root_dir, core_dir_abs):
        """
        Packages a list of asset files into a single .flatdata archive.
        files_to_package: A list of tuples, where each tuple is 
                          (absolute_path_to_source_asset_in_mod_project, filename_for_staging_and_flatlist_entry_base).
                          Example: [("C:/ModProj/prepared_sounds/sfx/boom.aaf", "boom.aaf")]
        """
        if not files_to_package:
            log_message(self.log_area, f"No files provided for packaging into {flatlist_name_stem}.flatdata. Skipping.")
            return True # No error, just nothing to do

        log_message(self.log_area, f"Packaging {len(files_to_package)} assets into {flatlist_name_stem}.flatdata...")

        # Temporary staging directory for mkflat, relative to game_root_dir/users/modwork
        mkflat_staging_dir_name = f"_mkflat_stage_{flatlist_name_stem}_{time.strftime('%Y%m%d%H%M%S')}"
        # Staging dir must be under users/modwork for starter.exe relative paths
        mkflat_staging_dir_rel = os.path.join("users", "modwork", mkflat_staging_dir_name)
        mkflat_staging_dir_abs = os.path.join(game_root_dir, mkflat_staging_dir_rel)
        os.makedirs(mkflat_staging_dir_abs, exist_ok=True)

        flatlist_content = "i_unflat:unflat()\n{\n"

        for abs_src_path_in_project, staging_filename in files_to_package:
            # staging_filename is the simple filename, e.g., "boom.aaf", "my_texture.texture"
            # The flatlist entry name is typically the filename without extension, and without .loc_def if present.
            flatlist_entry_name = os.path.splitext(staging_filename)[0] # "boom", "my_texture"
            if flatlist_entry_name.lower().endswith(".loc_def"):
                flatlist_entry_name = flatlist_entry_name[:-len(".loc_def")]
            
            # All user-provided assets are typically loc_def
            flatlist_content += f"    {flatlist_entry_name}\t, {mkflat_file_type}\t, loc_def ;\n"
            
            # Copy the source asset from Mod Project to the mkflat staging directory (in game_root/users/modwork/...)
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
                # Decide if this should be a fatal error for the archive
                # For now, let it continue, but the flatlist will reference a non-existent file in staging.
                # It's better to return False if a listed file is missing.
                if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
                return False


        flatlist_content += "}\n"
        
        # Path for .!flatlist file within the staging directory (relative to game_root)
        flatlist_filename_for_mkflat = f"{flatlist_name_stem}.!flatlist" 
        flatlist_path_in_staging_abs = os.path.join(mkflat_staging_dir_abs, flatlist_filename_for_mkflat)
        flatlist_path_in_staging_rel = os.path.relpath(flatlist_path_in_staging_abs, game_root_dir) # Relative to game_root

        try:
            with open(flatlist_path_in_staging_abs, "w", encoding='utf-8') as f:
                f.write(flatlist_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing {flatlist_filename_for_mkflat} to staging: {e}")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return False

        # Output .flatdata file path within the staging directory (relative to game_root)
        flatdata_output_in_staging_rel = os.path.join(mkflat_staging_dir_rel, f"{flatlist_name_stem}.flatdata")
        flatdata_output_in_staging_abs = os.path.join(game_root_dir, flatdata_output_in_staging_rel)
        
        # The final destination of the .flatdata file is within the mod's CORE structure in the Mod Project Dir
        final_flatdata_target_in_project_abs = os.path.join(core_dir_abs, "shared", "packed_data", f"{flatlist_name_stem}.flatdata")
        
        # mkflat command: mkflat, <output_flatdata_relative_to_game_root>, <input_flatlist_relative_to_game_root>
        # The input_flatlist path for mkflat should be relative to where mkflat is looking for the asset files,
        # which is the staging directory itself. So, just the filename of the flatlist.
        # However, starter.exe commands usually take paths relative to GAME_ROOT_DIR.
        # The PDF example: mkflat, users\modwork\my_addon.flatdata, users\modwork\my_addon.!flatlist
        # This implies both paths are relative to game root.
        # The files listed in my_addon.!flatlist are then expected to be in users\modwork\my_addon\ (a folder with same name as flatlist).
        # This means the mkflat_staging_dir_abs (e.g., game_root/users/modwork/_mkflat_stage_textures_xxxx/) is where the assets AND the flatlist file should be.
        # And the paths in the mkflat command are relative to game_root.

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
        if not self.initialize_mod_folders(silent=True): # Ensures CORE and subfolders exist
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
        # CORE/shared/packed_data is created by initialize_mod_folders

        if not self._generate_desc_addpack_file(mod_name_val, mod_author_val, mod_version_val, core_dir_abs, current_game_root):
            messagebox.showerror("Error", "Failed to generate desc.addpack. Check log.")
            return

        all_archives_successful = True
        archives_packaged_count = 0

        # Iterate through the defined flatdata types (textures, sounds, music)
        for flatlist_stem, definition in self.flatdata_definitions.items():
            mkflat_type = definition["mkflat_type"]
            # Collect files for *this specific* flatdata archive from the user's selection
            files_for_this_flatdata_archive = [] # List of (abs_src_path_in_project, staging_filename)

            for source_config in definition["sources"]:
                # e.g., source_config = {"prefix": "[SFX]", "folder": "prepared_sounds/sfx", "ext": ".aaf"}
                prefix_to_match = source_config["prefix"] + " " # e.g., "[SFX] "
                # Absolute path to the folder in Mod Project where these source assets are located
                source_folder_abs_in_project = os.path.join(current_mod_project_dir, source_config["folder"])
                
                for selected_file_with_prefix in selected_asset_filenames_with_prefix:
                    # selected_file_with_prefix is like "[SFX] boom.aaf"
                    if selected_file_with_prefix.startswith(prefix_to_match):
                        # asset_filename is the simple name, e.g., "boom.aaf"
                        asset_filename = selected_file_with_prefix.replace(prefix_to_match, "")
                        # Full path to the original asset in the "prepared_..." folder
                        original_asset_path_abs_in_project = os.path.join(source_folder_abs_in_project, asset_filename)
                        
                        files_for_this_flatdata_archive.append(
                            (original_asset_path_abs_in_project, asset_filename)
                        )
            
            if files_for_this_flatdata_archive: # Only proceed if there are files for this archive type
                success = self._package_asset_archive( # Call the refactored packaging function
                    flatlist_name_stem=flatlist_stem, # e.g., "sounds"
                    mkflat_file_type=mkflat_type,     # e.g., "sound"
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
             log_message(self.log_area, "No asset archives were generated. Ensure selected files match defined types (e.g., [TEX], [SFX], [MUS]) and their 'prepared_...' folders exist.")
             messagebox.showwarning("Packaging Skipped", "No asset archives were generated. Check prefixes and file locations of selected items.")
             return # Return because no archives were made, even if desc.addpack was.

        if all_archives_successful and archives_packaged_count > 0:
            log_message(self.log_area, "All selected mod files generated successfully in CORE directory.")
            messagebox.showinfo("Success", "Mod files (desc.addpack and selected .flatdata archives) generated successfully!")
        elif archives_packaged_count > 0 : 
            log_message(self.log_area, "Some mod files generated, but errors occurred with others. Check log.")
            messagebox.showwarning("Partial Success", "Some mod files generated, but errors occurred. Check log.")
        elif archives_packaged_count == 0 and not any(selected_asset_filenames_with_prefix) : # No files were selected initially
            log_message(self.log_area, "desc.addpack generated, but no assets were selected for packaging.")
            messagebox.showinfo("desc.addpack Generated", "desc.addpack generated. No assets were selected to package into .flatdata archives.")
        else: # Failed to generate any archives, though desc.addpack might have succeeded.
            log_message(self.log_area, "Failed to generate mod asset files. desc.addpack might have been created. Check log.")
            messagebox.showerror("Error", "Failed to generate mod asset files. Check log for details.")


    def create_mod_archive(self):
        if not self._validate_paths(check_mod_project=True, check_starter=False): return # Starter not needed for zipping
        
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
                # Continue even if readme creation fails, it's not critical for the archive itself.

        # Suggest save location (one level up from mod project dir, or mod project dir itself)
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
        
        # Ensure it ends with .gt2extension, even if user selected .zip then typed a name without it
        if not archive_save_path.lower().endswith(".gt2extension"):
            archive_save_path = os.path.splitext(archive_save_path)[0] + ".gt2extension"

        # shutil.make_archive creates archive_basename_for_shutil + ".zip"
        # So, if archive_save_path is "C:/path/to/MyMod.gt2extension",
        # archive_basename_for_shutil should be "C:/path/to/MyMod" (if we want MyMod.zip then rename)
        # Or, better: archive_basename_for_shutil is "C:/path/to/MyMod.gt2extension_temp"
        # then move "MyMod.gt2extension_temp.zip" to "MyMod.gt2extension"
        
        # Let's make the zip with a temp name, then rename to the final .gt2extension path
        temp_zip_base_name = os.path.splitext(archive_save_path)[0] + "_temp_zip_for_gt2ext"


        staging_dir = None # For collecting files to be zipped
        try:
            # Create a temporary staging directory inside the mod project dir
            staging_dir = os.path.join(current_mod_project_dir, "_archive_staging_temp")
            if os.path.exists(staging_dir): shutil.rmtree(staging_dir) # Clear if exists
            os.makedirs(staging_dir)

            # Copy CORE folder and readme.txt into the staging directory
            shutil.copytree(core_dir_to_archive, os.path.join(staging_dir, "CORE"))
            if os.path.exists(readme_file_to_archive): # readme might not exist if creation failed
                shutil.copy2(readme_file_to_archive, os.path.join(staging_dir, "readme.txt"))

            # Create the zip archive from the contents of the staging directory
            # make_archive(base_name, format, root_dir=None, base_dir=None, ...)
            # base_name: name of the file to create, including path, minus extension.
            # root_dir: directory to cd into before archiving. Files are archived relative to this.
            # base_dir: directory within root_dir to archive. If None, archives everything in root_dir.
            shutil.make_archive(base_name=temp_zip_base_name, 
                                format='zip', 
                                root_dir=staging_dir) # Archive contents of staging_dir
            
            created_zip_file = temp_zip_base_name + ".zip" # Full path to the created zip

            # Move the created .zip file to the desired final .gt2extension path
            if os.path.exists(archive_save_path): # Remove if final path already exists (e.g. user overwriting)
                os.remove(archive_save_path)
            shutil.move(created_zip_file, archive_save_path)

            log_message(self.log_area, f"Mod archive created: {archive_save_path}")
            messagebox.showinfo("Success", f"Mod archive (.gt2extension) created: {archive_save_path}")

        except Exception as e:
            log_message(self.log_area, f"Error creating mod archive: {e}")
            messagebox.showerror("Error", f"Error creating mod archive: {e}")
        finally:
            # Clean up temporary staging directory and any intermediate zip file
            if staging_dir and os.path.exists(staging_dir):
                try:
                    shutil.rmtree(staging_dir)
                except Exception as e_rm:
                    log_message(self.log_area, f"Warning: Could not remove staging directory {staging_dir}: {e_rm}")
            if 'created_zip_file' in locals() and os.path.exists(created_zip_file) and created_zip_file != archive_save_path :
                try:
                    os.remove(created_zip_file) # If move failed or it's a different temp name
                except Exception as e_rm_zip:
                    log_message(self.log_area, f"Warning: Could not remove temporary zip file {created_zip_file}: {e_rm_zip}")


app = None
if __name__ == "__main__":
    root = tk.Tk()
    app = TextureModTool(root)
    root.mainloop()
