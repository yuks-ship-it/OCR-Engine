# train.py - Train YOLO model on your dataset
from ultralytics import YOLO

if __name__ == "__main__":
    # Load a pre-trained model (YOLOv8n is lightweight)
    model = YOLO('yolov8n.pt')  # or 'yolov8s.pt' for better accuracy

    # Train the model
    model.train(
        data='dataset/data.yaml',
        epochs=100,
        imgsz=640,
        batch=16,
        name='board_detector',
        project='runs',
        exist_ok=True
    )
    print("Training complete. Best model saved at runs/board_detector/weights/best.pt")