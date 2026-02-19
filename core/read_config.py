import json

config_path = "/home/daan/Documents/thesis/engineering/coding/ring_milling_app/resources/config.json"

with open(config_path, "r") as f:
    config = json.load(f)

camera_index = config["camera_index"]
save_dir = config["save_code_directory"]
cal_dir = config["calibration_directory"]
prev_points_dir = config["previous_points_directory"]
std_save_flag = config["standard_save_flag"]
pix2mm_conversion = config["pixel2mm"]
