# train.py - Train YOLO model on your dataset
from ultralytics import YOLO

if __name__ == "__main__":
    # yolov8s.pt gives better accuracy than yolov8n.pt
    model = YOLO('yolov8s.pt')

    model.train(
        data='dataset/data.yaml',
        epochs=150,           # More epochs = better accuracy
        imgsz=640,
        batch=16,
        name='board_detector',
        project='runs',
        exist_ok=True,
        patience=20,          # Stop early if no improvement
        lr0=0.01,             # Initial learning rate
        lrf=0.001,            # Final learning rate
        augment=True,         # Data augmentation
        mosaic=1.0,
        degrees=10.0,         # Random rotation (boards can be tilted)
        translate=0.1,
        scale=0.5,
        flipud=0.0,           # Boards don't flip vertically
        fliplr=0.3,
        hsv_h=0.02,           # Slight hue shift for varied lighting
        hsv_s=0.5,
        hsv_v=0.4,            # Value/brightness variation for outdoor boards
    )

    print("Training complete. Best model saved at runs/board_detector/weights/best.pt")