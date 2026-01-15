import cv2
import numpy as np
import onnxruntime as ort
import yaml
import os

class YoloHelper:
    def __init__(self, model_path, yaml_path):
        self.class_names = []
        self.session = None
        self.model_input_size = 640 
        
        self.CONF_THRESH = 0.25      
        self.MIN_PIXEL_AREA = 300   
        self.MAX_PIXEL_AREA = 800000 
        
        self.ANTI_ROUND_RATIO_MIN = 0.80  
        self.ANTI_ROUND_RATIO_MAX = 1.25  
        self.ANTI_ROUND_MAX_AREA = 7000  
        self.BORDER_MARGIN = 80 
        self.OVERLAP_RATIO = 0.10    
        self.USE_CLAHE = False       

        if os.path.exists(yaml_path):
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
                if 'names' in data: self.class_names = data['names']
        
        if os.path.exists(model_path):
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            try:
                self.session = ort.InferenceSession(model_path, providers=providers)
            except:
                try:
                    self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
                except:
                    self.session = None

    def preprocess_one(self, img):
        img_resized = cv2.resize(img, (self.model_input_size, self.model_input_size))
        image_data = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        image_data = image_data.astype(np.float32) / 255.0
        image_data = np.transpose(image_data, (2, 0, 1))
        image_data = np.expand_dims(image_data, axis=0)
        return image_data

    def detect(self, image_path, conf=None, iou=0.45):
        if conf is None: conf = self.CONF_THRESH
        if self.session is None: return []

        try:
            stream = open(image_path, "rb")
            bytes = bytearray(stream.read())
            numpyarray = np.asarray(bytes, dtype=np.uint8)
            img_orig = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
        except: return []
            
        if img_orig is None: return []
        if img_orig.shape[2] == 4: img_orig = cv2.cvtColor(img_orig, cv2.COLOR_BGRA2BGR)

        h_img, w_img = img_orig.shape[:2]
        
        rows, cols = 1, 1
        if w_img > 2000 or h_img > 2000:
            rows, cols = 2, 2
            if w_img > 4000: cols = 3 

        tile_w = int(w_img / cols * (1 + self.OVERLAP_RATIO))
        tile_h = int(h_img / rows * (1 + self.OVERLAP_RATIO))
        
        if cols > 1: stride_x = int((w_img - tile_w) / (cols - 1))
        else: stride_x = 0
        if rows > 1: stride_y = int((h_img - tile_h) / (rows - 1))
        else: stride_y = 0

        batch_input = []
        batch_metadata = [] 

        for r in range(rows):
            for c in range(cols):
                if cols > 1: x1 = c * stride_x
                else: x1 = 0
                if rows > 1: y1 = r * stride_y
                else: y1 = 0
                x2 = min(x1 + tile_w, w_img)
                y2 = min(y1 + tile_h, h_img)
                tile = img_orig[y1:y2, x1:x2]
                if tile.size == 0: continue

                blob = self.preprocess_one(tile) 
                batch_input.append(blob)
                
                curr_h, curr_w = tile.shape[:2]
                scale_x = 640 / curr_w
                scale_y = 640 / curr_h
                batch_metadata.append({"x1": x1, "y1": y1, "scale_x": scale_x, "scale_y": scale_y})

        if not batch_input: return []
        
        input_tensor = np.vstack(batch_input) 
        input_name = self.session.get_inputs()[0].name
        
        try:
            outputs = self.session.run(None, {input_name: input_tensor})
            raw_output = outputs[0]
        except:
            raw_output = []
            for i in range(len(batch_input)):
                 single_input = input_tensor[i:i+1]
                 out = self.session.run(None, {input_name: single_input})
                 raw_output.append(out[0][0])
            raw_output = np.array(raw_output)

        final_results = []
        for i, batch_item in enumerate(raw_output):
            meta = batch_metadata[i]
            x1, y1 = meta["x1"], meta["y1"]
            scale_x, scale_y = meta["scale_x"], meta["scale_y"]

            prediction = batch_item.T 
            scores = np.max(prediction[:, 4:], axis=1)
            keep = scores > conf
            prediction = prediction[keep]
            scores = scores[keep]
            
            for j, pred in enumerate(prediction):
                class_id = np.argmax(pred[4:])
                score = float(pred[4 + class_id])
                label_name = self.class_names[class_id] if class_id < len(self.class_names) else "Unknown"
                
                if "hole" in label_name.lower(): continue 
                
                if "flux" in label_name.lower() or "defect" in label_name.lower():
                    cx, cy, w, h = pred[:4]
                    real_w = w / scale_x
                    real_h = h / scale_y
                    area = real_w * real_h
                    
                    if area < self.MIN_PIXEL_AREA: continue 
                    if area > self.MAX_PIXEL_AREA: continue
                    
                    t_x = (cx - w / 2) / scale_x
                    t_y = (cy - h / 2) / scale_y
                    g_x = t_x + x1
                    g_y = t_y + y1
                    g_x2 = g_x + real_w
                    g_y2 = g_y + real_h
                    
                    margin = self.BORDER_MARGIN
                    if g_x < margin or g_y < margin or g_x2 > (w_img - margin) or g_y2 > (h_img - margin): continue

                    ratio = 0
                    if real_h > 0: ratio = real_w / real_h
                    if self.ANTI_ROUND_RATIO_MIN <= ratio <= self.ANTI_ROUND_RATIO_MAX:
                        if area < self.ANTI_ROUND_MAX_AREA: continue

                    final_results.append([int(g_x), int(g_y), int(real_w), int(real_h), float(score), int(class_id)])

        if len(final_results) == 0: return []
        
        final_results = np.array(final_results)
        boxes = final_results[:, :4].astype(int).tolist()
        scores = final_results[:, 4].tolist()
        class_ids = final_results[:, 5].astype(int).tolist()
        
        indices = cv2.dnn.NMSBoxes(boxes, scores, score_threshold=conf, nms_threshold=iou)
        
        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]
                x = max(0, min(x, w_img))
                y = max(0, min(y, h_img))
                x2 = min(w_img, x + w)
                y2 = min(h_img, y + h)
                final_label = self.class_names[class_ids[i]] if class_ids[i] < len(self.class_names) else "Defect"
                results.append({"x1": x, "y1": y, "x2": x2, "y2": y2, "score": scores[i], "class_id": class_ids[i], "label": final_label})
        
        return results
