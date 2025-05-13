# Gravitool - User Manual - Currently Only Supports GTOS

Welcome to the Graviteam Asset Mod Tool! This guide will help you get started with extracting game assets, preparing your own modded assets, and packaging them into a distributable mod.

## 1. Getting Started: Project Setup

This is the first and most crucial step. The tool needs to know where your game is installed and where your mod project files will be stored.

**Tab: 1. Project Setup**

1.  **Set Game Root Directory:**
    * Click "Browse" next to "Game Root:".
    * Navigate to and select the main installation folder of your Graviteam game (e.g., the folder containing `starter.exe`).
    * The tool will try to find `starter.exe` here. This file is essential for many of the tool's functions.

2.  **Set Mod Project Directory:**
    * Click "Browse/Create" next to "Mod Project Dir:".
    * Choose an existing empty folder or navigate to where you want to create a new folder for your mod project. This is where all your work-in-progress files, extracted assets, and prepared mod files will be stored.
    * *Suggestion:* A good place might be `[YourGameRoot]\users\modwork\[YourModName]\`.

3.  **Mod Information:**
    * **Mod Name:** Enter the name of your mod (e.g., "My Awesome Tank Reskin"). This will be used in the `desc.addpack` file and the `readme.txt`.
    * **Author:** Your name or modding alias.
    * **Version:** The version of your mod (e.g., "100" for v1.00, "101" for v1.01).

4.  **Initialize/Verify Mod Project Folders:**
    * Once your Game Root and Mod Project Directory are set, click this button.
    * The tool will create a standard set of subfolders within your Mod Project Directory (like `dds_work`, `prepared_textures`, `prepared_sounds`, `CORE`, etc.) if they don't already exist. It will also create a basic `readme.txt` file.

**Important:**
* The Game Root and Mod Project Directory paths are saved automatically when you select them.
* You can change these paths anytime via the "File" menu.

## 2. Extracting Game Assets

To mod existing game assets (like textures or sounds), you first need to extract them from the game's archives.

**Tab: 2. Asset Extractor**

This tab has two sub-tabs: "Texture Extractor" and "Sound Extractor".

### 2.1 Texture Extractor

1.  **Select Game Texture Archives:**
    * Check the boxes next to the game's texture archives (`.flatdata` files) you want to extract. Common ones like `tex_main.flatdata` and `tex_objects.flatdata` are good starting points.
2.  **Optional: Delete original .texture files...:**
    * If checked (default), the original `.texture` (ATF) files will be deleted from your mod project's `extracted_game_textures/atf/` folder *after* they are successfully converted to `.dds`. This saves space. The `.dds` files will remain in `extracted_game_textures/dds/`.
3.  **Unpack Selected Texture Archives & Convert to DDS:**
    * Click this button.
    * **A popup will appear warning you that this process might take several minutes.** The tool may appear unresponsive. Please be patient.
    * The tool will:
        * Use `starter.exe` to unpack the selected `.flatdata` archives.
        * Copy the original `.texture` (ATF) files to `[YourModProjectDir]/extracted_game_textures/atf/[archive_name]/`.
        * Convert these `.texture` files to `.dds` format (which you can edit) and save them to `[YourModProjectDir]/extracted_game_textures/dds/[archive_name]/`.
4.  **Extracted Texture List:**
    * Successfully extracted and converted `.dds` files will be listed here, showing their path relative to the `extracted_game_textures/dds/` folder.
5.  **Save Texture List to File:**
    * Saves the current list of extracted textures to a `.txt` file for your reference.

### 2.2 Sound Extractor (SFX/Speech)

1.  **Select Game Sound Archives:**
    * Check the boxes next to the game's sound archives you want to extract (e.g., `sounds.flatdata`, `speech_eng.flatdata`).
2.  **Optional: Delete temporary unpack folders...:**
    * If checked (default), temporary folders created by `starter.exe` during unpacking (usually in your game's `users/modwork/` folder) will be deleted after the files are copied to your mod project.
3.  **Unpack Selected Sound Archives (and convert .loc_def.sound to .aaf):**
    * Click this button.
    * The tool will:
        * Unpack the selected sound `.flatdata` archives.
        * Copy the sound files to `[YourModProjectDir]/extracted_game_sounds/[archive_name]/`.
        * **Important:** Files with the `.loc_def.sound` extension will be automatically renamed to `.aaf` in your mod project directory.
4.  **Extracted Sound File List:**
    * Successfully extracted sound files (including the renamed `.aaf` files) will be listed here.
5.  **Save Sound List to File:**
    * Saves the current list of extracted sound files to a `.txt` file.

## 3. Modifying Textures

Once you have `.dds` files (either extracted from the game or your own), you can edit them. Then, you'll need to convert them back to the game's `.texture` (ATF) format.

**Tab: 3. Mod Texture Conversion**

* **Workflow:**
    1.  Find a game texture you want to edit from your `[ModProjectDir]/extracted_game_textures/dds/` folder.
    2.  Copy it to your `[ModProjectDir]/dds_work/` folder.
    3.  Edit the `.dds` file in `dds_work/` using an image editor that supports DDS (like Paint.NET with a DDS plugin, GIMP with a DDS plugin, or Photoshop with NVIDIA's DDS plugin). **Do not change the image dimensions or DXT format unless you know what you are doing.**
    4.  Once edited, use the tool to convert it back to `.texture`.

* **Convert Game .texture (ATF) to .dds (for editing):**
    * Use this if you have a `.texture` file from somewhere else (not extracted via Tab 2) and want to convert it to `.dds`.
    * Select one or more `.texture` files.
    * The output `.dds` files will be saved in `[ModProjectDir]/dds_work/`.

* **Convert Edited .dds to Game .texture (ATF):**
    * This is the main function you'll use after editing your textures.
    * Select one or more `.dds` files (usually from your `dds_work/` folder).
    * The output `.texture` files will be saved in `[ModProjectDir]/prepared_textures/`. These are the files that will be packaged into your mod.

## 4. Modifying Sounds (SFX/Speech)

To add new or replace existing sounds, you'll typically start with `.wav` files. These need to be converted to the game's `.loc_def.sound` format.

**Tab: 4. Sound Modding (SFX/Speech)**

* **Input .wav format:**
    * Your `.wav` files should be **44.1kHz, 16-bit**.
    * Use **Mono** for 3D sound effects (SFX) like explosions, vehicle sounds.
    * Use **Stereo** for UI sounds or system sounds.

1.  **Output Type:**
    * Select "SFX" if your sound is a general sound effect. It will be prepared for the `prepared_sounds/sfx/` folder.
    * Select "Speech" if your sound is a voice line. It will be prepared for the `prepared_sounds/speech/` folder.
2.  **Select .wav File(s) and Convert to .loc_def.sound:**
    * Click this button and select your `.wav` file(s).
    * The tool will use `starter.exe wav2aaf` to convert them.
    * The output `.loc_def.sound` files will be saved in the appropriate subfolder of `[ModProjectDir]/prepared_sounds/` (either `sfx/` or `speech/`).

## 5. Packaging Your Mod

Once you have prepared all your modded assets (textures in `prepared_textures/`, sounds in `prepared_sounds/sfx/` or `prepared_sounds/speech/`), you can package them into a mod.

**Tab: 5. Asset Packaging**

1.  **Refresh List from 'prepared_...' folders:**
    * Click this button to scan your `prepared_textures` and `prepared_sounds` folders.
    * Any valid assets found (e.g., `.texture` files, `.loc_def.sound` files) will appear in the listbox below, prefixed with `[TEX]`, `[SFX]`, or `[SPE]`.
2.  **Select asset files...to include in mod:**
    * From the list, select all the asset files you want to include in this version of your mod. You can select multiple files.
3.  **1. Generate Mod Files (desc.addpack & .flatdata archives):**
    * Click this button.
    * **Confirm Mod Details:** A dialog will pop up asking you to confirm or edit the Mod Name, Author, and Version (these are taken from Tab 1 but can be overridden here for this specific packaging step). Click "Confirm & Generate Files".
    * The tool will then:
        * Create/update `readme.txt` in your mod project root with the confirmed details.
        * Create/update `desc.addpack` in `[ModProjectDir]/CORE/` with the confirmed details. This file tells the game how to install your mod.
        * For the assets you selected in the listbox:
            * It will create the necessary `.flatdata` archives (e.g., `textures.flatdata`, `sounds.flatdata`) containing your selected modded assets.
            * These archives will be placed in `[ModProjectDir]/CORE/shared/packed_data/`.
4.  **2. Create .gt2extension Mod Archive:**
    * After successfully generating the mod files (Step 3), click this button.
    * The tool will take the entire `CORE` folder (containing `desc.addpack` and your `.flatdata` archives) and the `readme.txt` from your mod project root.
    * It will package them into a single `.gt2extension` file (which is essentially a `.zip` file).
    * You will be prompted where to save this `.gt2extension` file. This is the file you distribute to others to install your mod.

**Log Window:**
* At the bottom of the tool, there's a Log window. It displays messages about what the tool is doing, including any errors or warnings. Check this if something doesn't seem to work as expected.

## Disclaimer

GraviTool is an unofficial third-party tool designed to be used with Graviteam Tactics:Operation Star (GTOS) series games and their accompanying modding utilities (e.g., `starter.exe`).

* You must own a legitimate copy of the relevant Graviteam game to use this tool effectively with game assets.
* This tool does not distribute any copyrighted game files or proprietary game utilities.
* The use of Graviteam's `starter.exe` and other game assets is subject to Graviteam's End User License Agreement (EULA) and terms of service. Users are responsible for complying with these terms.
* The GraviTool is provided "as is", without warranty of any kind. The author is not responsible for any damage or issues that may arise from its use.

That's it! You now have a basic understanding of how to use Gravitool. Happy modding!
