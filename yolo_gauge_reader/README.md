# YOLO Gauge Reader

Zweistufiges Ausleseprogramm für deine sortierten und kalibrierten Manometerbilder.

## Pipeline

```text
Originalbild
  -> Stage 1 YOLO erkennt gauge
  -> Gauge-Crop wird erzeugt
  -> Stage 2 YOLO erkennt center, max, min, tip
  -> Winkel center -> tip
  -> Wert über gauge_profile.json
  -> readings.csv + Overlay-Bilder
```

## Start

Da Ultralytics bei dir über pipx installiert ist, nutze am besten den pipx-Python:

```bash
/home/edv/.local/share/pipx/venvs/ultralytics/bin/python main.py \
  --input /home/edv/Desktop/Werkfotos_Sortiert \
  --output /home/edv/Desktop/Manometer_YOLO_Auswertung \
  --stage1-model /home/edv/Desktop/yolo_runs/gauge_yolo26n_good_b32/weights/best.pt \
  --stage2-model /home/edv/Desktop/yolo_runs/gauge_crop_yolo26s_full_b32/weights/best.pt
```

## Testlauf

```bash
/home/edv/.local/share/pipx/venvs/ultralytics/bin/python main.py \
  --input /home/edv/Desktop/Werkfotos_Sortiert \
  --output /home/edv/Desktop/Manometer_YOLO_Auswertung_Test \
  --stage1-model /home/edv/Desktop/yolo_runs/gauge_yolo26n_good_b32/weights/best.pt \
  --stage2-model /home/edv/Desktop/yolo_runs/gauge_crop_yolo26s_full_b32/weights/best.pt \
  --max-images-per-folder 3
```

## Ausgabe

```text
Manometer_YOLO_Auswertung/
├── readings.csv
└── overlays/
```

## Klassen

Stage 1:

```text
0 center
1 gauge
2 max
3 min
4 tip
```

Stage 2:

```text
0 center
1 max
2 min
3 tip
```
