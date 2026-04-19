import os
import warnings

# Suppress onnxruntime C++ provider logs before the module is imported
os.environ.setdefault("ORT_LOGGING_LEVEL", "3")

import cv2
import numpy as np
import torch
import onnxruntime as ort
from ultralytics.utils.nms import non_max_suppression
from utils import load_toml_as_dict

warnings.filterwarnings("ignore", category=UserWarning)

debug = load_toml_as_dict("cfg/general_config.toml")['super_debug'] == "yes"

def get_optimal_threads(max_limit=4):
    threads = os.cpu_count()
    threads_amount = min(max(2, threads // 2), max_limit)
    if True: print(f"Detected {threads} CPU threads, using {threads_amount} threads.")
    return threads_amount

optimal_threads_amount = get_optimal_threads()
torch.set_num_threads(optimal_threads_amount)

class Detect:
    def __init__(self, model_path, ignore_classes=None, classes=None, input_size=(640, 640)):
        self.preferred_device = load_toml_as_dict("cfg/general_config.toml")['cpu_or_gpu']
        self.model_path = model_path
        self.classes = classes
        self.ignore_classes = ignore_classes if ignore_classes else []
        self.input_size = input_size
        self.model, self.device = self.load_model()
        self._padded_img_buffer = np.full(
            (1, 3, self.input_size[0], self.input_size[1]),
            128.0 / 255.0,
            dtype=np.float32
        )


    def load_model(self):
        available_providers = ort.get_available_providers()
        providers = []

        # TensorRT requires nvinfer_10.dll — register its dir then probe
        _trt_usable = False
        if "TensorrtExecutionProvider" in available_providers:
            import ctypes
            trt_lib = os.environ.get("TRT_LIB_PATH", "")
            if trt_lib and os.path.isdir(trt_lib):
                os.add_dll_directory(trt_lib)
            try:
                dll_path = os.path.join(trt_lib, "nvinfer_10.dll") if trt_lib else "nvinfer_10.dll"
                ctypes.CDLL(dll_path)
                _trt_usable = True
            except OSError:
                pass

        if self.preferred_device == "gpu" or self.preferred_device == "auto":
            if _trt_usable:
                providers = [
                    ("TensorrtExecutionProvider", {
                        "trt_engine_cache_enable": True,
                        "trt_engine_cache_path": "./cfg/trt_cache",
                        "trt_fp16_enable": True,
                    }),
                    ("CUDAExecutionProvider", {"cudnn_conv_algo_search": "HEURISTIC"}),
                    "CPUExecutionProvider",
                ]
                print("Using TensorRT GPU (first run builds engine cache, subsequent runs are faster)")
            elif "CUDAExecutionProvider" in available_providers:
                providers = [
                    ("CUDAExecutionProvider", {"cudnn_conv_algo_search": "HEURISTIC"}),
                    "CPUExecutionProvider",
                ]
                print("Using CUDA GPU")
            elif "DmlExecutionProvider" in available_providers:
                providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
                print("Using DirectML GPU")
            else:
                providers = ["CPUExecutionProvider"]
                print("Using CPU as no GPU provider found")
        else:
            providers = ["CPUExecutionProvider"]

        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        so.intra_op_num_threads = optimal_threads_amount
        so.inter_op_num_threads = optimal_threads_amount
        so.log_severity_level = 3  # suppress ORT C++ warnings

        os.makedirs("./cfg/trt_cache", exist_ok=True)

        trt_cache_empty = _trt_usable and not any(
            f.endswith(".engine") for f in os.listdir("./cfg/trt_cache")
        )
        if trt_cache_empty:
            print(f"[TRT] Building engine for {os.path.basename(self.model_path)} — this takes 2-5 min on first run, please wait...")
            import sys; sys.stdout.flush()

        model = ort.InferenceSession(self.model_path, sess_options=so, providers=providers)
        active = model.get_providers()[0]

        if trt_cache_empty:
            print("[TRT] Engine built and cached — future launches will be instant.")
        print(f"Active inference provider: {active}")

        return model, active

    def preprocess_image(self, img):
        h, w, _ = img.shape
        scale = min(self.input_size[0] / h, self.input_size[1] / w)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        self._padded_img_buffer[0, :, :new_h, :new_w] = np.transpose(resized_img, (2, 0, 1)).astype(np.float32) / 255.0

        return self._padded_img_buffer, new_w, new_h

    def postprocess(self, preds, img, orig_img_shape, resized_shape, conf_tresh=0.6):
        # Apply Non-Maximum Suppression (NMS)

        preds = non_max_suppression(
            preds,
            conf_thres=conf_tresh,
            iou_thres=0.6,
            classes=None,
            agnostic=False,
        )

        orig_h, orig_w = orig_img_shape
        resized_w, resized_h = resized_shape

        # Calculate the scaling factor and padding
        scale_w = orig_w / resized_w
        scale_h = orig_h / resized_h

        results = []
        for pred in preds:
            if len(pred):
                pred[:, 0] *= scale_w  # x1
                pred[:, 1] *= scale_h  # y1
                pred[:, 2] *= scale_w  # x2
                pred[:, 3] *= scale_h  # y2
                results.append(pred.cpu().numpy())

        return results

    def detect_objects(self, img, conf_tresh=0.6):
        orig_h, orig_w = img.shape[:2]
        orig_img_shape = (orig_h, orig_w)

        # Preprocess the image
        preprocessed_img, resized_w, resized_h = self.preprocess_image(img)
        resized_shape = (resized_w, resized_h)

        # Run inference
        outputs = self.model.run(None, {'images': preprocessed_img})

        # Postprocess the outputs
        detections = self.postprocess(torch.from_numpy(outputs[0]), preprocessed_img, orig_img_shape, resized_shape, conf_tresh)

        results = {}
        for detection in detections:
            for *xyxy, conf, cls in detection:
                x1, y1, x2, y2 = map(int, xyxy)
                class_id = int(cls)
                class_name = self.classes[class_id]

                if class_id in self.ignore_classes or class_name in self.ignore_classes:
                    continue
                if class_name not in results:
                    results[class_name] = []
                results[class_name].append([x1, y1, x2, y2])

        return results


