import json

config_path = "/home/daan/Documents/thesis/engineering/coding/ring_milling_app/resources/config.json"

with open(config_path, "r") as f:
    config = json.load(f)

camera_index = config["camera_index"]
save_dir = config["save_code_directory"]
prev_points_dir = config["previous_points_directory"]
std_save_flag = config["standard_save_flag"]
camera_rot_idx = config["rotate_index"]
