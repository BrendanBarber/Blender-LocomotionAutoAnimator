import bpy
import addon_utils
import os
import sys
import shutil


def load_config():
    """Load configuration from config.yml using simple text parsing"""
    config = {}
    try:
        with open('config.yml', 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#') and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')  # Remove quotes
                    config[key] = value
        return config
    except Exception as e:
        print(f"Error loading config.yml: {e}")
        sys.exit(1)

def find_addon_module(addon_name):
    """Find the addon module name"""
    for mod in addon_utils.modules():
        if mod.__name__ == addon_name or mod.__name__.endswith(addon_name):
            return mod.__name__
    return addon_name

def main():
    # Load configuration
    config = load_config()

    addon_name = config.get('addon_name')
    zip_path = config.get('output_zip', f"{config.get('addon_folder', '')}.zip")

    if not addon_name:
        print(f"ERROR: {addon_name} not found in config.yml")
        sys.exit(1)

    zip_path = os.path.abspath(zip_path)

    print("Starting addon update...")
    print(f"Addon name: {addon_name}")
    print(f"Zip path: {zip_path}")

    addon_dir = bpy.utils.user_resource('SCRIPTS', path="addons")
    addon_path = os.path.join(addon_dir, addon_name)

    print(f"Addon directory: {addon_dir}")
    print(f"Full addon path: {addon_path}")

    found_addon_name = find_addon_module(addon_name)
    if found_addon_name != addon_name:
        print(f"Found addon module: {found_addon_name}")
        addon_name = found_addon_name
    else:
        print(f"Using addon name: {addon_name}")

    print(f"Checking if addon is enabled: {addon_name}")
    if addon_name in bpy.context.preferences.addons.keys():
        print(f"Disabling addon: {addon_name}")
        try:
            bpy.ops.preferences.addon_disable(module=addon_name)
            print("Addon disabled successfully")
        except Exception as e:
            print(f"Error disabling addon: {e}")
    else:
        print(f"Addon {addon_name} not currently enabled")

    bpy.ops.preferences.addon_refresh()

    # Install updated addon
    print(f"Installing addon from: {zip_path}")

    if not os.path.exists(zip_path):
        print(f"ERROR: Zip file not found: {zip_path}")
        sys.exit(1)

    try:
        # Install the addon
        bpy.ops.preferences.addon_install(filepath=zip_path, overwrite=True)
        print("Addon installed successfully")

        bpy.ops.preferences.addon_refresh()

    except Exception as e:
        print(f"Error installing addon: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("Addon management completed successfully!")


if __name__ == "__main__":
    main()