import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import shutil
import configparser
import time
import re # For sanitizing folder names

# --- Tooltip Class ---
# Provides a simple tooltip popup for Tkinter widgets.
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        # Bind mouse events to show/hide the tooltip
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip) # Hide on click as well

    def show_tooltip(self, event=None):
        # Displays the tooltip window near the widget.
        if self.tooltip_window or not self.text:
            return
        
        # Calculate tooltip position
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # No window decorations

        # Tooltip label styling
        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"), wraplength=350) # Wraps text if too long
        label.pack(ipadx=2, ipady=2)

        tooltip_width = label.winfo_reqwidth()
        tooltip_height = label.winfo_reqheight()

        # Adjust position if tooltip goes off-screen
        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - 5
        if y + tooltip_height > screen_height:
            y = self.widget.winfo_rooty() - tooltip_height - 5

        self.tooltip_window.wm_geometry(f"+{int(x)}+{int(y)}")


    def hide_tooltip(self, event=None):
        # Destroys the tooltip window.
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

# --- Configuration ---
# File to store user paths
CONFIG_FILE = "gt_texture_mod_tool_config.ini"
# Global variables for storing game and mod paths
GAME_ROOT_DIR = ""
MOD_PROJECT_DIR = ""
STARTER_EXE_PATH = "" # Path to the game's command-line utility

# --- Helper Functions ---
def get_unique_timestamp_suffix():
    """Generates a unique timestamp string including microseconds for unique filenames."""
    return f"{time.strftime('%Y%m%d%H%M%S')}_{int(time.time() * 1000000) % 1000000}"

def load_config():
    """Loads game and mod directory paths from the configuration file."""
    global GAME_ROOT_DIR, MOD_PROJECT_DIR
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        GAME_ROOT_DIR = config.get("Paths", "GameRootDir", fallback="")
        MOD_PROJECT_DIR = config.get("Paths", "ModProjectDir", fallback="")
        update_starter_exe_path() # Update starter.exe path based on loaded game root
    # Update UI fields if the application window exists
    if 'app' in globals() and app:
        if hasattr(app, 'game_root_var'): app.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(app, 'mod_project_dir_var'): app.mod_project_dir_var.set(MOD_PROJECT_DIR)

def save_config():
    """Saves the current game and mod directory paths to the configuration file."""
    config = configparser.ConfigParser()
    config["Paths"] = {
        "GameRootDir": GAME_ROOT_DIR,
        "ModProjectDir": MOD_PROJECT_DIR,
    }
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

def update_starter_exe_path():
    """Updates the global STARTER_EXE_PATH based on the GAME_ROOT_DIR."""
    global STARTER_EXE_PATH
    if GAME_ROOT_DIR:
        STARTER_EXE_PATH = os.path.join(GAME_ROOT_DIR, "starter.exe")
    else:
        STARTER_EXE_PATH = ""

def run_starter_command(command_name, params_list, log_area_widget, timeout=120):
    """
    Executes a command using the game's starter.exe utility.
    Args:
        command_name (str): The command to run (e.g., "unflat", "atf2dds").
        params_list (list): A list of parameters for the command.
        log_area_widget (tk.Text): The text widget used for logging output.
        timeout (int): Maximum time in seconds to wait for the command to complete.
    Returns:
        tuple: (bool, str_or_None) where bool indicates success, 
               and str_or_None is the output path if relevant (e.g., for "unflat").
    """
    if not STARTER_EXE_PATH or not os.path.exists(STARTER_EXE_PATH):
        log_message(log_area_widget, "Error: starter.exe not found. Set Game Root Directory.")
        return False, None
    if not GAME_ROOT_DIR or not os.path.isdir(GAME_ROOT_DIR):
        log_message(log_area_widget, "Error: Game Root Directory is not set or invalid.")
        return False, None

    # Construct the command string
    cmd_string_part = f"{command_name}"
    if params_list:
        # Join parameters with commas, handling None values
        params_str = ','.join(map(lambda p: str(p) if p is not None else "", params_list))
        cmd_string_part += f",{params_str}"

    command = [STARTER_EXE_PATH, cmd_string_part]
    log_message(log_area_widget, f"Running: \"{STARTER_EXE_PATH}\" \"{cmd_string_part}\"")
    log_message(log_area_widget, f"Working directory: {GAME_ROOT_DIR}")

    process = None
    try:
        # Execute the command
        process = subprocess.Popen(command, cwd=GAME_ROOT_DIR, # Run from game root
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        stdout, stderr = process.communicate(timeout=timeout)

        if stdout: log_message(log_area_widget, f"Output:\n{stdout}")
        if stderr: log_message(log_area_widget, f"Errors:\n{stderr}")

        out_dir_log = os.path.join(GAME_ROOT_DIR, "out") # Game's own log directory
        log_message(log_area_widget, f"Command finished. Check '{out_dir_log}' for detailed logs from starter.exe.")

        if process.returncode != 0:
            log_message(log_area_widget, f"Command failed with return code {process.returncode}")
            return False, None
        # Specific handling for "unflat" command to return the output directory
        if command_name == "unflat" and len(params_list) > 1 and params_list[1]:
             return True, os.path.join(GAME_ROOT_DIR, params_list[1]) # params_list[1] is the output path for unflat
        return True, None
    except subprocess.TimeoutExpired:
        log_message(log_area_widget, "Error: Command timed out.")
        if process: process.kill()
        return False, None
    except Exception as e:
        log_message(log_area_widget, f"Error running command: {e}")
        return False, None

def log_message(log_area_widget, message):
    """Appends a message to the specified Tkinter Text widget."""
    if log_area_widget:
        log_area_widget.config(state=tk.NORMAL) # Enable editing
        log_area_widget.insert(tk.END, str(message) + "\n")
        log_area_widget.see(tk.END) # Scroll to the end
        log_area_widget.config(state=tk.DISABLED) # Disable editing
    else:
        print(message) # Fallback to console if no widget

# Main application class
class TextureModTool:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Gravitool - V1.0.0") # Updated Title
        self.root.geometry("950x900")

        # Apply a modern theme
        style = ttk.Style()
        style.theme_use('clam') 

        # --- Log Area Setup ---
        # Frame for the log area at the bottom
        log_main_frame = ttk.Frame(self.root)
        log_frame = ttk.LabelFrame(log_main_frame, text="Log")
        self.log_area = tk.Text(log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, font=("Segoe UI", 9))
        log_scroll = tk.Scrollbar(log_frame, command=self.log_area.yview)
        self.log_area.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,5))
        log_main_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

        load_config() # Load paths from config file

        # --- Menubar Setup ---
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Set Game Root Directory", command=self.set_game_root)
        filemenu.add_command(label="Set Mod Project Directory", command=self.set_mod_project_dir)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        # --- Main Tabbed Interface ---
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Tab 1: Project Setup
        setup_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(setup_tab_frame, text='1. Project Setup')
        self.create_setup_tab(setup_tab_frame)

        # Tab 2: Asset Extractor
        asset_extractor_main_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(asset_extractor_main_frame, text='2. Asset Extractor')
        self.create_asset_extractor_tab(asset_extractor_main_frame)

        # Tab 3: Mod Texture Conversion
        texture_conversion_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(texture_conversion_tab_frame, text='3. Mod Texture Conversion')
        self.create_texture_conversion_tab(texture_conversion_tab_frame)

        # Tab 4: Sound Modding
        sound_modding_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(sound_modding_tab_frame, text='4. Sound Modding (SFX/Speech)')
        self.create_sound_modding_tab(sound_modding_tab_frame)

        # Tab 5: Asset Packaging
        packaging_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(packaging_tab_frame, text='5. Asset Packaging')
        self.create_packaging_tab(packaging_tab_frame)

        # Initialize UI fields with loaded config values
        if hasattr(self, 'game_root_var'): self.game_root_var.set(GAME_ROOT_DIR)
        if hasattr(self, 'mod_project_dir_var'): self.mod_project_dir_var.set(MOD_PROJECT_DIR)

        if GAME_ROOT_DIR: update_starter_exe_path()
        log_message(self.log_area, "Tool initialized. Set Game Root and Mod Project directories if not already configured.")

        # Definitions for asset types used in packaging and listing
        self.flatdata_definitions = {
            "textures": {
                "mkflat_type": "texture", # Type used by mkflat
                "sources": [{"prefix": "[TEX]", "folder": "prepared_textures", "ext": ".texture"}]
            },
            "sounds": {
                "mkflat_type": "sound", # Type used by mkflat
                "sources": [
                    {"prefix": "[SFX]", "folder": os.path.join("prepared_sounds", "sfx"), "ext": ".loc_def.sound"},
                    {"prefix": "[SPE]", "folder": os.path.join("prepared_sounds", "speech"), "ext": ".loc_def.sound"}
                ]
            }
        }
        # List of asset types to scan for in 'prepared_...' folders
        self.asset_types_to_scan = []
        for definition in self.flatdata_definitions.values():
            for source in definition["sources"]:
                self.asset_types_to_scan.append(source.copy())

        self.confirmation_result = None # Stores result from the mod details confirmation dialog

    def create_setup_tab(self, tab_frame):
        """Creates the UI elements for the 'Project Setup' tab."""
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        # Game Root Directory selection
        ttk.Label(frame, text="Game Root:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.game_root_var = tk.StringVar(value=GAME_ROOT_DIR)
        ttk.Entry(frame, textvariable=self.game_root_var, width=60).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        game_root_browse_btn = ttk.Button(frame, text="Browse", command=self.set_game_root)
        game_root_browse_btn.grid(row=0, column=2, padx=5, pady=5)
        ToolTip(game_root_browse_btn, "Select the main installation folder of your Graviteam game (e.g., where starter.exe is located).")

        # Mod Project Directory selection
        ttk.Label(frame, text="Mod Project Dir:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mod_project_dir_var = tk.StringVar(value=MOD_PROJECT_DIR)
        ttk.Entry(frame, textvariable=self.mod_project_dir_var, width=60).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        mod_project_browse_btn = ttk.Button(frame, text="Browse/Create", command=self.set_mod_project_dir)
        mod_project_browse_btn.grid(row=1, column=2, padx=5, pady=5)
        ToolTip(mod_project_browse_btn, "Select an existing folder or a location to create a new folder for your mod project files.")

        frame.grid_columnconfigure(1, weight=1) # Allow entry field to expand

        # Mod Information input fields (for desc.addpack and readme.txt)
        info_frame = ttk.LabelFrame(frame, text="Mod Information (for desc.addpack & readme.txt)", padding="10")
        info_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky="ew")

        ttk.Label(info_frame, text="Mod Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.mod_name_var = tk.StringVar(value="MyMod") # Default mod name
        ttk.Entry(info_frame, textvariable=self.mod_name_var, width=40).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ToolTip(ttk.Label(info_frame, text="Mod Name:"), "The display name of your mod. Used in desc.addpack and readme.txt.\nAvoid special characters that are invalid in folder names.")

        ttk.Label(info_frame, text="Author:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.mod_author_var = tk.StringVar(value="Modder") # Default author
        ttk.Entry(info_frame, textvariable=self.mod_author_var, width=40).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(info_frame, text="Version (e.g., 100 for 1.00):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.mod_version_var = tk.StringVar(value="100") # Default version
        ttk.Entry(info_frame, textvariable=self.mod_version_var, width=10).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        info_frame.grid_columnconfigure(1, weight=1) # Allow entry field to expand

        # Button to initialize mod project folder structure
        init_folders_button = ttk.Button(frame, text="Initialize/Verify Mod Project Folders", command=self.initialize_mod_folders)
        init_folders_button.grid(row=4, column=0, columnspan=3, pady=10)
        ToolTip(init_folders_button,
                "Creates standard subfolders for textures, sounds (SFX/Speech), etc.,\n"
                "within your Mod Project Directory and a template readme.txt if they don't exist.")

    def create_asset_extractor_tab(self, parent_tab_frame):
        """Creates the UI for the 'Asset Extractor' tab, with sub-tabs for textures and sounds."""
        main_frame = ttk.Frame(parent_tab_frame, padding="5")
        main_frame.pack(expand=True, fill='both')

        self.asset_extractor_notebook = ttk.Notebook(main_frame)
        self.asset_extractor_notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # Sub-tab for Texture Extraction
        texture_extractor_sub_tab_frame = ttk.Frame(self.asset_extractor_notebook)
        self.asset_extractor_notebook.add(texture_extractor_sub_tab_frame, text='Texture Extractor')
        self._create_texture_extractor_sub_tab_content(texture_extractor_sub_tab_frame)

        # Sub-tab for Sound Extraction
        sound_extractor_sub_tab_frame = ttk.Frame(self.asset_extractor_notebook)
        self.asset_extractor_notebook.add(sound_extractor_sub_tab_frame, text='Sound Extractor (SFX/Speech)')
        self._create_sound_extractor_sub_tab_content(sound_extractor_sub_tab_frame)

    def _create_texture_extractor_sub_tab_content(self, tab_frame):
        """Creates UI elements for the 'Texture Extractor' sub-tab."""
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="This tool will unpack game texture archives (.flatdata) to your Mod Project Directory, \nconvert them to .dds, and generate a list of available textures.").pack(pady=(0,5))

        # Checkboxes for selecting game texture archives
        archive_frame = ttk.LabelFrame(frame, text="Select Game Texture Archives to Extract", padding="10")
        archive_frame.pack(fill=tk.X, pady=5)

        self.texture_archives_vars = {} # Stores BooleanVars for checkboxes
        known_texture_archives = [ # Common texture archives in Graviteam games
            "tex_main.flatdata", "tex_main_01.flatdata", "tex_misc.flatdata", "tex_objects.flatdata",
            "tex_humans.flatdata", "tex_techns.flatdata", "tex_dummy.flatdata", "textures_loc.flatdata"
        ]
        for i, archive_name in enumerate(known_texture_archives):
            var = tk.BooleanVar(value=True if archive_name in ["tex_main.flatdata", "tex_objects.flatdata"] else False) # Default selection
            chk = ttk.Checkbutton(archive_frame, text=archive_name, variable=var)
            chk.grid(row=i//2, column=i%2, padx=5, pady=2, sticky="w") # Arrange in two columns
            self.texture_archives_vars[archive_name] = var

        # Option to delete original .texture (ATF) files after DDS conversion
        self.delete_atf_after_extraction_var = tk.BooleanVar(value=True)
        delete_chk = ttk.Checkbutton(frame, text="Delete original .texture files from 'extracted_game_textures/atf/' after successful DDS conversion",
                        variable=self.delete_atf_after_extraction_var)
        delete_chk.pack(pady=(5,0), anchor="w", padx=20)
        ToolTip(delete_chk, "If checked, successfully converted .texture files in the 'extracted_game_textures/atf/' subfolders\nwill be deleted to save space. DDS files will remain.")

        # Button to start texture extraction and conversion
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

        # Listbox to display extracted texture files
        listbox_container_frame = ttk.Frame(frame)
        listbox_container_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=20)
        self.extracted_texture_listbox = tk.Listbox(listbox_container_frame, height=8, relief=tk.SUNKEN, borderwidth=1)
        list_scroll = tk.Scrollbar(listbox_container_frame, orient=tk.VERTICAL, command=self.extracted_texture_listbox.yview)
        self.extracted_texture_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.extracted_texture_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Button to save the list of extracted textures
        save_list_button = ttk.Button(frame, text="Save Texture List to File", command=self.save_extracted_texture_list)
        save_list_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(save_list_button, "Saves the list of extracted .dds texture paths (shown above) to a text file.")

    def _create_sound_extractor_sub_tab_content(self, tab_frame):
        """Creates UI elements for the 'Sound Extractor' sub-tab."""
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="This tool will unpack game sound archives (.flatdata) to your Mod Project Directory.\n.loc_def.sound files will be renamed to .aaf, and a list of available sound files will be generated.").pack(pady=(0,5))

        # Checkboxes for selecting game sound archives
        sound_archive_frame = ttk.LabelFrame(frame, text="Select Game Sound Archives to Extract", padding="10")
        sound_archive_frame.pack(fill=tk.X, pady=5)

        self.sound_archives_vars = {} # Stores BooleanVars for checkboxes
        known_sound_archives = [ # Common sound archives
            "sounds.flatdata",
            "speech.flatdata",
            "speech_eng.flatdata", # Language-specific speech archives
            "speech_rus.flatdata",
            "speech_ger.flatdata",
        ]
        default_sound_archives = ["sounds.flatdata", "speech.flatdata"] # Pre-select common ones

        for i, archive_name in enumerate(known_sound_archives):
            var = tk.BooleanVar(value=True if archive_name in default_sound_archives else False)
            chk = ttk.Checkbutton(sound_archive_frame, text=archive_name, variable=var)
            chk.grid(row=i, column=0, padx=5, pady=2, sticky="w") # Single column for sound archives
            self.sound_archives_vars[archive_name] = var

        # Option to delete temporary unpack folders
        self.delete_temp_sound_unflat_var = tk.BooleanVar(value=True)
        delete_temp_chk = ttk.Checkbutton(frame, text="Delete temporary unpack folders after extraction",
                                          variable=self.delete_temp_sound_unflat_var)
        delete_temp_chk.pack(pady=(5,0), anchor="w", padx=20)
        ToolTip(delete_temp_chk, "If checked, the temporary folders created by 'unflat' in the game directory\nwill be deleted after sound files are copied to your mod project.")

        # Button to start sound archive extraction
        extract_sound_button = ttk.Button(frame, text="Unpack Selected Sound Archives (and convert .loc_def.sound to .aaf)", command=self.extract_and_unpack_game_sounds)
        extract_sound_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(extract_sound_button,
                "Unpacks selected game sound archives (.flatdata) using 'unflat'.\n"
                "Extracted .loc_def.sound files are renamed to .aaf.\n"
                "Final sound files (e.g., .aaf) are saved to 'ModProjectDir/extracted_game_sounds/[archive_name]/'.")

        ttk.Label(frame, text="(.aaf files, converted from .loc_def.sound, will be in 'ModProjectDir/extracted_game_sounds/[archive_name]/')").pack()
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(frame, text="Extracted Sound File List (relative to 'extracted_game_sounds/'):").pack(pady=(5,0))

        # Listbox to display extracted sound files
        sound_listbox_container_frame = ttk.Frame(frame)
        sound_listbox_container_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=20)
        self.extracted_sound_listbox = tk.Listbox(sound_listbox_container_frame, height=8, relief=tk.SUNKEN, borderwidth=1)
        sound_list_scroll = tk.Scrollbar(sound_listbox_container_frame, orient=tk.VERTICAL, command=self.extracted_sound_listbox.yview)
        self.extracted_sound_listbox.configure(yscrollcommand=sound_list_scroll.set)
        sound_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.extracted_sound_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Button to save the list of extracted sounds
        save_sound_list_button = ttk.Button(frame, text="Save Sound List to File", command=self.save_extracted_sound_list)
        save_sound_list_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(save_sound_list_button, "Saves the list of extracted sound file paths (shown above) to a text file.")


    def create_texture_conversion_tab(self, tab_frame):
        """Creates UI elements for the 'Mod Texture Conversion' tab."""
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        ttk.Label(frame, text="Use these tools to convert textures for your mod.").pack(pady=(0,10))
        ttk.Label(frame, text="Typically, you'd copy desired .dds files from 'extracted_game_textures/dds/'\n to 'dds_work/', edit them, then convert back to .texture.").pack(pady=(0,10))

        # Button to convert .texture (ATF) to .dds
        atf_to_dds_button = ttk.Button(frame, text="Convert Game .texture (ATF) to .dds (for editing)", command=self.convert_atf_to_dds_for_modding)
        atf_to_dds_button.pack(pady=10, fill=tk.X, padx=20)
        ToolTip(atf_to_dds_button,
                "Select one or more .texture (ATF) files.\n"
                "Converts them to .dds format using 'atf2dds'.\n"
                "Output .dds files are saved in 'ModProjectDir/dds_work/'.")

        ttk.Label(frame, text="Select any .texture file. Output .dds will be in 'ModProjectDir/dds_work/'").pack(pady=(0,10))
        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        # Button to convert .dds to .texture (ATF)
        dds_to_atf_button = ttk.Button(frame, text="Convert Edited .dds to Game .texture (ATF)", command=self.convert_dds_to_atf_for_modding)
        dds_to_atf_button.pack(pady=10, fill=tk.X, padx=20)
        ToolTip(dds_to_atf_button,
                "Select one or more .dds files (typically from 'dds_work/').\n"
                "Converts them to .texture (ATF) format using 'dds2atf'.\n"
                "Output .texture files are saved in 'ModProjectDir/prepared_textures/'.")
        ttk.Label(frame, text="Select .dds from 'dds_work/'. Output .texture will be in 'ModProjectDir/prepared_textures/'").pack(pady=(0,10))

    def create_sound_modding_tab(self, tab_frame):
        """Creates UI elements for the 'Sound Modding' tab."""
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        # Frame for WAV to AAF (.loc_def.sound) conversion
        aaf_frame = ttk.LabelFrame(frame, text="Convert .wav to Game Sound Format (.loc_def.sound)", padding="10")
        aaf_frame.pack(fill=tk.X, pady=10)

        ttk.Label(aaf_frame, text="Input .wav format: 44.1kHz, 16-bit. Mono for 3D SFX, Stereo for UI/System sounds.").pack(anchor="w", pady=(0,5))

        # Radio buttons to select sound type (SFX or Speech) for output folder
        sound_type_frame = ttk.Frame(aaf_frame)
        sound_type_frame.pack(anchor="w", pady=(0,5))
        ttk.Label(sound_type_frame, text="Output Type:").pack(side=tk.LEFT, padx=(0,5))
        self.sound_type_var = tk.StringVar(value="SFX") # Default to SFX
        sfx_radio = ttk.Radiobutton(sound_type_frame, text="SFX (to prepared_sounds/sfx)", variable=self.sound_type_var, value="SFX")
        sfx_radio.pack(side=tk.LEFT, padx=5)
        ToolTip(sfx_radio, "Sound effects (e.g., explosions, vehicle sounds) are typically mono.")
        speech_radio = ttk.Radiobutton(sound_type_frame, text="Speech (to prepared_sounds/speech)", variable=self.sound_type_var, value="Speech")
        speech_radio.pack(side=tk.LEFT, padx=5)
        ToolTip(speech_radio, "Speech files.")

        # Button to convert .wav to .loc_def.sound
        wav_to_aaf_button = ttk.Button(aaf_frame, text="Select .wav File(s) and Convert to .loc_def.sound", command=self.convert_wav_to_aaf)
        wav_to_aaf_button.pack(fill=tk.X, pady=5)
        ToolTip(wav_to_aaf_button, "Uses 'starter.exe wav2aaf'.\nOutput .loc_def.sound files are saved in the selected 'prepared_sounds' subfolder.")

        # Informational text about sound modding
        info_text = (
            "General Notes for SFX/Speech:\n"
            "- Game sound files use the .loc_def.sound extension (internally AAF format).\n"
            "- After conversion, refresh the list in the 'Asset Packaging' tab to include them in your mod."
        )
        ttk.Label(frame, text=info_text, justify=tk.LEFT, wraplength=800).pack(pady=10, anchor="w")


    def create_packaging_tab(self, tab_frame):
        """Creates UI elements for the 'Asset Packaging' tab."""
        frame = ttk.Frame(tab_frame, padding="10")
        frame.pack(expand=True, fill='both')

        # Listbox for selecting prepared assets to include in the mod
        list_frame = ttk.LabelFrame(frame, text="Select asset files from 'prepared_...' folders to include in mod", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.packaged_assets_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10, relief=tk.SUNKEN, borderwidth=1)
        list_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.packaged_assets_listbox.yview)
        self.packaged_assets_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.packaged_assets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Button to refresh the list of prepared assets
        refresh_button = ttk.Button(frame, text="Refresh List from 'prepared_...' folders", command=self.load_prepared_assets)
        refresh_button.pack(pady=(5,10), fill=tk.X, padx=20)
        ToolTip(refresh_button, "Updates the list above with recognized asset files currently in\n"
                                 "'ModProjectDir/prepared_textures/' (.texture) and\n"
                                 "'ModProjectDir/prepared_sounds/(sfx/speech)/' (.loc_def.sound).")

        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        # Button to generate mod files (desc.addpack, .flatdata archives)
        generate_files_button = ttk.Button(frame, text="1. Generate Mod Files (desc.addpack & .flatdata archives)", command=self.generate_mod_files)
        generate_files_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(generate_files_button,
                "First, you'll confirm/edit mod details (name, author, version).\n"
                "Then, for selected assets:\n"
                "- Creates 'desc.addpack' in 'CORE/' using confirmed details.\n"
                "- Updates 'readme.txt' in the project root with confirmed details.\n"
                "- Creates appropriate '.!flatlist' files in a temporary staging area.\n"
                "- Copies selected asset files to the staging area.\n"
                "- Creates '.flatdata' archives (e.g., textures.flatdata, sounds.flatdata)\n"
                "  using 'mkflat' and places them in 'CORE/shared/packed_data/'.\n"
                "- Cleans up temporary staging files.")

        # Button to create the final .gt2extension mod archive
        create_archive_button = ttk.Button(frame, text="2. Create .gt2extension Mod Archive", command=self.create_mod_archive)
        create_archive_button.pack(pady=5, fill=tk.X, padx=20)
        ToolTip(create_archive_button,
                "Packages the 'CORE/' folder and 'readme.txt' from your Mod Project Directory\n"
                "into a distributable .gt2extension archive file (a renamed .zip).\n"
                "Uses the mod details currently set in the 'Project Setup' tab (which should have been confirmed via 'Generate Mod Files').")

    def _validate_paths(self, check_mod_project=True, check_starter=True):
        """Validates that essential paths (Game Root, Mod Project, starter.exe) are set and valid."""
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
                 # This is not an error, as it can be created by initialize_mod_folders
                 log_message(self.log_area, f"Mod Project Directory '{MOD_PROJECT_DIR}' does not exist yet. It will be created if needed.")
        return True

    def set_game_root(self):
        """Opens a dialog to select the Game Root Directory and saves it."""
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
        """Opens a dialog to select or create the Mod Project Directory and saves it."""
        global MOD_PROJECT_DIR
        initial_dir_suggestion = ""
        current_game_root = self.game_root_var.get()
        # Suggest a 'modwork' subfolder in the game's 'users' directory
        if current_game_root and os.path.isdir(current_game_root):
            initial_dir_suggestion = os.path.join(current_game_root, "users", "modwork")
            os.makedirs(initial_dir_suggestion, exist_ok=True) # Create if it doesn't exist

        directory = filedialog.askdirectory(title="Select or Create Mod Project Directory", initialdir=initial_dir_suggestion or None)
        if directory:
            self.mod_project_dir_var.set(directory)
            MOD_PROJECT_DIR = directory
            save_config()
            log_message(self.log_area, f"Mod Project Directory set to: {MOD_PROJECT_DIR}")
            self.initialize_mod_folders(silent=True) # Initialize folders silently after setting

    def _update_readme_file(self):
        """
        Creates or updates the readme.txt file in the mod project directory
        using the current mod information from the UI StringVars. 
        Attempts to preserve any existing description in the readme.
        """
        current_mod_project_dir = self.mod_project_dir_var.get()
        if not current_mod_project_dir:
            log_message(self.log_area, "Mod Project Directory not set. Cannot update readme.txt.")
            return False

        readme_path = os.path.join(current_mod_project_dir, "readme.txt")
        # Get values directly from StringVars, as these are the source of truth after confirmation dialog
        mod_name = self.mod_name_var.get() or "MyMod"
        mod_author = self.mod_author_var.get() or "Unknown Author"
        mod_version = self.mod_version_var.get() or "100"

        existing_description = "Replace this with your mod's description." # Default description

        # Try to read existing description if readme.txt exists
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding='utf-8') as f:
                    lines = f.readlines()
                desc_line_index = -1
                for i, line in enumerate(lines):
                    if line.strip().lower().startswith("description:"):
                        desc_line_index = i
                        break
                if desc_line_index != -1 and desc_line_index + 1 < len(lines):
                    existing_description = "".join(lines[desc_line_index+1:]).strip()
                    if not existing_description: # Ensure there's a placeholder if empty
                        existing_description = "Replace this with your mod's description."
            except Exception as e:
                log_message(self.log_area, f"Warning: Could not read existing readme.txt to preserve description: {e}. A new one will be created with default description.")

        # Write the new or updated readme.txt
        try:
            with open(readme_path, "w", encoding='utf-8') as f:
                f.write(f"Mod: {mod_name}\n")
                f.write(f"Author: {mod_author}\n")
                f.write(f"Version: {mod_version}\n\n")
                f.write("Description:\n")
                f.write(f"{existing_description}\n")
            log_message(self.log_area, f"readme.txt updated at: {readme_path} with Name: {mod_name}, Author: {mod_author}, Version: {mod_version}")
            return True
        except Exception as e:
            log_message(self.log_area, f"Error updating readme.txt {readme_path}: {e}")
            return False

    def initialize_mod_folders(self, silent=False):
        """
        Creates the standard folder structure for a mod project if it doesn't already exist.
        Also creates a template readme.txt if one is not present.
        Args:
            silent (bool): If True, suppresses non-critical log messages and popups.
        """
        if not self._validate_paths(check_mod_project=True, check_starter=False): # Starter not needed for this
            if not self.mod_project_dir_var.get(): # Specific check if mod project dir is the issue
                 if not silent:
                    log_message(self.log_area, "Mod project directory not set, cannot initialize folders.")
                    messagebox.showerror("Error", "Mod Project Directory is not set. Cannot initialize folders.")
                 return False

        current_mod_project_dir = self.mod_project_dir_var.get()

        # Create the main mod project directory if it doesn't exist
        if not os.path.isdir(current_mod_project_dir):
            try:
                os.makedirs(current_mod_project_dir)
                if not silent: log_message(self.log_area, f"Created Mod Project Directory: {current_mod_project_dir}")
            except Exception as e:
                log_message(self.log_area, f"Error creating Mod Project Directory {current_mod_project_dir}: {e}")
                if not silent: messagebox.showerror("Error", f"Could not create Mod Project Directory: {e}")
                return False

        # Define standard subfolders for the mod project
        paths_to_create = {
            "dds_work": os.path.join(current_mod_project_dir, "dds_work"), # For DDS files being edited
            "prepared_textures": os.path.join(current_mod_project_dir, "prepared_textures"), # For final .texture files
            "CORE_dir": os.path.join(current_mod_project_dir, "CORE"), # For game-installable files
            "CORE_shared_packed_data": os.path.join(current_mod_project_dir, "CORE", "shared", "packed_data"), # For .flatdata archives
            "extracted_atf_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "atf"), # Original .texture files
            "extracted_dds_base": os.path.join(current_mod_project_dir, "extracted_game_textures", "dds"), # Converted .dds from game
            "extracted_sounds_base": os.path.join(current_mod_project_dir, "extracted_game_sounds"), # Extracted game sounds
            "wav_sfx_work": os.path.join(current_mod_project_dir, "wav_sfx_work"), # For SFX .wav files
            "wav_speech_work": os.path.join(current_mod_project_dir, "wav_speech_work"), # For Speech .wav files
            "prepared_sounds_sfx": os.path.join(current_mod_project_dir, "prepared_sounds", "sfx"), # Final SFX .loc_def.sound
            "prepared_sounds_speech": os.path.join(current_mod_project_dir, "prepared_sounds", "speech"), # Final Speech .loc_def.sound
        }

        created_any_folder = False
        for key, p in paths_to_create.items():
            if not os.path.exists(p):
                try:
                    os.makedirs(p, exist_ok=True)
                    if not silent: log_message(self.log_area, f"Created folder: {p}")
                    created_any_folder = True
                except Exception as e:
                    log_message(self.log_area, f"Error creating folder {p}: {e}")
                    if not silent: messagebox.showerror("Error", f"Could not create folder {p}: {e}")
                    return False

        # Create or update readme.txt
        readme_path = os.path.join(current_mod_project_dir, "readme.txt")
        readme_created_or_updated_now = False
        if not os.path.exists(readme_path):
            if self._update_readme_file(): # Uses current mod info from UI
                if not silent: log_message(self.log_area, f"Created template readme.txt: {readme_path}")
                readme_created_or_updated_now = True
            else:
                if not silent: log_message(self.log_area, f"Failed to create readme.txt during initialization.")

        if not created_any_folder and not readme_created_or_updated_now and not silent:
            log_message(self.log_area, "Mod project folders and readme.txt already seem to exist or no new ones needed.")
        elif (created_any_folder or readme_created_or_updated_now) and not silent:
            log_message(self.log_area, "Mod project folder structure and/or readme.txt initialized/verified.")
        return True


    def extract_and_convert_game_textures(self):
        """
        Handles the process of unpacking selected game texture archives (.flatdata),
        converting the contained .texture files to .dds, and listing them.
        """
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True): # Ensure folders exist
            log_message(self.log_area, "Failed to initialize mod project folders for texture extraction.")
            return

        # --- ADDED POPUP ---
        # Inform the user about the potential duration of the process.
        messagebox.showinfo("Texture Extraction", 
                            "The texture extraction and conversion process can take several minutes, "
                            "especially for large archives or a large number of selections.\n\n"
                            "The tool may appear unresponsive during this time. Please be patient.")
        self.root.update_idletasks() # Ensure the messagebox is shown before continuing

        selected_archives = [name for name, var in self.texture_archives_vars.items() if var.get()]
        if not selected_archives:
            messagebox.showinfo("No Selection", "No texture archives selected for extraction.")
            return

        log_message(self.log_area, f"Starting texture extraction for: {', '.join(selected_archives)}")
        self.extracted_texture_listbox.delete(0, tk.END) # Clear previous list
        all_extracted_texture_names_for_file = [] # For saving to file

        timestamp_prefix = time.strftime("%Y%m%d-%H%M%S")
        # Define base directories for extracted ATF (original .texture) and DDS files within the mod project
        final_extracted_atf_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_textures", "atf")
        final_extracted_dds_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_textures", "dds")
        current_game_root = self.game_root_var.get()

        for archive_name in selected_archives:
            # Default path for shared texture archives
            archive_path_rel_to_game_root = os.path.join("data", "k43t", "shared", "packed_data", archive_name)

            # Check for localized texture archives if not found in shared path
            if not os.path.exists(os.path.join(current_game_root, archive_path_rel_to_game_root)):
                found_loc_archive = False
                for loc_folder in ["loc_eng", "loc_rus", "loc_ger", "loc_def"]: # Common localization folders
                    alt_archive_path_rel = os.path.join("data", "k43t", loc_folder, "packed_data", archive_name)
                    if os.path.exists(os.path.join(current_game_root, alt_archive_path_rel)):
                        archive_path_rel_to_game_root = alt_archive_path_rel
                        found_loc_archive = True
                        log_message(self.log_area, f"Found localized texture archive at: {alt_archive_path_rel}")
                        break
                if not found_loc_archive:
                    log_message(self.log_area, f"Warning: Texture archive '{archive_name}' not found in common game data paths. Skipping.")
                    continue

            log_message(self.log_area, f"Processing texture archive: {archive_path_rel_to_game_root}")
            archive_base_name = os.path.splitext(archive_name)[0] # e.g., "tex_main" from "tex_main.flatdata"

            # Define a unique temporary output directory for 'unflat' within the game's user work area
            starter_unflat_output_rel = os.path.join("users", "modwork", f"_temp_unflat_tex_{archive_base_name}_{timestamp_prefix}_{get_unique_timestamp_suffix()}")
            starter_unflat_output_abs = os.path.join(current_game_root, starter_unflat_output_rel)
            os.makedirs(os.path.dirname(starter_unflat_output_abs), exist_ok=True)

            # Run 'unflat' command to unpack the archive
            success, unflat_output_actual_abs = run_starter_command("unflat", [archive_path_rel_to_game_root, starter_unflat_output_rel], self.log_area, timeout=300) # Increased timeout for large archives

            if not success or not (unflat_output_actual_abs and os.path.isdir(unflat_output_actual_abs)):
                log_message(self.log_area, f"  Failed to unpack texture archive '{archive_name}'. Output dir: {unflat_output_actual_abs}. Skipping.")
                if os.path.exists(starter_unflat_output_abs): shutil.rmtree(starter_unflat_output_abs) # Clean up temp dir
                continue

            log_message(self.log_area, f"  Successfully unpacked to '{unflat_output_actual_abs}'. Now converting .texture to .dds...")
            # Define final destination directories within the mod project for this archive's ATF and DDS files
            final_atf_archive_dir_in_project = os.path.join(final_extracted_atf_base_abs, archive_base_name)
            final_dds_archive_dir_in_project = os.path.join(final_extracted_dds_base_abs, archive_base_name)
            os.makedirs(final_atf_archive_dir_in_project, exist_ok=True)
            os.makedirs(final_dds_archive_dir_in_project, exist_ok=True)

            textures_in_archive_count = 0
            successfully_converted_atf_paths_in_project = [] # To track files for optional deletion

            # Iterate through unpacked files and convert .texture to .dds
            for item in os.listdir(unflat_output_actual_abs):
                if item.lower().endswith(".texture"): # Process only .texture files
                    textures_in_archive_count += 1
                    src_atf_in_game_temp_abs = os.path.join(unflat_output_actual_abs, item) # Source .texture in game's temp unpack dir
                    dest_atf_in_project_abs = os.path.join(final_atf_archive_dir_in_project, item) # Destination for original .texture in mod project
                    
                    # Copy original .texture to mod project (for backup or if deletion is off)
                    try:
                        shutil.copy2(src_atf_in_game_temp_abs, dest_atf_in_project_abs)
                    except Exception as e:
                        log_message(self.log_area, f"    Error copying {item} to project ATF archive: {e}")
                        continue

                    dds_filename = item.replace(".texture", ".dds")
                    # Temporary output path for DDS file within the game's temp unflat directory
                    temp_dds_output_in_game_temp_rel = os.path.join(starter_unflat_output_rel, dds_filename) 
                    temp_dds_output_in_game_temp_abs = os.path.join(current_game_root, temp_dds_output_in_game_temp_rel)

                    # Path to source ATF relative to game root, as required by atf2dds
                    param_src_atf_rel = os.path.relpath(src_atf_in_game_temp_abs, current_game_root) 
                    # Run 'atf2dds' command
                    conv_success, _ = run_starter_command("atf2dds", [param_src_atf_rel, temp_dds_output_in_game_temp_rel], self.log_area)

                    if conv_success and os.path.exists(temp_dds_output_in_game_temp_abs):
                        # Copy successfully converted DDS to the mod project's DDS directory
                        dest_dds_in_project_abs = os.path.join(final_dds_archive_dir_in_project, dds_filename)
                        try:
                            shutil.copy2(temp_dds_output_in_game_temp_abs, dest_dds_in_project_abs)
                            listbox_entry = os.path.join(archive_base_name, dds_filename) # Relative path for listbox
                            all_extracted_texture_names_for_file.append(listbox_entry)
                            self.extracted_texture_listbox.insert(tk.END, listbox_entry)
                            self.extracted_texture_listbox.see(tk.END)
                            successfully_converted_atf_paths_in_project.append(dest_atf_in_project_abs)
                        except Exception as e:
                            log_message(self.log_area, f"    Error copying converted DDS {dds_filename} to project: {e}")
                    else:
                        log_message(self.log_area, f"    Failed to convert {item} from {archive_name}. Temp DDS not found at {temp_dds_output_in_game_temp_abs}")

            # Optionally delete original .texture files from the mod project's 'atf' backup folder
            if self.delete_atf_after_extraction_var.get() and successfully_converted_atf_paths_in_project:
                log_message(self.log_area, f"  Deleting original .texture files from {final_atf_archive_dir_in_project}...")
                deleted_count = 0
                for atf_to_delete in successfully_converted_atf_paths_in_project:
                    try:
                        if os.path.exists(atf_to_delete):
                           os.remove(atf_to_delete)
                           deleted_count +=1
                    except Exception as e:
                        log_message(self.log_area, f"    Error deleting {os.path.basename(atf_to_delete)} from project ATF backup: {e}")
                if deleted_count > 0:
                    log_message(self.log_area, f"    Successfully deleted {deleted_count} .texture files from project's ATF backup.")
                # Remove the archive-specific ATF subfolder if it's now empty
                if os.path.exists(final_atf_archive_dir_in_project) and not os.listdir(final_atf_archive_dir_in_project):
                    try:
                        os.rmdir(final_atf_archive_dir_in_project)
                        log_message(self.log_area, f"    Removed empty project ATF subfolder: {final_atf_archive_dir_in_project}")
                    except Exception as e:
                        log_message(self.log_area, f"    Could not remove empty project ATF subfolder {final_atf_archive_dir_in_project}: {e}")
            elif not self.delete_atf_after_extraction_var.get():
                 log_message(self.log_area, f"  Kept original .texture files in project's ATF backup: {final_atf_archive_dir_in_project}")

            if textures_in_archive_count == 0:
                log_message(self.log_area, f"  No .texture files found in unpacked '{unflat_output_actual_abs}'.")
            
            # Clean up the temporary unpack directory in the game's folder
            if os.path.exists(starter_unflat_output_abs):
                try:
                    shutil.rmtree(starter_unflat_output_abs)
                    log_message(self.log_area, f"  Cleaned up game temp unpack dir: {starter_unflat_output_abs}")
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove game temp unpack dir {starter_unflat_output_abs}: {e}")
            self.root.update_idletasks() # Keep UI responsive

        log_message(self.log_area, "Game texture extraction and conversion process finished.")
        if not all_extracted_texture_names_for_file:
            log_message(self.log_area, "No textures were successfully extracted and converted.")
        else:
            messagebox.showinfo("Extraction Complete", f"Texture extraction and conversion complete. Check 'extracted_game_textures' and list.")


    def extract_and_unpack_game_sounds(self):
        """
        Handles unpacking selected game sound archives (.flatdata),
        renaming .loc_def.sound files to .aaf, and listing them.
        """
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for sound extraction.")
            return

        selected_sound_archives = [name for name, var in self.sound_archives_vars.items() if var.get()]
        if not selected_sound_archives:
            messagebox.showinfo("No Selection", "No sound archives selected for extraction.")
            return

        log_message(self.log_area, f"Starting sound archive extraction for: {', '.join(selected_sound_archives)}")
        self.extracted_sound_listbox.delete(0, tk.END) # Clear previous list
        all_extracted_sound_files_for_list = [] # For saving to file

        timestamp_prefix = time.strftime("%Y%m%d-%H%M%S")
        # Base directory in mod project for all extracted game sounds
        final_extracted_sounds_base_abs = os.path.join(self.mod_project_dir_var.get(), "extracted_game_sounds")
        os.makedirs(final_extracted_sounds_base_abs, exist_ok=True)

        current_game_root = self.game_root_var.get()
        # Sound file extensions to look for in the unpacked archives.
        # Renaming of .loc_def.sound to .aaf happens after these are copied.
        sound_file_extensions = (".loc_def.sound", ".sound", ".aaf") # Game uses these, primarily .loc_def.sound

        for archive_name in selected_sound_archives:
            # Default path for shared sound archives
            archive_path_rel_to_game_root = os.path.join("data", "k43t", "shared", "packed_data", archive_name)

            # Check for localized sound archives if not found in shared path
            if not os.path.exists(os.path.join(current_game_root, archive_path_rel_to_game_root)):
                found_loc_archive = False
                # Prioritize specific language folders for speech archives
                loc_folders_to_try = ["loc_eng", "loc_rus", "loc_ger", "loc_def"]
                if "speech" in archive_name.lower():
                    speech_lang_part = archive_name.lower().replace(".flatdata","").replace("speech_","")
                    if speech_lang_part in ["eng", "rus", "ger"]: # e.g. speech_eng.flatdata -> loc_eng
                        loc_folders_to_try = [f"loc_{speech_lang_part}", "loc_def"] + loc_folders_to_try
                    else: # For generic speech.flatdata
                        loc_folders_to_try = ["loc_def", "loc_eng", "loc_rus", "loc_ger"]
                
                for loc_folder in loc_folders_to_try:
                    alt_archive_path_rel = os.path.join("data", "k43t", loc_folder, "packed_data", archive_name)
                    if os.path.exists(os.path.join(current_game_root, alt_archive_path_rel)):
                        archive_path_rel_to_game_root = alt_archive_path_rel
                        found_loc_archive = True
                        log_message(self.log_area, f"Found sound archive at: {alt_archive_path_rel}")
                        break
                if not found_loc_archive:
                    log_message(self.log_area, f"Warning: Sound archive '{archive_name}' not found in common game data paths. Skipping.")
                    continue

            log_message(self.log_area, f"Processing sound archive: {archive_path_rel_to_game_root}")
            archive_base_name = os.path.splitext(archive_name)[0] # e.g., "sounds"

            # Define a unique temporary output directory for 'unflat'
            starter_unflat_output_rel = os.path.join("users", "modwork", f"_temp_unflat_sound_{archive_base_name}_{timestamp_prefix}_{get_unique_timestamp_suffix()}")
            starter_unflat_output_abs = os.path.join(current_game_root, starter_unflat_output_rel)
            os.makedirs(os.path.dirname(starter_unflat_output_abs), exist_ok=True)

            log_message(self.log_area, f"  Unpacking '{archive_path_rel_to_game_root}' to game's temp '{starter_unflat_output_rel}'...")
            # Run 'unflat' command
            success, unflat_output_actual_abs = run_starter_command("unflat", [archive_path_rel_to_game_root, starter_unflat_output_rel], self.log_area, timeout=300)

            if not success or not (unflat_output_actual_abs and os.path.isdir(unflat_output_actual_abs)):
                log_message(self.log_area, f"  Failed to unpack sound archive '{archive_name}' or output dir '{unflat_output_actual_abs}' not found. Skipping.")
                if os.path.exists(starter_unflat_output_abs) and self.delete_temp_sound_unflat_var.get():
                    shutil.rmtree(starter_unflat_output_abs) # Clean up temp
                continue

            log_message(self.log_area, f"  Successfully unpacked to '{unflat_output_actual_abs}'. Copying sound files to mod project...")
            # Final destination for this archive's sounds within the mod project
            final_sound_archive_dir_in_project = os.path.join(final_extracted_sounds_base_abs, archive_base_name)
            os.makedirs(final_sound_archive_dir_in_project, exist_ok=True)

            sounds_found_in_archive_count = 0
            # Iterate through unpacked files, copy, and rename .loc_def.sound to .aaf
            for item_name in os.listdir(unflat_output_actual_abs):
                item_path_abs = os.path.join(unflat_output_actual_abs, item_name) # Full path to file in temp unpack dir
                if os.path.isfile(item_path_abs) and any(item_name.lower().endswith(ext) for ext in sound_file_extensions):
                    sounds_found_in_archive_count += 1
                    # Path to copy the sound file to within the mod project
                    dest_sound_file_in_project_abs = os.path.join(final_sound_archive_dir_in_project, item_name)
                    final_item_name_for_list = item_name # Default to original name for listbox

                    try:
                        shutil.copy2(item_path_abs, dest_sound_file_in_project_abs) # Copy to mod project
                        
                        # If the copied file is .loc_def.sound, rename it to .aaf in the mod project
                        if item_name.lower().endswith(".loc_def.sound"):
                            base_name = item_name[:-len(".loc_def.sound")] # Get name without extension
                            new_item_name = base_name + ".aaf" # New name with .aaf extension
                            new_dest_sound_file_in_project_abs = os.path.join(final_sound_archive_dir_in_project, new_item_name)
                            try:
                                # If a file with the new name already exists (e.g. from a previous partial run), remove it.
                                # This handles cases where os.rename might fail (e.g. on Windows due to case differences or if it's a dir).
                                if os.path.exists(new_dest_sound_file_in_project_abs) and \
                                   new_dest_sound_file_in_project_abs != dest_sound_file_in_project_abs : # Ensure not renaming to itself
                                    os.remove(new_dest_sound_file_in_project_abs)

                                os.rename(dest_sound_file_in_project_abs, new_dest_sound_file_in_project_abs)
                                log_message(self.log_area, f"    Renamed '{item_name}' to '{new_item_name}' in project.")
                                final_item_name_for_list = new_item_name # Update name for listbox
                            except Exception as e_rename:
                                log_message(self.log_area, f"    Error renaming {item_name} to {new_item_name}: {e_rename}. Keeping original name.")
                                # If rename fails, final_item_name_for_list remains the original item_name
                        
                        # Add the (potentially renamed) file to the listbox
                        listbox_entry = os.path.join(archive_base_name, final_item_name_for_list)
                        all_extracted_sound_files_for_list.append(listbox_entry)
                        self.extracted_sound_listbox.insert(tk.END, listbox_entry)
                        self.extracted_sound_listbox.see(tk.END)

                    except Exception as e_copy:
                        log_message(self.log_area, f"    Error copying sound file {item_name} to project: {e_copy}")


            if sounds_found_in_archive_count == 0:
                log_message(self.log_area, f"  No recognized sound files (e.g., {', '.join(sound_file_extensions)}) found in unpacked '{unflat_output_actual_abs}'.")
            else:
                log_message(self.log_area, f"  Finished processing {sounds_found_in_archive_count} sound files from '{archive_name}'. Copied to '{final_sound_archive_dir_in_project}'.")

            # Clean up temporary unpack directory if option is checked
            if os.path.exists(starter_unflat_output_abs) and self.delete_temp_sound_unflat_var.get():
                try:
                    shutil.rmtree(starter_unflat_output_abs)
                    log_message(self.log_area, f"  Cleaned up temporary unpack directory: {starter_unflat_output_abs}")
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove game temp unpack dir {starter_unflat_output_abs}: {e}")
            elif os.path.exists(starter_unflat_output_abs): # If not deleting, log that it's kept
                 log_message(self.log_area, f"  Kept temporary unpack directory: {starter_unflat_output_abs}")

            self.root.update_idletasks() # Keep UI responsive

        log_message(self.log_area, "Game sound archive extraction process finished.")
        if not all_extracted_sound_files_for_list:
            log_message(self.log_area, "No sound files were successfully extracted (and renamed if applicable) from the selected archives.")
        else:
            messagebox.showinfo("Extraction Complete", f"Sound archive extraction complete. Check the 'extracted_game_sounds' folder in your Mod Project Directory and the list. .loc_def.sound files have been renamed to .aaf.")


    def save_extracted_texture_list(self):
        """Saves the content of the extracted texture listbox to a text file."""
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
        if not filepath: return # User cancelled
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
        """Saves the content of the extracted sound listbox to a text file."""
        if self.extracted_sound_listbox.size() == 0:
            messagebox.showinfo("No List", "Sound file list is empty. Extract some sound archives first.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Extracted Sound File List As",
            initialdir=current_mod_project_dir or os.getcwd() # Default to mod project dir
        )
        if not filepath: return # User cancelled

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
        """
        Converts selected .texture (ATF) files to .dds format for editing.
        Output is placed in 'ModProjectDir/dds_work/'.
        """
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for ATF to DDS conversion.")
            return
        
        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        # Suggest starting directory for file dialog
        suggested_atf_dir = os.path.join(current_mod_project_dir, "extracted_game_textures", "atf")
        if not os.path.isdir(suggested_atf_dir): # Fallback if not found
            suggested_atf_dir = os.path.join(current_game_root, "data")
        if not os.path.isdir(suggested_atf_dir): # Further fallback
            suggested_atf_dir = current_game_root

        source_atf_files_abs = filedialog.askopenfilenames(
            title="Select .texture (ATF) files to convert for modding",
            initialdir=suggested_atf_dir,
            filetypes=[("Texture files", "*.texture"), ("All files", "*.*")]
        )
        if not source_atf_files_abs: return # User cancelled
        
        output_dds_dir_abs = os.path.join(current_mod_project_dir, "dds_work") # Output to dds_work folder
        log_message(self.log_area, f"Starting ATF to DDS conversion for {len(source_atf_files_abs)} file(s)...")
        success_count = 0
        
        for atf_path_abs in source_atf_files_abs:
            filename = os.path.basename(atf_path_abs)
            base, _ = os.path.splitext(filename)
            dds_filename = base + ".dds"

            # Define temporary output path for DDS within game's user work area
            timestamp_suffix = get_unique_timestamp_suffix()
            temp_dds_output_base_dir_rel = os.path.join("users", "modwork", f"_temp_atf2dds_{timestamp_suffix}")
            os.makedirs(os.path.join(current_game_root, temp_dds_output_base_dir_rel), exist_ok=True)
            temp_dds_output_rel = os.path.join(temp_dds_output_base_dir_rel, dds_filename)
            temp_dds_output_abs = os.path.join(current_game_root, temp_dds_output_rel)

            final_dds_path_abs = os.path.join(output_dds_dir_abs, dds_filename) # Final destination in mod project
            param_atf_path_rel = os.path.relpath(atf_path_abs, current_game_root) # Path relative to game root for starter.exe

            log_message(self.log_area, f"Converting: {param_atf_path_rel} -> temp {temp_dds_output_rel}")
            # Run 'atf2dds' command
            conv_success, _ = run_starter_command("atf2dds", [param_atf_path_rel, temp_dds_output_rel], self.log_area)

            if conv_success and os.path.exists(temp_dds_output_abs):
                try:
                    shutil.move(temp_dds_output_abs, final_dds_path_abs) # Move converted file to mod project
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_dds_path_abs}")
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted DDS {dds_filename} to {output_dds_dir_abs}: {e}")
                    if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs) # Clean up temp if move failed
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp DDS not found at {temp_dds_output_abs}.")
                if os.path.exists(temp_dds_output_abs): os.remove(temp_dds_output_abs) # Clean up if conversion failed but file exists

            # Clean up the temporary base directory used for this conversion
            if os.path.exists(os.path.join(current_game_root, temp_dds_output_base_dir_rel)):
                try:
                    shutil.rmtree(os.path.join(current_game_root, temp_dds_output_base_dir_rel))
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove temp dir {temp_dds_output_base_dir_rel}: {e}")

        log_message(self.log_area, f"ATF to DDS conversion finished. {success_count}/{len(source_atf_files_abs)} successful. DDS files in '{output_dds_dir_abs}'")

    def convert_dds_to_atf_for_modding(self):
        """
        Converts selected .dds files (typically edited by user) back to .texture (ATF) format.
        Output is placed in 'ModProjectDir/prepared_textures/'.
        """
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for DDS to ATF conversion.")
            return
        
        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        # Suggest starting directory for file dialog (user's DDS work folder)
        source_dds_dir_abs = os.path.join(current_mod_project_dir, "dds_work")
        
        source_dds_files_abs = filedialog.askopenfilenames(
            title="Select .dds files from 'dds_work' to convert",
            initialdir=source_dds_dir_abs, # Default to dds_work
            filetypes=[("DDS files", "*.dds"), ("All files", "*.*")]
        )
        if not source_dds_files_abs: return # User cancelled
        
        output_atf_dir_abs = os.path.join(current_mod_project_dir, "prepared_textures") # Output to prepared_textures
        log_message(self.log_area, f"Starting DDS to ATF conversion for {len(source_dds_files_abs)} file(s)...")
        success_count = 0
        
        for dds_path_abs in source_dds_files_abs:
            filename = os.path.basename(dds_path_abs)
            base, _ = os.path.splitext(filename)
            atf_filename = base + ".texture" # Target .texture filename

            # Define temporary output path for ATF within game's user work area
            timestamp_suffix = get_unique_timestamp_suffix()
            temp_atf_output_base_dir_rel = os.path.join("users", "modwork", f"_temp_dds2atf_{timestamp_suffix}")
            os.makedirs(os.path.join(current_game_root, temp_atf_output_base_dir_rel), exist_ok=True)
            temp_atf_output_rel = os.path.join(temp_atf_output_base_dir_rel, atf_filename)
            temp_atf_output_abs = os.path.join(current_game_root, temp_atf_output_rel)

            final_atf_path_abs = os.path.join(output_atf_dir_abs, atf_filename) # Final destination in mod project
            param_dds_path_rel = os.path.relpath(dds_path_abs, current_game_root) # Path relative to game root

            log_message(self.log_area, f"Converting: {param_dds_path_rel} -> temp {temp_atf_output_rel}")
            # Run 'dds2atf' command
            conv_success, _ = run_starter_command("dds2atf", [param_dds_path_rel, temp_atf_output_rel], self.log_area)

            if conv_success and os.path.exists(temp_atf_output_abs):
                try:
                    shutil.move(temp_atf_output_abs, final_atf_path_abs) # Move converted file
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_atf_path_abs}")
                    success_count +=1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted ATF {atf_filename} to {output_atf_dir_abs}: {e}")
                    if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp ATF not found at {temp_atf_output_abs}.")
                if os.path.exists(temp_atf_output_abs): os.remove(temp_atf_output_abs)

            # Clean up temporary base directory
            if os.path.exists(os.path.join(current_game_root, temp_atf_output_base_dir_rel)):
                try:
                    shutil.rmtree(os.path.join(current_game_root, temp_atf_output_base_dir_rel))
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove temp dir {temp_atf_output_base_dir_rel}: {e}")

        log_message(self.log_area, f"DDS to ATF conversion finished. {success_count}/{len(source_dds_files_abs)} successful. Texture files in '{output_atf_dir_abs}'")
        self.load_prepared_assets() # Refresh asset list in packaging tab

    def convert_wav_to_aaf(self):
        """
        Converts selected .wav files to the game's .loc_def.sound format (internally AAF).
        Output is placed in 'ModProjectDir/prepared_sounds/sfx/' or '.../speech/'.
        """
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True):
            log_message(self.log_area, "Failed to initialize mod project folders for WAV to game sound conversion.")
            return

        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        sound_category = self.sound_type_var.get() # SFX or Speech from radio button

        output_subfolder = "sfx" if sound_category == "SFX" else "speech"
        final_output_dir_abs = os.path.join(current_mod_project_dir, "prepared_sounds", output_subfolder)

        # Suggest starting directory for file dialog based on sound category
        suggested_wav_dir = os.path.join(current_mod_project_dir, f"wav_{output_subfolder}_work")
        if not os.path.isdir(suggested_wav_dir): # Fallback
            suggested_wav_dir = current_mod_project_dir

        source_wav_files_abs = filedialog.askopenfilenames(
            title=f"Select .wav files for {sound_category} to .loc_def.sound conversion",
            initialdir=suggested_wav_dir,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if not source_wav_files_abs: return # User cancelled

        log_message(self.log_area, f"Starting WAV to .loc_def.sound ({sound_category}) conversion for {len(source_wav_files_abs)} file(s)...")
        success_count = 0
        for wav_path_abs in source_wav_files_abs:
            filename = os.path.basename(wav_path_abs)
            base, _ = os.path.splitext(filename)
            target_sound_filename = base + ".loc_def.sound" # Game's target extension

            # Define temporary output path for .loc_def.sound within game's user work area
            timestamp_suffix = get_unique_timestamp_suffix()
            temp_output_base_dir_rel = os.path.join("users", "modwork", f"_temp_wav2aaf_{timestamp_suffix}")
            os.makedirs(os.path.join(current_game_root, temp_output_base_dir_rel), exist_ok=True)
            temp_output_filename_rel = os.path.join(temp_output_base_dir_rel, target_sound_filename)
            temp_output_path_abs = os.path.join(current_game_root, temp_output_filename_rel)

            final_sound_path_abs = os.path.join(final_output_dir_abs, target_sound_filename) # Final destination in mod project
            param_wav_path_rel = os.path.relpath(wav_path_abs, current_game_root) # Path relative to game root

            log_message(self.log_area, f"Converting: {param_wav_path_rel} -> temp {temp_output_filename_rel}")
            # Run 'wav2aaf' command
            conv_success, _ = run_starter_command("wav2aaf", [param_wav_path_rel, temp_output_filename_rel], self.log_area)

            if conv_success and os.path.exists(temp_output_path_abs):
                try:
                    shutil.move(temp_output_path_abs, final_sound_path_abs) # Move converted file
                    log_message(self.log_area, f"  Successfully converted and moved to: {final_sound_path_abs}")
                    success_count += 1
                except Exception as e:
                    log_message(self.log_area, f"  Error moving converted sound file {target_sound_filename} to {final_output_dir_abs}: {e}")
                    if os.path.exists(temp_output_path_abs): os.remove(temp_output_path_abs)
            else:
                log_message(self.log_area, f"  Failed to convert {filename} or temp sound file not found at {temp_output_path_abs}.")
                if os.path.exists(temp_output_path_abs): os.remove(temp_output_path_abs)

            # Clean up temporary base directory
            if os.path.exists(os.path.join(current_game_root, temp_output_base_dir_rel)):
                try:
                    shutil.rmtree(os.path.join(current_game_root, temp_output_base_dir_rel))
                except Exception as e:
                    log_message(self.log_area, f"  Warning: Could not remove temp dir {temp_output_base_dir_rel}: {e}")

        log_message(self.log_area, f"WAV to .loc_def.sound ({sound_category}) conversion finished. {success_count}/{len(source_wav_files_abs)} successful. Files in '{final_output_dir_abs}'")
        self.load_prepared_assets() # Refresh asset list in packaging tab

    def load_prepared_assets(self):
        """
        Scans the 'prepared_textures' and 'prepared_sounds' folders in the mod project
        and populates the listbox in the 'Asset Packaging' tab.
        """
        self.packaged_assets_listbox.delete(0, tk.END) # Clear previous list
        current_mod_project_dir = self.mod_project_dir_var.get()
        if not current_mod_project_dir:
            log_message(self.log_area, "Mod Project Directory not set. Cannot load assets.")
            return
        
        total_found = 0
        # Iterate through defined asset types (textures, sounds)
        for asset_type_info in self.asset_types_to_scan:
            asset_dir = os.path.join(current_mod_project_dir, asset_type_info["folder"]) # e.g., .../prepared_textures
            if os.path.isdir(asset_dir):
                count_this_type = 0
                for item in sorted(os.listdir(asset_dir)): # List files in the asset directory
                    if item.lower().endswith(asset_type_info["ext"]): # Check for correct extension
                        self.packaged_assets_listbox.insert(tk.END, f"{asset_type_info['prefix']} {item}") # Add with prefix, e.g., "[TEX] mytexture.texture"
                        count_this_type += 1
                        total_found +=1
                if count_this_type > 0:
                    log_message(self.log_area, f"Found {count_this_type} {asset_type_info['ext']} files in '{asset_type_info['folder']}'.")
        
        if total_found == 0:
            log_message(self.log_area, "No prepared asset files found in expected 'prepared_...' subfolders (textures, sfx, speech).")
        else:
            log_message(self.log_area, f"Total {total_found} prepared asset files loaded. Select files to include in the mod package.")

    def _generate_desc_addpack_file(self, mod_name, author, version, core_dir_abs, game_root_dir):
        """
        Generates the 'desc.addpack' file required for the game to recognize the mod.
        Uses a template from the game's 'docs/modwork/stencil' directory.
        Args:
            mod_name (str): Name of the mod.
            author (str): Author of the mod.
            version (str): Version of the mod (as a string, e.g., "100").
            core_dir_abs (str): Absolute path to the 'CORE' directory in the mod project.
            game_root_dir (str): Absolute path to the game root directory.
        Returns:
            bool: True if successful, False otherwise.
        """
        os.makedirs(core_dir_abs, exist_ok=True) # Ensure CORE directory exists

        # Path to the template desc.addpack.engcfg2 file
        stencil_dir_abs = os.path.join(game_root_dir, "docs", "modwork", "stencil")
        template_filename = "desc_example.addpack.engcfg2" # Standard template name
        template_path_abs = os.path.join(stencil_dir_abs, template_filename)

        if not os.path.exists(template_path_abs):
            log_message(self.log_area, f"Error: Template '{template_filename}' not found at {template_path_abs}")
            messagebox.showerror("Template Missing", f"Addon template '{template_filename}' not found in game docs: {template_path_abs}")
            return False
        
        # Read template content, trying various encodings
        desc_engcfg2_content = None
        encodings_to_try = ['utf-8-sig', 'utf-8', 'windows-1251', 'latin-1']
        for enc in encodings_to_try:
            try:
                with open(template_path_abs, "r", encoding=enc) as f:
                    desc_engcfg2_content = f.read()
                log_message(self.log_area, f"Successfully read template '{template_filename}' with {enc} encoding.")
                break
            except UnicodeDecodeError:
                log_message(self.log_area, f"Warning: Failed to decode template '{template_filename}' with {enc}. Retrying.")
            except Exception as e:
                log_message(self.log_area, f"Warning: Failed to read template '{template_filename}' with {enc}: {e}. Retrying.")
        
        if desc_engcfg2_content is None:
            log_message(self.log_area, f"Critical Error: Could not read/decode template '{template_filename}'.")
            messagebox.showerror("Template Read Error", f"Could not read/decode addon template '{template_filename}'.")
            return False

        # Sanitize mod name for use in file paths (replace invalid characters)
        sanitized_mod_name_for_path = re.sub(r'[^\w\s_-]', '_', mod_name).strip()
        sanitized_mod_name_for_path = re.sub(r'\s+', '_', sanitized_mod_name_for_path)
        if not sanitized_mod_name_for_path: sanitized_mod_name_for_path = "MyMod" # Default if empty

        installer_mod_path = f"mods/{sanitized_mod_name_for_path}" # Path used by game installer
        log_message(self.log_area, f"Setting installer path in desc.addpack to: {installer_mod_path} using Mod Name: '{mod_name}'")

        # Replace placeholders in the template content
        desc_engcfg2_content = desc_engcfg2_content.replace("<my_updates>", installer_mod_path)
        desc_engcfg2_content = desc_engcfg2_content.replace("<My Addon>", mod_name)
        desc_engcfg2_content = desc_engcfg2_content.replace("<Vasya Pupkin>", author)
        desc_engcfg2_content = re.sub(r"version\[u\]\s*=\s*\d+", f"version[u] = {version}", desc_engcfg2_content) # Update version

        # Ensure addon type is set to RES (Resource) if not already a different valid type
        if "type[*] =" not in desc_engcfg2_content:
             desc_engcfg2_content += "\ntype[*] = RES;\n" # Add if missing
        elif "type[*] = ADDN" in desc_engcfg2_content or "type[*] = CAMP" in desc_engcfg2_content:
            pass # Keep ADDN or CAMP if already set
        else: # Change to RES if it's something else unexpected
            desc_engcfg2_content = re.sub(r"type\[\*\]\s*=\s*\w+;", "type[*] = RES;", desc_engcfg2_content)

        # Write modified content to a temporary .engcfg2 file in game's user work area
        timestamp_suffix = get_unique_timestamp_suffix()
        temp_desc_engcfg2_name = f"_temp_desc_{timestamp_suffix}.addpack.engcfg2"
        temp_desc_engcfg2_path_rel = os.path.join("users", "modwork", temp_desc_engcfg2_name)
        temp_desc_engcfg2_path_abs = os.path.join(game_root_dir, temp_desc_engcfg2_path_rel)
        os.makedirs(os.path.dirname(temp_desc_engcfg2_path_abs), exist_ok=True)

        try:
            with open(temp_desc_engcfg2_path_abs, "w", encoding='utf-8') as f:
                f.write(desc_engcfg2_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing temporary desc file '{temp_desc_engcfg2_path_abs}': {e}")
            return False

        # Convert the temporary .engcfg2 file to the binary .addpack format using 'pd2cfgp'
        final_desc_addpack_path_abs = os.path.join(core_dir_abs, "desc.addpack") # Final destination in mod's CORE folder
        temp_desc_addpack_output_name = f"_temp_desc_{timestamp_suffix}.addpack"
        temp_desc_addpack_output_rel = os.path.join("users", "modwork", temp_desc_addpack_output_name)
        temp_desc_addpack_output_abs = os.path.join(game_root_dir, temp_desc_addpack_output_rel)

        log_message(self.log_area, "Generating desc.addpack...")
        gen_success, _ = run_starter_command("pd2cfgp", [temp_desc_engcfg2_path_rel, temp_desc_addpack_output_rel], self.log_area)

        # Clean up temporary .engcfg2 file
        if os.path.exists(temp_desc_engcfg2_path_abs):
            try: os.remove(temp_desc_engcfg2_path_abs)
            except Exception as e_rm: log_message(self.log_area, f"Warning: Could not remove temp file {temp_desc_engcfg2_path_abs}: {e_rm}")

        if not gen_success or not os.path.exists(temp_desc_addpack_output_abs):
            log_message(self.log_area, "Error generating desc.addpack or temp output not found.")
            if os.path.exists(temp_desc_addpack_output_abs): os.remove(temp_desc_addpack_output_abs) # Clean up temp .addpack if it exists
            return False

        # Move the generated .addpack file to the mod's CORE directory
        try:
            os.makedirs(os.path.dirname(final_desc_addpack_path_abs), exist_ok=True)
            shutil.move(temp_desc_addpack_output_abs, final_desc_addpack_path_abs)
            log_message(self.log_area, f"desc.addpack created/updated at {final_desc_addpack_path_abs}")
            return True
        except Exception as e:
            log_message(self.log_area, f"Error moving generated desc.addpack to project: {e}")
            if os.path.exists(temp_desc_addpack_output_abs): os.remove(temp_desc_addpack_output_abs) # Clean up if move fails
            return False

    def _package_asset_archive(self, flatlist_name_stem, mkflat_file_type,
                               files_to_package, game_root_dir, core_dir_abs):
        """
        Packages a list of asset files into a .flatdata archive (e.g., textures.flatdata, sounds.flatdata).
        Args:
            flatlist_name_stem (str): The base name for the archive (e.g., "textures", "sounds").
            mkflat_file_type (str): The type string used by mkflat (e.g., "texture", "sound").
            files_to_package (list of tuples): Each tuple is (absolute_source_path_in_project, staging_filename).
            game_root_dir (str): Absolute path to the game root directory.
            core_dir_abs (str): Absolute path to the 'CORE/shared/packed_data' directory in the mod project.
        Returns:
            bool: True if successful, False otherwise.
        """
        if not files_to_package:
            log_message(self.log_area, f"No files provided for packaging into {flatlist_name_stem}.flatdata. Skipping.")
            return True # Not an error if no files for this specific archive type

        log_message(self.log_area, f"Packaging {len(files_to_package)} assets into {flatlist_name_stem}.flatdata...")

        # Create a temporary staging directory in game's user work area for mkflat
        mkflat_staging_dir_name = f"_mkflat_stage_{flatlist_name_stem}_{get_unique_timestamp_suffix()}"
        mkflat_staging_dir_rel = os.path.join("users", "modwork", mkflat_staging_dir_name)
        mkflat_staging_dir_abs = os.path.join(game_root_dir, mkflat_staging_dir_rel)
        os.makedirs(mkflat_staging_dir_abs, exist_ok=True)

        flatlist_content = "i_unflat:unflat()\n{\n" # Standard flatlist header
        assets_copied_for_mkflat = []

        # Copy selected assets to the staging directory and build the flatlist content
        for abs_src_path_in_project, staging_filename in files_to_package:
            flatlist_entry_name = staging_filename
            # Remove game-specific extensions for the flatlist entry name
            if flatlist_entry_name.lower().endswith(".loc_def.sound"):
                flatlist_entry_name = flatlist_entry_name[:-len(".loc_def.sound")]
            elif flatlist_entry_name.lower().endswith(".texture"):
                flatlist_entry_name = flatlist_entry_name[:-len(".texture")]

            flatlist_content += f"    {flatlist_entry_name}\t, {mkflat_file_type}\t, loc_def ;\n" # Add entry to flatlist

            # Copy asset from mod's 'prepared_...' folder to the staging directory
            dst_asset_for_mkflat_path_abs = os.path.join(mkflat_staging_dir_abs, staging_filename)
            if os.path.exists(abs_src_path_in_project):
                try:
                    shutil.copy2(abs_src_path_in_project, dst_asset_for_mkflat_path_abs)
                    assets_copied_for_mkflat.append(dst_asset_for_mkflat_path_abs)
                except Exception as e:
                    log_message(self.log_area, f"Error copying {staging_filename} from {abs_src_path_in_project} to mkflat staging {dst_asset_for_mkflat_path_abs}: {e}")
                    if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs) # Clean up staging on error
                    return False
            else:
                log_message(self.log_area, f"Warning: Source asset {abs_src_path_in_project} not found for copying. Skipping this file for {flatlist_name_stem}.flatdata.")
                continue # Skip this file but continue with others

        if not assets_copied_for_mkflat: # If no valid files ended up being copied
            log_message(self.log_area, f"No valid asset files were found to copy for {flatlist_name_stem}.flatdata. Skipping archive creation.")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return True # Not an error, just nothing to package for this type

        flatlist_content += "}\n" # Close flatlist structure
        flatlist_filename_for_mkflat = f"{flatlist_name_stem}.!flatlist" # e.g., textures.!flatlist
        flatlist_path_in_staging_abs = os.path.join(mkflat_staging_dir_abs, flatlist_filename_for_mkflat)
        flatlist_path_in_staging_rel = os.path.relpath(flatlist_path_in_staging_abs, game_root_dir) # Relative path for mkflat

        # Write the .!flatlist file to the staging directory
        try:
            with open(flatlist_path_in_staging_abs, "w", encoding='utf-8') as f:
                f.write(flatlist_content)
        except Exception as e:
            log_message(self.log_area, f"Error writing {flatlist_filename_for_mkflat} to staging: {e}")
            if os.path.exists(mkflat_staging_dir_abs): shutil.rmtree(mkflat_staging_dir_abs)
            return False

        # Define output path for .flatdata archive in staging and final destination in mod project
        flatdata_output_in_staging_rel = os.path.join(mkflat_staging_dir_rel, f"{flatlist_name_stem}.flatdata")
        flatdata_output_in_staging_abs = os.path.join(game_root_dir, flatdata_output_in_staging_rel)
        final_flatdata_target_in_project_abs = os.path.join(core_dir_abs, "shared", "packed_data", f"{flatlist_name_stem}.flatdata")

        # Run 'mkflat' command to create the .flatdata archive
        mk_success, _ = run_starter_command("mkflat", [flatdata_output_in_staging_rel, flatlist_path_in_staging_rel], self.log_area)

        if not mk_success or not os.path.exists(flatdata_output_in_staging_abs):
            log_message(self.log_area, f"Error generating {flatlist_name_stem}.flatdata or output not found in staging at {flatdata_output_in_staging_abs}.")
            # Staging dir cleaned up in finally block
            return False

        # Move the generated .flatdata archive to the mod's CORE/shared/packed_data directory
        try:
            os.makedirs(os.path.dirname(final_flatdata_target_in_project_abs), exist_ok=True)
            shutil.move(flatdata_output_in_staging_abs, final_flatdata_target_in_project_abs)
            log_message(self.log_area, f"{flatlist_name_stem}.flatdata created at {final_flatdata_target_in_project_abs}")
            return True
        except Exception as e:
            log_message(self.log_area, f"Error moving generated {flatlist_name_stem}.flatdata to project: {e}")
            return False
        finally:
            # Always clean up the mkflat staging directory
            if os.path.exists(mkflat_staging_dir_abs):
                try:
                    shutil.rmtree(mkflat_staging_dir_abs)
                    log_message(self.log_area, f"Cleaned up mkflat staging for {flatlist_name_stem}: {mkflat_staging_dir_abs}")
                except Exception as e:
                    log_message(self.log_area, f"Warning: Could not remove mkflat staging for {flatlist_name_stem}: {e}")

    def generate_mod_files(self):
        """
        Orchestrates the generation of all mod files:
        1. Confirms mod details (name, author, version) with the user.
        2. Updates/creates readme.txt.
        3. Generates desc.addpack.
        4. Packages selected assets from 'prepared_...' folders into .flatdata archives.
        """
        if not self._validate_paths(check_mod_project=True): return
        if not self.initialize_mod_folders(silent=True): # Ensure project structure is ready
            log_message(self.log_area, "Failed to initialize mod project folders for packaging.")
            return

        # --- Confirm Mod Details First ---
        # This dialog updates self.mod_name_var, etc., directly if confirmed.
        log_message(self.log_area, "Requesting confirmation of Mod Details before generating files...")
        confirmed_details = self._confirm_mod_details_dialog(
            title="Confirm/Edit Mod Details for File Generation",
            confirm_button_text="Confirm & Generate Files"
        )

        if not confirmed_details: # User cancelled the dialog
            log_message(self.log_area, "Mod file generation cancelled by user at detail confirmation step.")
            return
        log_message(self.log_area, "Mod details confirmed. Proceeding with file generation.")

        # Get the confirmed/edited details from the UI StringVars
        mod_name_val = self.mod_name_var.get()
        mod_author_val = self.mod_author_var.get()
        mod_version_val = self.mod_version_var.get()

        # Update readme.txt with the confirmed mod information
        if not self._update_readme_file():
            log_message(self.log_area, "Warning: Failed to update readme.txt with confirmed details. Proceeding with other file generation.")
            # Optionally, could ask user to proceed if readme is critical, but for now, continue.

        # Get selected assets from the listbox
        selected_indices = self.packaged_assets_listbox.curselection()
        selected_asset_filenames_with_prefix = [self.packaged_assets_listbox.get(i) for i in selected_indices]

        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get()
        core_dir_abs = os.path.join(current_mod_project_dir, "CORE") # Base for installable mod files
        os.makedirs(core_dir_abs, exist_ok=True)

        # Generate desc.addpack using the confirmed details
        if not self._generate_desc_addpack_file(mod_name_val, mod_author_val, mod_version_val, core_dir_abs, current_game_root):
            messagebox.showerror("Error", "Failed to generate desc.addpack. Check log.")
            return

        all_archives_successful = True
        archives_packaged_count = 0

        # If no assets are selected, only desc.addpack and readme.txt are generated/updated.
        if not selected_asset_filenames_with_prefix:
            log_message(self.log_area, "desc.addpack and readme.txt updated with confirmed details. No assets were selected for .flatdata archives.")
            messagebox.showinfo("Files Generated", "desc.addpack and readme.txt updated with confirmed details. No assets were selected to package into .flatdata archives.")
            return

        # Iterate through asset types (textures, sounds) to package them into respective .flatdata archives
        for flatlist_stem, definition in self.flatdata_definitions.items(): # e.g., "textures", "sounds"
            mkflat_type = definition["mkflat_type"] # "texture" or "sound"
            files_for_this_flatdata_archive = [] # List of (source_path, staging_filename)

            # Gather files for the current archive type (e.g., all selected .texture files)
            for source_config in definition["sources"]: # e.g., config for prepared_textures
                prefix_to_match = source_config["prefix"] + " " # e.g., "[TEX] "
                source_folder_abs_in_project = os.path.join(current_mod_project_dir, source_config["folder"])

                for selected_file_with_prefix in selected_asset_filenames_with_prefix:
                    if selected_file_with_prefix.startswith(prefix_to_match):
                        asset_filename = selected_file_with_prefix.split(prefix_to_match, 1)[1] # Get filename without prefix
                        original_asset_path_abs_in_project = os.path.join(source_folder_abs_in_project, asset_filename)

                        if os.path.exists(original_asset_path_abs_in_project):
                            files_for_this_flatdata_archive.append(
                                (original_asset_path_abs_in_project, asset_filename) # Store full source path and base filename
                            )
                        else:
                            log_message(self.log_area, f"Warning: Selected asset '{asset_filename}' not found at '{original_asset_path_abs_in_project}'. Skipping for {flatlist_stem}.flatdata.")
                            all_archives_successful = False # Mark as not entirely successful

            # If there are files to package for this archive type, call _package_asset_archive
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

        # Provide feedback to the user based on the outcome
        if archives_packaged_count == 0 and any(selected_asset_filenames_with_prefix):
             log_message(self.log_area, "desc.addpack and readme.txt updated. However, no asset archives were created. This might be due to missing source files or incorrect prefixes for selected items.")
             messagebox.showwarning("Packaging Issue", "desc.addpack and readme.txt updated. No .flatdata archives were created. Check log for details on missing files or prefix mismatches.")
        elif all_archives_successful and archives_packaged_count > 0:
            log_message(self.log_area, "All selected mod files generated successfully in CORE directory (including updated desc.addpack and readme.txt).")
            messagebox.showinfo("Success", "Mod files (desc.addpack, readme.txt, and selected .flatdata archives) generated successfully with confirmed details!")
        elif archives_packaged_count > 0 : # Some archives made, but not all operations were perfect
            log_message(self.log_area, "desc.addpack and readme.txt updated. Some .flatdata archives generated, but errors occurred with others (e.g., missing files). Check log.")
            messagebox.showwarning("Partial Success", "desc.addpack and readme.txt updated. Some .flatdata archives generated, but errors occurred. Check log for details.")
        elif not all_archives_successful and archives_packaged_count == 0 and any(selected_asset_filenames_with_prefix):
            log_message(self.log_area, "desc.addpack and readme.txt updated, but failed to generate any .flatdata archives due to errors (e.g. all selected files missing). Check log.")
            messagebox.showerror("Error", "desc.addpack and readme.txt updated, but failed to create any .flatdata archives. Check log for details.")

    def _confirm_mod_details_dialog(self, title="Confirm Mod Details", confirm_button_text="Confirm"):
        """
        Displays a modal dialog for the user to confirm or edit mod details (name, author, version).
        Updates the main application's StringVars (self.mod_name_var, etc.) if confirmed.
        Args:
            title (str): The title for the dialog window.
            confirm_button_text (str): Text for the confirm button.
        Returns:
            bool: True if the user confirmed, False if cancelled or closed.
        """
        self.confirmation_result = False # Reset result before showing dialog

        dialog = tk.Toplevel(self.root) # Create a new top-level window
        dialog.title(title)
        dialog.transient(self.root) # Set as transient to the main window
        dialog.grab_set() # Make it modal (blocks interaction with main window)
        dialog.resizable(False, False)
        dialog.attributes("-toolwindow", True) # Simple window style

        main_frame = ttk.Frame(dialog, padding="15 15 15 15")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text="Please review and confirm/edit the following mod details:",
                  wraplength=380, justify=tk.LEFT).grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")

        details_frame = ttk.Frame(main_frame)
        details_frame.grid(row=1, column=0, columnspan=2, pady=(0,15), sticky="ew")

        # Use temporary StringVars for the dialog to avoid affecting main UI vars unless confirmed
        dialog_mod_name_var = tk.StringVar(value=self.mod_name_var.get())
        dialog_mod_author_var = tk.StringVar(value=self.mod_author_var.get())
        dialog_mod_version_var = tk.StringVar(value=self.mod_version_var.get())

        # Mod Name Entry
        ttk.Label(details_frame, text="Mod Name:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=3, sticky="e")
        mod_name_entry = ttk.Entry(details_frame, textvariable=dialog_mod_name_var, width=40)
        mod_name_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")

        # Author Entry
        ttk.Label(details_frame, text="Author:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, padx=5, pady=3, sticky="e")
        mod_author_entry = ttk.Entry(details_frame, textvariable=dialog_mod_author_var, width=40)
        mod_author_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")

        # Version Entry
        ttk.Label(details_frame, text="Version:", font=("Segoe UI", 9, "bold")).grid(row=2, column=0, padx=5, pady=3, sticky="e")
        mod_version_entry = ttk.Entry(details_frame, textvariable=dialog_mod_version_var, width=15)
        mod_version_entry.grid(row=2, column=1, padx=5, pady=3, sticky="w")

        details_frame.grid_columnconfigure(1, weight=1) # Allow entry fields to expand

        # --- Dialog Actions ---
        def on_confirm():
            # Update the main application's StringVars with values from the dialog
            self.mod_name_var.set(dialog_mod_name_var.get() or "MyMod") # Use default if empty
            self.mod_author_var.set(dialog_mod_author_var.get() or "Modder")
            self.mod_version_var.set(dialog_mod_version_var.get() or "100")
            log_message(self.log_area, f"Mod details confirmed/updated in UI: Name='{self.mod_name_var.get()}', Author='{self.mod_author_var.get()}', Version='{self.mod_version_var.get()}'")
            self.confirmation_result = True
            dialog.destroy()

        def on_cancel():
            self.confirmation_result = False
            dialog.destroy()

        # --- Dialog Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="e") # Align right

        confirm_button = ttk.Button(button_frame, text=confirm_button_text, command=on_confirm, style="Accent.TButton")
        confirm_button.pack(side=tk.RIGHT, padx=(10,0))
        ToolTip(confirm_button, "Proceed using these details.")

        cancel_button = ttk.Button(button_frame, text="Cancel", command=on_cancel)
        cancel_button.pack(side=tk.RIGHT, padx=(0,5))
        ToolTip(cancel_button, "Cancel this operation.")

        # Style for the confirm button
        s = ttk.Style()
        s.configure("Accent.TButton", font=("Segoe UI", 9, "bold"))

        dialog.protocol("WM_DELETE_WINDOW", on_cancel) # Handle window close button
        mod_name_entry.focus_set() # Set focus to the first entry field

        # Center the dialog on the parent window or screen
        dialog.update_idletasks() # Ensure dimensions are calculated
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()

        # Check if parent window might be minimized or off-screen
        if parent_width < dialog_width or parent_height < dialog_height or parent_x < 0 or parent_y < 0:
            # Center on screen if parent is not suitable
            x = (self.root.winfo_screenwidth() // 2) - (dialog_width // 2)
            y = (self.root.winfo_screenheight() // 2) - (dialog_height // 2)
        else:
            # Center on parent
            x = parent_x + (parent_width // 2) - (dialog_width // 2)
            y = parent_y + (parent_height // 2) - (dialog_height // 2)
        dialog.geometry(f'{dialog_width}x{dialog_height}+{x}+{y}')

        self.root.wait_window(dialog) # Wait for the dialog to be closed
        return self.confirmation_result

    def create_mod_archive(self):
        """
        Packages the mod files (CORE folder and readme.txt) into a .gt2extension archive (a renamed .zip file).
        Assumes mod details have been set/confirmed via 'Generate Mod Files' step.
        """
        if not self._validate_paths(check_mod_project=True, check_starter=False): return # Starter not needed for zipping

        # Get current mod details from UI (should be up-to-date from generate_mod_files confirmation)
        current_mod_name = self.mod_name_var.get()
        current_mod_author = self.mod_author_var.get()
        current_mod_version = self.mod_version_var.get()
        current_mod_project_dir = self.mod_project_dir_var.get()
        current_game_root = self.game_root_var.get() # Needed for _generate_desc_addpack_file
        core_dir_abs = os.path.join(current_mod_project_dir, "CORE")

        # Ensure essential mod details are present
        if not all([current_mod_name, current_mod_author, current_mod_version]):
            messagebox.showerror("Error", "Mod Name, Author, and Version must be set in the 'Project Setup' tab. Please use 'Generate Mod Files' to set/confirm them first.")
            log_message(self.log_area, "Error: Mod Name, Author, or Version not set. Cannot create archive.")
            return

        log_message(self.log_area, f"Creating archive with details: Name='{current_mod_name}', Author='{current_mod_author}', Version='{current_mod_version}'")

        # Crucially, re-generate desc.addpack and readme.txt to ensure they reflect the *absolute latest* UI values
        # before packaging. This makes this step self-contained regarding these two files.
        log_message(self.log_area, "Ensuring desc.addpack is up-to-date for archive...")
        if not self._generate_desc_addpack_file(current_mod_name, current_mod_author, current_mod_version, core_dir_abs, current_game_root):
            messagebox.showerror("Error", "Failed to update desc.addpack with current details. Archive creation aborted. Check log.")
            log_message(self.log_area, "Failed to update desc.addpack. Archive creation aborted.")
            return

        log_message(self.log_area, "Ensuring readme.txt is up-to-date for archive...")
        if not self._update_readme_file(): # This uses the main UI StringVars
            messagebox.showerror("Readme Error", "Failed to update readme.txt with current details. Archive creation aborted. Check log.")
            log_message(self.log_area, "Failed to update readme.txt. Archive creation aborted.")
            return

        # Sanitize mod name for the archive filename
        mod_name_for_archive = re.sub(r'[^\w\s_-]', '_', current_mod_name).strip()
        mod_name_for_archive = re.sub(r'\s+', '_', mod_name_for_archive)
        if not mod_name_for_archive: mod_name_for_archive = "MyMod" # Default filename part

        readme_file_to_archive = os.path.join(current_mod_project_dir, "readme.txt")

        # Check if CORE directory and desc.addpack exist (should have been created by generate_mod_files)
        if not os.path.isdir(core_dir_abs) or not os.path.exists(os.path.join(core_dir_abs,"desc.addpack")):
            messagebox.showerror("Error", "CORE directory or desc.addpack not found. Please run 'Generate Mod Files' first. Archive creation aborted.")
            log_message(self.log_area, "Error: CORE/desc.addpack not found. Archive creation aborted.")
            return

        # Suggest save location for the archive (one level up from mod project dir)
        initial_save_dir = os.path.dirname(current_mod_project_dir) if current_mod_project_dir and os.path.dirname(current_mod_project_dir) else (current_mod_project_dir or os.getcwd())

        archive_save_path = filedialog.asksaveasfilename(
            title="Save Mod Archive As",
            initialdir=initial_save_dir,
            initialfile=f"{mod_name_for_archive}.gt2extension", # Suggested filename
            defaultextension=".gt2extension",
            filetypes=[("Graviteam Mod Archive", "*.gt2extension"), ("Zip files", "*.zip")]
        )

        if not archive_save_path: # User cancelled
            log_message(self.log_area, "Mod archive creation cancelled (file save dialog).")
            return

        # Ensure the extension is .gt2extension (even if user typed .zip)
        if not archive_save_path.lower().endswith(".gt2extension"):
            archive_save_path = os.path.splitext(archive_save_path)[0] + ".gt2extension"

        # Use a temporary name for shutil.make_archive to avoid issues with existing files
        temp_zip_base_name = os.path.join(os.path.dirname(archive_save_path), f"_temp_archive_{get_unique_timestamp_suffix()}")

        staging_dir = None # Temporary directory to gather files for zipping
        created_zip_file_path = None # Path to the zip file created by make_archive

        try:
            # Create a temporary staging directory within the mod project
            staging_dir = os.path.join(current_mod_project_dir, f"_archive_staging_{get_unique_timestamp_suffix()}")
            if os.path.exists(staging_dir): shutil.rmtree(staging_dir) # Clean up if exists from previous attempt
            os.makedirs(staging_dir)

            # Copy CORE folder and readme.txt to the staging directory
            shutil.copytree(core_dir_abs, os.path.join(staging_dir, "CORE"))
            if os.path.exists(readme_file_to_archive):
                shutil.copy2(readme_file_to_archive, os.path.join(staging_dir, "readme.txt"))
            else:
                log_message(self.log_area, "Warning: readme.txt was not found in project dir during packaging.")

            # Create the zip archive from the staging directory content
            created_zip_file_path = shutil.make_archive(base_name=temp_zip_base_name,
                                                        format='zip',
                                                        root_dir=staging_dir) # Zip content of staging_dir

            # Move the created .zip to the final .gt2extension path
            if os.path.exists(archive_save_path): # Remove if target already exists
                os.remove(archive_save_path)
            shutil.move(created_zip_file_path, archive_save_path)

            log_message(self.log_area, f"Mod archive created: {archive_save_path}")
            messagebox.showinfo("Success", f"Mod archive (.gt2extension) created:\n{archive_save_path}")

        except Exception as e:
            log_message(self.log_area, f"Error creating mod archive: {e}")
            messagebox.showerror("Error", f"Error creating mod archive: {e}")
        finally:
            # Clean up the staging directory
            if staging_dir and os.path.exists(staging_dir):
                try:
                    shutil.rmtree(staging_dir)
                    log_message(self.log_area, f"Cleaned up staging directory: {staging_dir}")
                except Exception as e_rm:
                    log_message(self.log_area, f"Warning: Could not remove staging directory {staging_dir}: {e_rm}")

            # Clean up the temporary zip file if it wasn't moved (e.g., if move failed or it's a different path)
            if created_zip_file_path and os.path.exists(created_zip_file_path) and created_zip_file_path != archive_save_path:
                try:
                    os.remove(created_zip_file_path)
                    log_message(self.log_area, f"Cleaned up temporary zip file: {created_zip_file_path}")
                except Exception as e_rm_zip:
                    log_message(self.log_area, f"Warning: Could not remove temporary zip file {created_zip_file_path}: {e_rm_zip}")


# --- Main Application Execution ---
app = None # Global reference to the application instance
if __name__ == "__main__":
    root = tk.Tk()
    app = TextureModTool(root) # Create the application instance
    root.mainloop() # Start the Tkinter event loop
