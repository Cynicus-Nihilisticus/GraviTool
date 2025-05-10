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
        "ModProjectDir": MOD_PROJECT_DIR
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
        params_str = ','.join(map(str, [p if p is not None else "" for p in params_list]))
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
        self.root.title("Graviteam Asset Mod Tool (GTOS)")
        self.root.geometry("950x850")

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
        # self.create_sound_modding_tab(sound_modding_tab) # Placeholder

        packaging_tab = ttk.Frame(self.notebook)
        self.notebook.add(packaging_tab, text='5. Asset Packaging')
        self.create_packaging_tab(packaging_tab)
        
        if hasattr(self, 'game_root_var'): self.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(self, 'mod_project_dir_var'): self.mod_project_dir_var.set(MOD_PROJECT_DIR)
        
        if GAME_ROOT_DIR: update_starter_exe_path()
        log_message(self.log_area, "Tool initialized. Set Game Root and Mod Project directories if not already configured.")

    def create_setup_tab(self, tab):
        # ... (same as before, with ToolTips) ...
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
        
        frame.grid_columnconfigure(1, weight=1)

        info_frame = ttk.LabelFrame(frame, text="Mod Information (for desc.addpack & readme.txt)", padding="10")
        info_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")

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
        init_folders_button.grid(row=3, column=0, columnspan=3, pady=10)
        ToolTip(init_folders_button, 
                "Creates standard subfolders for textures, sounds, etc.,\n"
                "within your Mod Project Directory and a template readme.txt if they don't exist.")

    def create_extractor_tab(self, tab):
        # ... (same as before, with ToolTips) ...
        frame = ttk.Frame(tab, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="This tool will unpack game texture archives (.flatdata) to your Mod Project Directory, \nconvert them to .dds, and generate a list of available textures.").pack(pady=(0,5))
        
        archive_frame = ttk.LabelFrame(frame, text="Select Game Texture Archives to Extract", padding="10")
        archive_frame.pack(fill=tk.X, pady=5)

        self.texture_archives_vars = {}
        known_texture_archives = [ 
            "tex_main.flatdata", "tex_main_01.flatdata", "tex_misc.flatdata", "tex_objects.flatdata",
        ]
        for i, archive_name in enumerate(known_texture_archives):
            var = tk.BooleanVar(value=True if i < 2 else False) 
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
        list_scroll = ttk.Scrollbar(listbox_container_frame, orient=tk.VERTICAL, command=self.extracted_texture_listbox.yview)
        self.extracted_texture_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.extracted_texture_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        save_list_button = ttk.Button(frame, text="Save List to File", command=self.save_extracted_texture_list)
        save_list_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(save_list_button, "Saves the list of extracted .dds texture paths (shown above) to a text file.")

    def create_conversion_tab(self, tab):
        # ... (same as before, with ToolTips) ...
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

    def create_packaging_tab(self, tab):
        # ... (same as before, with ToolTips and renamed elements) ...
        frame = ttk.Frame(tab, padding="10")
        frame.pack(expand=True, fill='both')

        list_frame = ttk.LabelFrame(frame, text="Select asset files from 'prepared_...' folders to include in mod", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.packaged_assets_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10, relief=tk.SUNKEN, borderwidth=1)
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.packaged_assets_listbox.yview)
        self.packaged_assets_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.packaged_assets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        refresh_button = ttk.Button(frame, text="Refresh List from 'prepared_...' folders", command=self.load_prepared_assets)
        refresh_button.pack(pady=(5,10), fill=tk.X, padx=20)
        ToolTip(refresh_button, "Updates the list above with recognized asset files currently in\n'ModProjectDir/prepared_textures/' and 'ModProjectDir/prepared_sounds/...'.")
        
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        generate_files_button = ttk.Button(frame, text="1. Generate Mod Files (desc.addpack & .flatdata archives)", command=self.generate_mod_files)
        generate_files_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(generate_files_button,
                "For selected assets:\n"
                "- Creates 'desc.addpack' in 'CORE/'.\n"
                "- Creates appropriate '.!flatlist' files in a temporary staging area.\n"
                "- Copies selected asset files to the staging area.\n"
                "- Creates '.flatdata' archives (e.g., textures.flatdata, sounds.flatdata)\n  using 'mkflat' and places them in 'CORE/shared/packed_data/'.\n"
                "- Cleans up temporary staging files.")

        create_archive_button = ttk.Button(frame, text="2. Create .gt2extension Mod Archive", command=self.create_mod_archive)
        create_archive_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(create_archive_button,
                "Packages the 'CORE/' folder and 'readme.txt' from your Mod Project Directory\n"
                "into a distributable .gt2extension archive file (a renamed .zip).")

    def _validate_paths(self, check_mod_project=True):
        # ... (same as before) ...
        global GAME_ROOT_DIR, MOD_PROJECT_DIR, STARTER_EXE_PATH
        GAME_ROOT_DIR = self.game_root_var.get()
        MOD_PROJECT_DIR = self.mod_project_dir_var.get()

        if not GAME_ROOT_DIR or not os.path.isdir(GAME_ROOT_DIR):
            log_message(self.log_area, "Error: Game Root Directory is not set or invalid.")
            messagebox.showerror("Error", "Game Root Directory is not set or invalid.")
            return False
        
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
        # ... (same as before) ...
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
        # ... (same as before) ...
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
        # ... (same as before, with new sound folders) ...
        if not self._validate_paths(check_mod_project=True): return False
        current_mod_project_dir = self.mod_project_dir_var.get()
        if not current_mod_project_dir:
            if not silent: log_message(self.log_area, "Mod project directory not set, cannot initialize folders.")
            return False

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
            "CORE_shared_packed_data": os.path.join(current_mod_project_dir, "CORE", "shared", "packed_data"), # This is for final mod structure
            "extracted_atf_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "atf"),
            "extracted_dds_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "dds"),
            "wav_sfx_work": os.path.join(current_mod_project_dir, "wav_sfx_work"),
            "wav_speech_work": os.path.join(current_mod_project_dir, "wav_speech_work"),
            "wav_music_work": os.path.join(current_mod_project_dir, "wav_music_work"),
            "prepared_sounds_sfx": os.path.join(current_mod_project_dir, "prepared_sounds", "sfx"),
            "prepared_sounds_speech": os.path.join(current_mod_project_dir, "prepared_sounds", "speech"),
            "prepared_sounds_music": os.path.join(current_mod_project_dir, "prepared_sounds", "music"),
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
        # ... (same as before) ...
        if not self._validate_paths(check_mod_project=True): return
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
        os.makedirs(final_extracted_atf_base_abs, exist_ok=True)
        os.makedirs(final_extracted_dds_base_abs, exist_ok=True)

        current_game_root = self.game_root_var.get()

        for archive_name in selected_archives:
            archive_path_rel_to_game_root = os.path.join("data", "k43t", "shared", "packed_data", archive_name)
            archive_path_abs_in_game = os.path.join(current_game_root, archive_path_rel_to_game_root)
            
            if not os.path.exists(archive_path_abs_in_game):
                log_message(self.log_area, f"Warning: Archive '{archive_path_rel_to_game_root}' not found in game data. Skipping.")
                continue

            log_message(self.log_area, f"Processing archive: {archive_path_rel_to_game_root}")
            archive_base_name = os.path.splitext(archive_name)[0]

            starter_unflat_output_rel = os.path.join("users", "modwork", f"_temp_unflat_{archive_base_name}_{timestamp}")
            starter_unflat_output_abs = os.path.join(current_game_root, starter_unflat_output_rel)
            # Ensure parent of starter_unflat_output_abs exists if starter.exe doesn't create it
            os.makedirs(os.path.dirname(starter_unflat_output_abs), exist_ok=True)


            log_message(self.log_area, f"  Unpacking '{archive_path_rel_to_game_root}' to game's temp '{starter_unflat_output_rel}'...")
            success, unflat_output_actual_abs = run_starter_command("unflat", [archive_path_rel_to_game_root, starter_unflat_output_rel], self.log_area, timeout=300)
            
            if not success or not (unflat_output_actual_abs and os.path.isdir(unflat_output_actual_abs)):
                log_message(self.log_area, f"  Failed to unpack '{archive_name}' or output dir '{unflat_output_actual_abs}' not found. Skipping.")
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
                        log_message(self.log_area, f"    Failed to convert {item} from {archive_name} or temp DDS not found.")
            
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
            messagebox.showinfo("Extraction Complete", f"Extraction and conversion complete. Check the 'extracted_game_textures' folder in your Mod Project Directory and the list.")

    def save_extracted_texture_list(self):
        # ... (same as before) ...
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

    def convert_atf_to_dds_for_modding(self):
        # ... (same as before) ...
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
            
            temp_dds_output_base_dir = os.path.join(current_game_root, "users", "modwork")
            os.makedirs(temp_dds_output_base_dir, exist_ok=True) # Ensure users/modwork exists
            temp_dds_output_abs = os.path.join(temp_dds_output_base_dir, f"_temp_{dds_filename}")


            final_dds_path_abs = os.path.join(output_dds_dir_abs, dds_filename)
            
            param_atf_path_rel = os.path.relpath(atf_path_abs, current_game_root)
            param_dds_path_rel = os.path.relpath(temp_dds_output_abs, current_game_root)

            log_message(self.log_area, f"Converting: {param_atf_path_rel} -> temp {param_dds_path_rel}")
            conv_success, _ = run_starter_command("atf2dds", [param_atf_path_rel, param_dds_path_rel], self.log_area)
            
            if conv_success and os.path.exists(temp_dds_output_abs):
                try:
                    shutil.move(temp_dds_output_abs, final_dds_path_abs) 
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"Error moving converted DDS {dds_filename} to {output_dds_dir_abs}: {e}")
                    if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs) 
            else:
                log_message(self.log_area, f"Failed to convert {filename} or temp DDS not found.")
                if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs)
        log_message(self.log_area, f"ATF to DDS conversion finished. {success_count}/{len(source_atf_files_abs)} successful. DDS files in '{output_dds_dir_abs}'")

    def convert_dds_to_atf_for_modding(self):
        # ... (same as before) ...
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
            
            temp_atf_output_base_dir = os.path.join(current_game_root, "users", "modwork")
            os.makedirs(temp_atf_output_base_dir, exist_ok=True)
            temp_atf_output_abs = os.path.join(temp_atf_output_base_dir, f"_temp_{atf_filename}")

            final_atf_path_abs = os.path.join(output_atf_dir_abs, atf_filename)

            param_dds_path_rel = os.path.relpath(dds_path_abs, current_game_root)
            param_atf_path_rel = os.path.relpath(temp_atf_output_abs, current_game_root)
            
            log_message(self.log_area, f"Converting: {param_dds_path_rel} -> temp {param_atf_path_rel}")
            conv_success, _ = run_starter_command("dds2atf", [param_dds_path_rel, param_atf_path_rel], self.log_area)
            
            if conv_success and os.path.exists(temp_atf_output_abs):
                try:
                    shutil.move(temp_atf_output_abs, final_atf_path_abs)
                    success_count +=1
                except Exception as e:
                    log_message(self.log_area, f"Error moving converted ATF {atf_filename} to {output_atf_dir_abs}: {e}")
                    if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)
            else:
                log_message(self.log_area, f"Failed to convert {filename} or temp ATF not found.")
                if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)

        log_message(self.log_area, f"DDS to ATF conversion finished. {success_count}/{len(source_dds_files_abs)} successful. Texture files in '{output_atf_dir_abs}'")
        self.load_prepared_assets()

    def load_prepared_assets(self):
        # ... (same as before) ...
        self.packaged_assets_listbox.delete(0, tk.END)
        current_mod_project_dir = self.mod_project_dir_var.get()
        if not current_mod_project_dir:
            log_message(self.log_area, "Mod Project Directory not set. Cannot load assets.")
            return

        asset_types_to_scan = [
            {"prefix": "[TEX]", "folder": "prepared_textures", "ext": ".texture"},
            {"prefix": "[SFX]", "folder": os.path.join("prepared_sounds", "sfx"), "ext": ".aaf"},
            {"prefix": "[SPE]", "folder": os.path.join("prepared_sounds", "speech"), "ext": ".aaf"},
            {"prefix": "[MUS]", "folder": os.path.join("prepared_sounds", "music"), "ext": ".xWMA"},
        ]
        
        total_found = 0
        for asset_type in asset_types_to_scan:
            asset_dir = os.path.join(current_mod_project_dir, asset_type["folder"])
            if os.path.isdir(asset_dir):
                count_this_type = 0
                for item in sorted(os.listdir(asset_dir)):
                    if item.lower().endswith(asset_type["ext"]):
                        self.packaged_assets_listbox.insert(tk.END, f"{asset_type['prefix']} {item}")
                        count_this_type += 1
                        total_found +=1
                if count_this_type > 0:
                    log_message(self.log_area, f"Found {count_this_type} {asset_type['ext']} files in '{asset_type['folder']}'.")
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
            return False

        desc_engcfg2_content = None
        encodings_to_try = ['utf-8-sig', 'utf-8', 'windows-1251']
        for enc in encodings_to_try:
            try:
                with open(template_path_abs, "r", encoding=enc) as f:
                    desc_engcfg2_content = f.read()
                log_message(self.log_area, f"Successfully read template '{template_filename}' with {enc} encoding.")
                break
            except Exception:
                log_message(self.log_area, f"Warning: Failed to decode template '{template_filename}' with {enc}.")
        
        if desc_engcfg2_content is None:
            log_message(self.log_area, f"Critical Error: Could not read/decode template file '{template_filename}'.")
            return False

        # Sanitize mod_name for use in a path
        # Replace characters not suitable for folder names with an underscore
        # Allow alphanumeric, space, underscore, hyphen. Remove leading/trailing whitespace.
        sanitized_mod_name = re.sub(r'[^\w\s_-]', '_', mod_name).strip()
        if not sanitized_mod_name: sanitized_mod_name = "MyMod" # Fallback
        sanitized_mod_name = re.sub(r'\s+', '_', sanitized_mod_name) # Replace spaces with underscores for path

        # This path is for the installer, relative to data/k43t/
        installer_mod_path = f"mods/{sanitized_mod_name}" 
        log_message(self.log_area, f"Setting installer path in desc.addpack to: {installer_mod_path}")

        desc_engcfg2_content = desc_engcfg2_content.replace("<my_updates>", installer_mod_path)
        desc_engcfg2_content = desc_engcfg2_content.replace("<My Addon>", mod_name) # Display name
        desc_engcfg2_content = desc_engcfg2_content.replace("<Vasya Pupkin>", author)
        desc_engcfg2_content = desc_engcfg2_content.replace("version[u] = 100", f"version[u] = {version}")
        desc_engcfg2_content = desc_engcfg2_content.replace("type[*]= RES", "type[*]= RES")

        temp_desc_engcfg2_name = "_temp_desc.addpack.engcfg2"
        temp_desc_engcfg2_path_in_game_temp_abs = os.path.join(game_root_dir, "users", "modwork", temp_desc_engcfg2_name)
        os.makedirs(os.path.dirname(temp_desc_engcfg2_path_in_game_temp_abs), exist_ok=True)

        try:
            with open(temp_desc_engcfg2_path_in_game_temp_abs, "w", encoding='utf-8') as f:
                f.write(desc_engcfg2_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing temporary desc file: {e}")
            return False
        
        final_desc_addpack_path_abs = os.path.join(core_dir_abs, "desc.addpack")
        temp_desc_addpack_output_name = "_temp_desc.addpack"
        temp_desc_addpack_output_abs = os.path.join(game_root_dir, "users", "modwork", temp_desc_addpack_output_name)

        param_temp_engcfg2_rel = os.path.relpath(temp_desc_engcfg2_path_in_game_temp_abs, game_root_dir)
        param_temp_addpack_rel = os.path.relpath(temp_desc_addpack_output_abs, game_root_dir)

        log_message(self.log_area, "Generating desc.addpack...")
        gen_success, _ = run_starter_command("pd2cfgp", [param_temp_engcfg2_rel, param_temp_addpack_rel], self.log_area)
        
        if os.path.exists(temp_desc_engcfg2_path_in_game_temp_abs):
            try: os.remove(temp_desc_engcfg2_path_in_game_temp_abs)
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

    def _package_asset_archive(self, asset_type_label, source_subfolder_rel, asset_extension, 
                               flatlist_name_stem, mkflat_file_type, 
                               selected_asset_filenames_with_prefix, mod_project_dir, game_root_dir, core_dir_abs):
        # ... (same as before) ...
        prefix_to_match = f"[{asset_type_label.upper()[:3]}] "
        assets_to_package_this_type = [
            filename_with_prefix.replace(prefix_to_match, "") 
            for filename_with_prefix in selected_asset_filenames_with_prefix 
            if filename_with_prefix.startswith(prefix_to_match)
        ]

        if not assets_to_package_this_type:
            log_message(self.log_area, f"No {asset_type_label} selected for packaging. Skipping {flatlist_name_stem}.flatdata.")
            return True 

        log_message(self.log_area, f"Packaging {len(assets_to_package_this_type)} {asset_type_label} into {flatlist_name_stem}.flatdata...")

        mkflat_staging_dir_name = f"_mkflat_stage_{flatlist_name_stem}_{time.strftime('%Y%m%d%H%M%S')}"
        mkflat_staging_dir_abs = os.path.join(game_root_dir, "users", "modwork", mkflat_staging_dir_name)
        os.makedirs(mkflat_staging_dir_abs, exist_ok=True)

        flatlist_content = "i_unflat:unflat()\n{\n"
        source_asset_dir_abs = os.path.join(mod_project_dir, source_subfolder_rel)

        for asset_file_name in assets_to_package_this_type:
            base_name = asset_file_name
            suffixes_to_remove = [".loc_def" + asset_extension, asset_extension]
            for suffix in suffixes_to_remove:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break 
            
            flatlist_content += f"    {base_name}\t, {mkflat_file_type}\t, loc_def ;\n"
            
            src_asset_path = os.path.join(source_asset_dir_abs, asset_file_name)
            dst_asset_for_mkflat_path = os.path.join(mkflat_staging_dir_abs, asset_file_name)
            if os.path.exists(src_asset_path):
                try:
                    shutil.copy2(src_asset_path, dst_asset_for_mkflat_path)
                except Exception as e:
                    log_message(self.log_area, f"Error copying {asset_file_name} to mkflat staging: {e}")
                    if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
                    return False
            else:
                log_message(self.log_area, f"Warning: Source asset {src_asset_path} not found for copying.")
                if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
                return False

        flatlist_content += "}\n"
        
        flatlist_filename_for_mkflat = f"{flatlist_name_stem}.!flatlist" 
        flatlist_path_for_mkflat_abs = os.path.join(mkflat_staging_dir_abs, flatlist_filename_for_mkflat)
        try:
            with open(flatlist_path_for_mkflat_abs, "w", encoding='utf-8') as f:
                f.write(flatlist_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing {flatlist_filename_for_mkflat} to staging: {e}")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return False

        flatdata_output_in_staging_abs = os.path.join(mkflat_staging_dir_abs, f"{flatlist_name_stem}.flatdata")
        # The final destination of the .flatdata file is within the mod's CORE structure
        final_flatdata_target_in_project_abs = os.path.join(core_dir_abs, "shared", "packed_data", f"{flatlist_name_stem}.flatdata")
        
        param_flatdata_output_rel = os.path.relpath(flatdata_output_in_staging_abs, game_root_dir)
        param_flatlist_path_rel = os.path.relpath(flatlist_path_for_mkflat_abs, game_root_dir)

        mk_success, _ = run_starter_command("mkflat", [param_flatdata_output_rel, param_flatlist_path_rel], self.log_area)
        
        if not mk_success or not os.path.exists(flatdata_output_in_staging_abs):
            log_message(self.log_area, f"Error generating {flatlist_name_stem}.flatdata or output not found in staging.")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return False
        
        try:
            # Ensure the target directory in the project exists
            os.makedirs(os.path.dirname(final_flatdata_target_in_project_abs), exist_ok=True)
            shutil.move(flatdata_output_in_staging_abs, final_flatdata_target_in_project_abs)
            log_message(self.log_area, f"{flatlist_name_stem}.flatdata created at {final_flatdata_target_in_project_abs}")
            return True
        except Exception as e:
            log_message(self.log_area, f"Error moving generated {flatlist_name_stem}.flatdata to project: {e}")
            return False # Return False as move failed
        finally: 
            if os.path.exists(mkflat_staging_dir_abs): 
                try:
                    shutil.rmtree(mkflat_staging_dir_abs)
                except Exception as e:
                    log_message(self.log_area, f"Warning: Could not remove mkflat staging for {flatlist_name_stem}: {e}")
    
    def generate_mod_files(self):
        # ... (same as before, calls _generate_desc_addpack_file and _package_asset_archive) ...
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
        os.makedirs(os.path.join(core_dir_abs, "shared", "packed_data"), exist_ok=True)

        if not self._generate_desc_addpack_file(mod_name_val, mod_author_val, mod_version_val, core_dir_abs, current_game_root):
            messagebox.showerror("Error", "Failed to generate desc.addpack. Check log.")
            return

        asset_packaging_configs = [
            {
                "label": "TEX", "source_subfolder": "prepared_textures", "ext": ".texture",
                "flatlist_stem": "textures", "mkflat_type": "texture"
            },
            # Future sound configs will go here
        ]
        
        all_archives_successful = True
        archives_packaged_count = 0

        for config in asset_packaging_configs:
            prefix_to_check = f"[{config['label']}] "
            if any(s.startswith(prefix_to_check) for s in selected_asset_filenames_with_prefix):
                success = self._package_asset_archive(
                    asset_type_label=config["label"],
                    source_subfolder_rel=config["source_subfolder"],
                    asset_extension=config["ext"],
                    flatlist_name_stem=config["flatlist_stem"],
                    mkflat_file_type=config["mkflat_type"],
                    selected_asset_filenames_with_prefix=selected_asset_filenames_with_prefix,
                    mod_project_dir=current_mod_project_dir,
                    game_root_dir=current_game_root,
                    core_dir_abs=core_dir_abs
                )
                if success:
                    archives_packaged_count +=1
                else:
                    all_archives_successful = False
                    log_message(self.log_area, f"Failed to package {config['flatlist_stem']}.flatdata.")
        
        if archives_packaged_count == 0:
             log_message(self.log_area, "No asset archives were generated as no matching files were selected or processed for defined types.")
             messagebox.showwarning("Packaging Skipped", "No asset archives were generated. Ensure files are selected and correctly prefixed for defined asset types (e.g., [TEX]).")
             return

        if all_archives_successful and archives_packaged_count > 0:
            log_message(self.log_area, "All selected mod files generated successfully in CORE directory.")
            messagebox.showinfo("Success", "Mod files (desc.addpack and selected .flatdata archives) generated successfully!")
        elif archives_packaged_count > 0 : 
            log_message(self.log_area, "Some mod files generated, but errors occurred with others. Check log.")
            messagebox.showwarning("Partial Success", "Some mod files generated, but errors occurred. Check log.")
        else: 
            log_message(self.log_area, "Failed to generate mod asset files. Check log.")
            messagebox.showerror("Error", "Failed to generate mod asset files. Check log for details.")

    def create_mod_archive(self):
        # ... (same as before) ...
        if not self._validate_paths(check_mod_project=True): return
        
        mod_name_val = self.mod_name_var.get()
        mod_name_for_archive = self.mod_name_var.get() # Use original mod name for archive file name if possible
        # Sanitize for file name
        mod_name_for_archive = re.sub(r'[^\w\s_-]', '_', mod_name_for_archive).strip()
        mod_name_for_archive = re.sub(r'\s+', '_', mod_name_for_archive)
        if not mod_name_for_archive: mod_name_for_archive = "MyMod"


        if not mod_name_val: # Check original mod name for error message
            messagebox.showerror("Error", "Mod Name (from Project Setup tab) must be set to create an archive.")
            log_message(self.log_area, "Error: Mod Name must be set for archive creation.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        core_dir_to_archive = os.path.join(current_mod_project_dir, "CORE")
        readme_file_to_archive = os.path.join(current_mod_project_dir, "readme.txt")

        if not os.path.isdir(core_dir_to_archive) or not os.path.exists(os.path.join(core_dir_to_archive,"desc.addpack")):
            messagebox.showerror("Error", "CORE directory or desc.addpack not found. Generate mod files first.")
            log_message(self.log_area, "Error: CORE/desc.addpack not found. Generate mod files first.")
            return
        
        if not os.path.exists(readme_file_to_archive):
            log_message(self.log_area, f"readme.txt not found at {readme_file_to_archive}. Creating a basic one.")
            try:
                with open(readme_file_to_archive, "w", encoding='utf-8') as f:
                    f.write(f"Mod: {mod_name_val}\n") # Use original mod_name_val for readme content
                    f.write(f"Author: {self.mod_author_var.get() or 'Unknown'}\n")
                    f.write(f"Version: {self.mod_version_var.get() or '100'}\n\n")
                    f.write("Basic mod description.")
            except Exception as e:
                log_message(self.log_area, f"Warning: Could not create readme.txt: {e}")

        archive_save_path = filedialog.asksaveasfilename(
            title="Save Mod Archive As",
            initialdir=os.path.dirname(current_mod_project_dir) or current_mod_project_dir,
            initialfile=f"{mod_name_for_archive}.gt2extension", # Use sanitized name for file
            defaultextension=".gt2extension",
            filetypes=[("Graviteam Mod Archive", "*.gt2extension"), ("Zip files", "*.zip")]
        )
        if not archive_save_path:
            log_message(self.log_area, "Mod archive creation cancelled.")
            return
        
        if not archive_save_path.lower().endswith(".gt2extension"):
            archive_save_path = os.path.splitext(archive_save_path)[0] + ".gt2extension"

        archive_basename_for_shutil = os.path.splitext(archive_save_path)[0] 
        
        staging_dir = None
        try:
            staging_dir = os.path.join(current_mod_project_dir, "_archive_staging_temp")
            if os.path.exists(staging_dir): shutil.rmtree(staging_dir)
            os.makedirs(staging_dir)

            shutil.copytree(core_dir_to_archive, os.path.join(staging_dir, "CORE"))
            if os.path.exists(readme_file_to_archive):
                shutil.copy2(readme_file_to_archive, os.path.join(staging_dir, "readme.txt"))

            shutil.make_archive(archive_basename_for_shutil, 'zip', root_dir=staging_dir)
            created_zip_file = archive_basename_for_shutil + ".zip"

            if os.path.exists(archive_save_path): os.remove(archive_save_path)
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
                except Exception as e:
                    log_message(self.log_area, f"Warning: Could not remove staging directory {staging_dir}: {e}")

app = None
if __name__ == "__main__":
    root = tk.Tk()
    app = TextureModTool(root)
    root.mainloop()