PI:
python3 /home/pi/camera_capture_local.py

KI:
python3 /home/edv/Desktop/pull_pi_camera_images.py

und

cd /home/edv/Desktop/yolo_gauge_reader

/home/edv/.local/share/pipx/venvs/ultralytics/bin/python live_camera_reader.py \
  --camera-config /home/edv/Desktop/yolo_gauge_reader/camera_profiles.json \
  --output /home/edv/Desktop/Manometer_Live_Auswertung \
  --stage1-model /home/edv/Desktop/yolo_runs/gauge_yolo26n_good_b32/weights/best.pt \
  --stage2-model /home/edv/Desktop/yolo_runs/gauge_crop_yolo26s_full_b32/weights/best.pt \
  --interval-seconds 5 \
  --max-images-per-camera 10
