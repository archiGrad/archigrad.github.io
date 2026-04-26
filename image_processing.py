from PIL import Image

RESIZE_METHODS = {
    'NEAREST': Image.Resampling.NEAREST,
    'BOX': Image.Resampling.BOX,
    'BILINEAR': Image.Resampling.BILINEAR,
    'HAMMING': Image.Resampling.HAMMING,
    'BICUBIC': Image.Resampling.BICUBIC,
    'LANCZOS': Image.Resampling.LANCZOS,
}


def _apply_sharpen(img, conf):
    if conf['SHARPEN']:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.UnsharpMask(
            radius=conf['SHARPEN_RADIUS'],
            percent=conf['SHARPEN_PERCENT'],
            threshold=conf['SHARPEN_THRESHOLD']
        )) 
    return img


def _apply_blur(img, conf):
    if conf['GAUSSIAN_BLUR']:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=conf['GAUSSIAN_BLUR_RADIUS']))
    return img


def _apply_color_to_transparent(img, conf):
    if not conf.get('COLOR_TO_TRANSPARENT'):
        return img
    tc = _parse_color(conf.get('COLOR_TO_TRANSPARENT_COLOR', [0, 0, 0]))
    threshold = conf.get('COLOR_TO_TRANSPARENT_THRESHOLD', 0)
    img = img.convert('RGBA')
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if abs(r - tc[0]) < threshold and abs(g - tc[1]) < threshold and abs(b - tc[2]) < threshold:
                pixels[x, y] = (r, g, b, 0)
    return img


def _apply_contrast(img, conf):
    if conf['CONTRAST']:
        from PIL import ImageEnhance
        img = ImageEnhance.Contrast(img).enhance(conf['CONTRAST_FACTOR'])
    return img


def _apply_exposure(img, conf):
    if conf['EXPOSURE']:
        import numpy as np
        factor = conf['EXPOSURE_FACTOR']
        arr = np.array(img, dtype=np.float32)
        if img.mode == 'RGBA':
            arr[..., :3] = np.clip(arr[..., :3] * factor, 0, 255)
        else:
            arr = np.clip(arr * factor, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8), img.mode)
    return img


def _apply_gamma(img, conf):
    if conf['GAMMA']:
        import numpy as np
        gamma = conf['GAMMA_VALUE']
        inv_gamma = 1.0 / gamma
        arr = np.array(img, dtype=np.float32)
        if img.mode == 'RGBA':
            arr[..., :3] = np.clip(255.0 * (arr[..., :3] / 255.0) ** inv_gamma, 0, 255)
        else:
            arr = np.clip(255.0 * (arr / 255.0) ** inv_gamma, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8), img.mode)
    return img


def _apply_alpha_outline(img, conf):
    if conf['ALPHA_OUTLINE']:
        import numpy as np

        thickness = conf['ALPHA_OUTLINE_THICKNESS']
        outline_color = _parse_color(conf['ALPHA_OUTLINE_COLOR'])

        img = img.convert('RGBA')
        arr = np.array(img)
        alpha = arr[..., 3]
        opaque = alpha > 0

        source = opaque if thickness < 0 else ~opaque
        dist = np.zeros(source.shape, dtype=np.float32)
        dist[source] = float('inf')
        remaining = source.copy()
        for i in range(1, abs(thickness) + 1):
            eroded = remaining.copy()
            eroded[1:] &= remaining[:-1]
            eroded[:-1] &= remaining[1:]
            eroded[:, 1:] &= remaining[:, :-1]
            eroded[:, :-1] &= remaining[:, 1:]
            border = remaining & ~eroded
            dist[border] = i
            remaining = eroded

        abs_t = abs(thickness)
        mask = (dist >= 1) & (dist <= abs_t)
        mode = conf['ALPHA_OUTLINE_LERPCOLOR']
        oc = np.array(outline_color, dtype=np.float32)

        edge_rgb = arr[..., :3].copy()
        if thickness > 0 and mode != 'newcolor':
            filled = opaque.copy()
            for _ in range(abs_t):
                expanded = filled.copy()
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    shifted = np.roll(np.roll(filled, dy, 0), dx, 1)
                    shifted_rgb = np.roll(np.roll(edge_rgb, dy, 0), dx, 1)
                    new_pixels = shifted & ~expanded
                    for c in range(3):
                        edge_rgb[..., c][new_pixels] = shifted_rgb[..., c][new_pixels]
                    expanded |= shifted
                filled = expanded
        elif thickness < 0 and mode != 'newcolor':
            border1 = opaque & ~(np.roll(opaque,1,0) & np.roll(opaque,-1,0) & np.roll(opaque,1,1) & np.roll(opaque,-1,1))
            filled = border1.copy()
            for _ in range(abs_t):
                expanded = filled.copy()
                for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                    shifted = np.roll(np.roll(filled, dy, 0), dx, 1)
                    shifted_rgb = np.roll(np.roll(edge_rgb, dy, 0), dx, 1)
                    new_pixels = shifted & ~expanded & opaque
                    for c in range(3):
                        edge_rgb[..., c][new_pixels] = shifted_rgb[..., c][new_pixels]
                    expanded |= shifted
                filled = expanded

        grad = np.clip(1.0 - (dist[mask] - 1) / max(abs_t - 1, 1), 0, 1)

        if mode == 'bordercolor':
            for c in range(3):
                arr[..., c][mask] = edge_rgb[..., c][mask]
        elif mode == 'newcolor':
            for c in range(3):
                arr[..., c][mask] = int(oc[c])
        elif mode == 'border_to_new':
            for c in range(3):
                orig = edge_rgb[..., c][mask].astype(np.float32)
                arr[..., c][mask] = (orig * grad + oc[c] * (1.0 - grad)).astype(np.uint8)
        elif mode == 'new_to_border':
            for c in range(3):
                orig = edge_rgb[..., c][mask].astype(np.float32)
                arr[..., c][mask] = (oc[c] * grad + orig * (1.0 - grad)).astype(np.uint8)

        if thickness > 0:
            arr[..., 3][mask] = 255

        img = Image.fromarray(arr, 'RGBA')
    return img


# HUE examples for .custom_processing:
#   Shift hue by 60 degrees:
#     HUE = True
#     HUE_SHIFT = 60
#   HUE_SHIFT range: -180 to 180 (degrees)
def _apply_hue(img, conf):
    if not conf.get('HUE'):
        return img
    import numpy as np
    shift = conf.get('HUE_SHIFT', 0)
    has_alpha = img.mode == 'RGBA'
    alpha = img.split()[3] if has_alpha else None
    hsv = img.convert('HSV')
    arr = np.array(hsv, dtype=np.int16)
    arr[..., 0] = (arr[..., 0] + int(shift / 360.0 * 255)) % 256
    img = Image.fromarray(arr.astype(np.uint8), 'HSV').convert('RGB')
    if has_alpha:
        img = img.convert('RGBA')
        img.putalpha(alpha)
    return img


# SATURATION examples for .custom_processing:
#   Boost saturation:
#     SATURATION = True
#     SATURATION_FACTOR = 1.5
#   Desaturate to grayscale:
#     SATURATION = True
#     SATURATION_FACTOR = 0.0
def _apply_saturation(img, conf):
    if not conf.get('SATURATION'):
        return img
    from PIL import ImageEnhance
    factor = conf.get('SATURATION_FACTOR', 1.0)
    has_alpha = img.mode == 'RGBA'
    alpha = img.split()[3] if has_alpha else None
    rgb = img.convert('RGB')
    rgb = ImageEnhance.Color(rgb).enhance(factor)
    if has_alpha:
        rgb = rgb.convert('RGBA')
        rgb.putalpha(alpha)
    return rgb


# VIBRANCE examples for .custom_processing:
#   Subtle vibrance boost (only muted colors):
#     VIBRANCE = True
#     VIBRANCE_FACTOR = 0.5
#   Strong vibrance:
#     VIBRANCE = True
#     VIBRANCE_FACTOR = 1.0
#   VIBRANCE_FACTOR range: -1.0 to 1.0
def _apply_vibrance(img, conf):
    if not conf.get('VIBRANCE'):
        return img
    import numpy as np
    factor = conf.get('VIBRANCE_FACTOR', 0.5)
    has_alpha = img.mode == 'RGBA'
    alpha = img.split()[3] if has_alpha else None
    rgb = np.array(img.convert('RGB'), dtype=np.float32)
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    weight = (1.0 - sat) * factor
    weight = weight[..., np.newaxis]
    avg = rgb.mean(axis=-1, keepdims=True)
    rgb = np.clip(rgb + (rgb - avg) * weight, 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb, 'RGB')
    if has_alpha:
        img = img.convert('RGBA')
        img.putalpha(alpha)
    return img


# CONTOUR examples for .custom_processing:
#   White contour on transparent background:
#     CONTOUR = True
#     CONTOUR_LOW = 100
#     CONTOUR_HIGH = 200
#     CONTOUR_COLOR = white
#     CONTOUR_THICKNESS = 1
#     CONTOUR_OVERLAY = false
#   Red contour overlaid on original:
#     CONTOUR = True
#     CONTOUR_LOW = 50
#     CONTOUR_HIGH = 150
#     CONTOUR_COLOR = red
#     CONTOUR_OVERLAY = true
def _apply_contour(img, conf):
    if not conf.get('CONTOUR'):
        return img
    import numpy as np
    import cv2
    low = conf.get('CONTOUR_LOW', 100)
    high = conf.get('CONTOUR_HIGH', 200)
    color = _parse_color(conf.get('CONTOUR_COLOR', [255, 255, 255]))
    thickness = conf.get('CONTOUR_THICKNESS', 1)
    overlay = conf.get('CONTOUR_OVERLAY', False)
    img = img.convert('RGBA')
    arr = np.array(img)
    gray = cv2.cvtColor(arr[..., :3], cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, low, high)
    if thickness > 1:
        k = np.ones((thickness, thickness), np.uint8)
        edges = cv2.dilate(edges, k)
    mask = edges > 0
    if overlay:
        for c in range(3):
            arr[..., c][mask] = color[c]
        arr[..., 3][mask] = 255
    else:
        out = np.zeros_like(arr)
        for c in range(3):
            out[..., c][mask] = color[c]
        out[..., 3][mask] = 255
        arr = out
    return Image.fromarray(arr, 'RGBA')


_MP_MODEL_DIR = None
_POSE_DETECTOR = None
_FACE_DETECTOR = None
_SSD_NET = None
_SSD_CLASSES = ['background', 'aeroplane', 'bicycle', 'bird', 'boat',
                'bottle', 'bus', 'car', 'cat', 'chair', 'cow', 'diningtable',
                'dog', 'horse', 'motorbike', 'person', 'pottedplant', 'sheep',
                'sofa', 'train', 'tvmonitor']

_POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),
    (15, 17), (15, 19), (15, 21), (17, 19),
    (16, 18), (16, 20), (16, 22), (18, 20),
]


def _resolve_model_dir(conf, key, default_subdir):
    import os
    val = conf.get(key) or ''
    base = os.path.dirname(os.path.abspath(__file__))
    if val:
        d = val if os.path.isabs(val) else os.path.normpath(os.path.join(base, val))
    else:
        d = os.path.normpath(os.path.join(base, 'models', default_subdir))
    os.makedirs(d, exist_ok=True)
    return d


def _get_model_dir(conf):
    return _resolve_model_dir(conf, 'MEDIAPIPE_MODEL_DIR', 'mediapipe')


def _download(url, path):
    import urllib.request
    if not __import__('os').path.exists(path):
        urllib.request.urlretrieve(url, path)
    return path


def _get_pose_detector(conf):
    global _POSE_DETECTOR
    if _POSE_DETECTOR is None:
        import os
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        variant = conf.get('POSE_MODEL', 'lite')
        url = f'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{variant}/float16/latest/pose_landmarker_{variant}.task'
        path = os.path.join(_get_model_dir(conf), f'pose_landmarker_{variant}.task')
        _download(url, path)
        opts = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=path),
            num_poses=conf.get('POSE_MAX', 5),
        )
        _POSE_DETECTOR = mp_vision.PoseLandmarker.create_from_options(opts)
    return _POSE_DETECTOR


def _get_face_detector(conf):
    global _FACE_DETECTOR
    if _FACE_DETECTOR is None:
        import os
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        url = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'
        path = os.path.join(_get_model_dir(conf), 'face_landmarker.task')
        _download(url, path)
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=path),
            num_faces=conf.get('FACE_MAX', 5),
        )
        _FACE_DETECTOR = mp_vision.FaceLandmarker.create_from_options(opts)
    return _FACE_DETECTOR


# POSE examples for .custom_processing:
#   Draw skeleton over detected people:
#     POSE = True
#     POSE_COLOR = lime
#     POSE_THICKNESS = 2
#     POSE_POINT_RADIUS = 3
#     POSE_MAX = 5
#     POSE_MODEL = lite      # lite | full | heavy
#     POSE_MIN_VISIBILITY = 0.5
def _apply_pose(img, conf):
    if not conf.get('POSE'):
        return img
    import numpy as np
    import cv2
    import mediapipe as mp
    color = _parse_color(conf.get('POSE_COLOR', [0, 255, 0]))
    thickness = conf.get('POSE_THICKNESS', 2)
    radius = conf.get('POSE_POINT_RADIUS', 3)
    min_vis = conf.get('POSE_MIN_VISIBILITY', 0.5)
    img = img.convert('RGBA')
    arr = np.array(img)
    rgb = arr[..., :3].copy()
    detector = _get_pose_detector(conf)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_img)
    h, w = arr.shape[:2]
    bgr_color = (int(color[2]), int(color[1]), int(color[0]))
    canvas = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    for landmarks in result.pose_landmarks or []:
        pts = []
        for lm in landmarks:
            vis = getattr(lm, 'visibility', 1.0)
            pts.append((int(lm.x * w), int(lm.y * h), vis))
        for a, b in _POSE_CONNECTIONS:
            if a < len(pts) and b < len(pts) and pts[a][2] >= min_vis and pts[b][2] >= min_vis:
                cv2.line(canvas, pts[a][:2], pts[b][:2], bgr_color + (255,), thickness, cv2.LINE_AA)
        for x, y, v in pts:
            if v >= min_vis:
                cv2.circle(canvas, (x, y), radius, bgr_color + (255,), -1, cv2.LINE_AA)
    arr = cv2.cvtColor(canvas, cv2.COLOR_BGRA2RGBA)
    return Image.fromarray(arr, 'RGBA')


# FACE examples for .custom_processing:
#   Draw face landmarks (478 dots) over detected faces:
#     FACE = True
#     FACE_COLOR = cyan
#     FACE_POINT_RADIUS = 1
#     FACE_MAX = 5
def _apply_face(img, conf):
    if not conf.get('FACE'):
        return img
    import numpy as np
    import cv2
    import mediapipe as mp
    color = _parse_color(conf.get('FACE_COLOR', [0, 255, 255]))
    radius = conf.get('FACE_POINT_RADIUS', 1)
    img = img.convert('RGBA')
    arr = np.array(img)
    rgb = arr[..., :3].copy()
    detector = _get_face_detector(conf)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_img)
    h, w = arr.shape[:2]
    bgr_color = (int(color[2]), int(color[1]), int(color[0]))
    canvas = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    for landmarks in result.face_landmarks or []:
        for lm in landmarks:
            x, y = int(lm.x * w), int(lm.y * h)
            cv2.circle(canvas, (x, y), radius, bgr_color + (255,), -1, cv2.LINE_AA)
    arr = cv2.cvtColor(canvas, cv2.COLOR_BGRA2RGBA)
    return Image.fromarray(arr, 'RGBA')


def _get_ssd_net(conf):
    global _SSD_NET
    if _SSD_NET is None:
        import os
        import cv2
        d = _resolve_model_dir(conf, 'MOBILENETSSD_MODEL_DIR', 'ssd')
        proto = os.path.join(d, 'MobileNetSSD_deploy.prototxt')
        weights = os.path.join(d, 'MobileNetSSD_deploy.caffemodel')
        _download('https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/voc/MobileNetSSD_deploy.prototxt', proto)
        _download('https://raw.githubusercontent.com/djmv/MobilNet_SSD_opencv/master/MobileNetSSD_deploy.caffemodel', weights)
        _SSD_NET = cv2.dnn.readNetFromCaffe(proto, weights)
    return _SSD_NET


# DETECT examples for .custom_processing:
#   Annotate detected objects with boxes and labels:
#     DETECT = True
#     DETECT_THRESHOLD = 0.4
#     DETECT_BOX_COLOR = yellow
#     DETECT_BOX_THICKNESS = 2
#     DETECT_LABEL = true
#     DETECT_LABEL_COLOR = black
#     DETECT_LABEL_BG = yellow
#     DETECT_LABEL_SCALE = 0.5
#     DETECT_CLASSES = person,car,dog        # comma-separated, omit for all
def _apply_detect(img, conf):
    if not conf.get('DETECT'):
        return img
    import numpy as np
    import cv2
    threshold = conf.get('DETECT_THRESHOLD', 0.4)
    box_color = _parse_color(conf.get('DETECT_BOX_COLOR', [255, 255, 0]))
    box_thickness = conf.get('DETECT_BOX_THICKNESS', 2)
    show_label = conf.get('DETECT_LABEL', True)
    label_color = _parse_color(conf.get('DETECT_LABEL_COLOR', [0, 0, 0]))
    label_bg = _parse_color(conf.get('DETECT_LABEL_BG', [255, 255, 0]))
    label_scale = conf.get('DETECT_LABEL_SCALE', 0.5)
    classes_filter = conf.get('DETECT_CLASSES')
    if isinstance(classes_filter, str):
        classes_filter = {c.strip().lower() for c in classes_filter.split(',') if c.strip()}
    elif isinstance(classes_filter, (list, tuple)):
        classes_filter = {str(c).strip().lower() for c in classes_filter}
    img = img.convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    bgr = cv2.cvtColor(arr[..., :3], cv2.COLOR_RGB2BGR)
    net = _get_ssd_net(conf)
    blob = cv2.dnn.blobFromImage(bgr, 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()
    canvas = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    box_bgr = (int(box_color[2]), int(box_color[1]), int(box_color[0]), 255)
    label_bgr = (int(label_color[2]), int(label_color[1]), int(label_color[0]), 255)
    label_bg_bgr = (int(label_bg[2]), int(label_bg[1]), int(label_bg[0]), 255)
    for i in range(detections.shape[2]):
        conf_score = float(detections[0, 0, i, 2])
        if conf_score < threshold:
            continue
        idx = int(detections[0, 0, i, 1])
        cname = _SSD_CLASSES[idx] if idx < len(_SSD_CLASSES) else str(idx)
        if classes_filter and cname.lower() not in classes_filter:
            continue
        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
        x0, y0, x1, y1 = box.astype(int)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w - 1, x1), min(h - 1, y1)
        cv2.rectangle(canvas, (x0, y0), (x1, y1), box_bgr, box_thickness)
        if show_label:
            text = f'{cname} {conf_score:.2f}'
            (tw, th), bl = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, label_scale, 1)
            ly = max(th + 2, y0)
            cv2.rectangle(canvas, (x0, ly - th - 2), (x0 + tw + 2, ly + bl), label_bg_bgr, -1)
            cv2.putText(canvas, text, (x0 + 1, ly - 1), cv2.FONT_HERSHEY_SIMPLEX, label_scale, label_bgr, 1, cv2.LINE_AA)
    arr = cv2.cvtColor(canvas, cv2.COLOR_BGRA2RGBA)
    return Image.fromarray(arr, 'RGBA')


COLOR_MAP = {
    'black': (0, 0, 0), 'white': (255, 255, 255), 'red': (255, 0, 0),
    'green': (0, 255, 0), 'blue': (0, 0, 255), 'yellow': (255, 255, 0),
    'cyan': (0, 255, 255), 'magenta': (255, 0, 255), 'light_gray': (192, 192, 192),
    'dark_gray': (64, 64, 64), 'orange': (255, 165, 0), 'purple': (128, 0, 128),
    'lime': (0, 255, 0)
}


def _parse_color(c):
    if isinstance(c, (list, tuple)) and len(c) == 3:
        return tuple(int(x) for x in c)
    if isinstance(c, str) and c.startswith('#'):
        h = c.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    if isinstance(c, str):
        return COLOR_MAP.get(c, (0, 0, 0))
    return (0, 0, 0)


# INVERT examples for .custom_processing:
#   Invert all pixels:
#     INVERT = True
#   Invert only near a specific color:
#     INVERT = True
#     INVERT_COLOR = white
#     INVERT_THRESHOLD = 40
def _apply_invert(img, conf):
    if conf.get('INVERT'):
        import numpy as np
        img = img.convert('RGBA')
        arr = np.array(img)
        color = conf.get('INVERT_COLOR', [0, 0, 0])
        threshold = conf.get('INVERT_THRESHOLD', 0)
        if threshold > 0:
            tc = np.array(_parse_color(color), dtype=np.float32)
            diff = np.abs(arr[..., :3].astype(np.float32) - tc)
            mask = np.all(diff < threshold, axis=-1)
            arr[..., :3][mask] = 255 - arr[..., :3][mask]
        else:
            arr[..., :3] = 255 - arr[..., :3]
        img = Image.fromarray(arr, 'RGBA')
    return img


# PIXELATE examples for .custom_processing:
#   Basic pixelate (divide resolution by 4):
#     PIXELATE = True
#     PIXELATE_LEVEL = 4
#   Pixelate with specific resampling:
#     PIXELATE = True
#     PIXELATE_LEVEL = 8
#     PIXELATE_DOWN_METHOD = NEAREST
#     PIXELATE_UP_METHOD = NEAREST
def _apply_pixelate(img, conf):
    if conf.get('PIXELATE'):
        level = conf.get('PIXELATE_LEVEL', 2)
        down_method = RESIZE_METHODS.get(conf.get('PIXELATE_DOWN_METHOD', 'NEAREST').upper(), Image.Resampling.NEAREST)
        up_method = RESIZE_METHODS.get(conf.get('PIXELATE_UP_METHOD', 'NEAREST').upper(), Image.Resampling.NEAREST)
        w, h = img.size
        small_w, small_h = max(1, w // level), max(1, h // level)
        img = img.resize((small_w, small_h), down_method).resize((w, h), up_method)
    return img


# FILL examples for .custom_processing:
#   Fill transparent pixels with black:
#     FILL = True
#     FILL_COLOR = black
#     FILL_THRESHOLD = 128
#   Fill with hex color, low threshold:
#     FILL = True
#     FILL_COLOR = #ff0000
#     FILL_THRESHOLD = 50
def _apply_fill(img, conf):
    if conf.get('FILL'):
        import numpy as np
        fill_color = _parse_color(conf.get('FILL_COLOR', [0, 0, 0]))
        threshold = conf.get('FILL_THRESHOLD', 128)
        img = img.convert('RGBA')
        arr = np.array(img)
        mask = arr[..., 3] < threshold
        arr[..., 0][mask] = fill_color[0]
        arr[..., 1][mask] = fill_color[1]
        arr[..., 2][mask] = fill_color[2]
        arr[..., 3][mask] = 255
        img = Image.fromarray(arr, 'RGBA')
    return img


def _apply_colorize(img, conf):
    if not conf.get('COLORIZE'):
        return img
    import numpy as np
    color = _parse_color(conf.get('COLORIZE_COLOR', [255, 255, 255]))
    threshold = conf.get('COLORIZE_THRESHOLD', 0)
    img = img.convert('RGBA')
    arr = np.array(img)
    mask = arr[..., 3] > threshold
    arr[..., 0][mask] = color[0]
    arr[..., 1][mask] = color[1]
    arr[..., 2][mask] = color[2]
    img = Image.fromarray(arr, 'RGBA')
    return img


# COLOR_REPLACE examples for .custom_processing:
#   Replace red with white:
#     COLOR_REPLACE_SRC = red
#     COLOR_REPLACE_THRESHOLD = 100
#     COLOR_REPLACE_DST = white
def _apply_color_replace(img, conf):
    if not conf.get('COLOR_REPLACE'):
        return img
    import numpy as np
    thresh = conf.get('COLOR_REPLACE_THRESHOLD', 100)
    img = img.convert('RGBA')
    arr = np.array(img)
    sc = np.array(_parse_color(conf.get('COLOR_REPLACE_SRC', [0, 0, 0])), dtype=np.float32)
    dc = _parse_color(conf.get('COLOR_REPLACE_DST', [0, 0, 0]))
    diff = np.abs(arr[..., :3].astype(np.float32) - sc)
    mask = np.all(diff < thresh, axis=-1) if thresh > 0 else np.all(arr[..., :3] == sc.astype(np.uint8), axis=-1)
    arr[..., 0][mask] = dc[0]
    arr[..., 1][mask] = dc[1]
    arr[..., 2][mask] = dc[2]
    img = Image.fromarray(arr, 'RGBA')
    return img


# RECTANGLES examples for .custom_processing:
#   Overlay with fill and border:
#     RECT_AX = 0.1
#     RECT_AY = 0.1
#     RECT_BX = 0.9
#     RECT_BY = 0.9
#     RECT_MODE = overlay
#     RECT_FILL = True
#     RECT_FILL_COLOR = red
#     RECT_BORDER = 3
#     RECT_BORDER_COLOR = white
#     RECT_ROUNDNESS = 0.2
#
# All rectangle options:
#   RECT_AX, RECT_AY, RECT_BX, RECT_BY — corners, normalized 0.0-1.0
#   RECT_MODE       — "overlay", "subtract", "intersect"
#   RECT_FILL       — true/false
#   RECT_FILL_COLOR — color name, hex "#ff0000"
#   RECT_BORDER     — pixel thickness (overlay only)
#   RECT_BORDER_COLOR — color (overlay only)
#   RECT_CUT_BORDER — pixel thickness at new alpha edge (subtract/intersect only)
#   RECT_CUT_BORDER_COLOR — color (subtract/intersect only)
#   RECT_ROUNDNESS  — 0.0 (sharp) to 1.0 (fully rounded)
def _apply_rectangle(img, conf):
    if not conf.get('RECTANGLE'):
        return img
    import numpy as np
    img = img.convert('RGBA')
    w, h = img.size
    ax = conf.get('RECT_AX', 0.0)
    ay = conf.get('RECT_AY', 0.0)
    bx = conf.get('RECT_BX', 1.0)
    by = conf.get('RECT_BY', 1.0)
    mode = conf.get('RECT_MODE', 'overlay')
    fill = conf.get('RECT_FILL', False)
    fill_color = _parse_color(conf.get('RECT_FILL_COLOR', [255, 255, 255]))
    border = conf.get('RECT_BORDER', 0)
    border_color = _parse_color(conf.get('RECT_BORDER_COLOR', [255, 255, 255]))
    roundness = conf.get('RECT_ROUNDNESS', 0.0)

    x0, x1 = int(min(ax, bx) * w), int(max(ax, bx) * w)
    y0, y1 = int(min(ay, by) * h), int(max(ay, by) * h)
    x0, x1 = max(0, x0), min(w, x1)
    y0, y1 = max(0, y0), min(h, y1)

    rw, rh = x1 - x0, y1 - y0
    if rw <= 0 or rh <= 0:
        return img

    yy, xx = np.mgrid[y0:y1, x0:x1]
    if roundness > 0:
        radius = roundness * min(rw, rh) / 2
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = rw / 2 - radius, rh / 2 - radius
        dx = np.clip(np.abs(xx - cx) - hw, 0, None)
        dy = np.clip(np.abs(yy - cy) - hh, 0, None)
        inside = (dx**2 + dy**2) <= radius**2
    else:
        inside = np.ones((rh, rw), dtype=bool)

    if border > 0:
        inner = np.zeros_like(inside)
        iy0, iy1 = border, rh - border
        ix0, ix1 = border, rw - border
        if iy1 > iy0 and ix1 > ix0:
            sub_yy = yy[iy0:iy1, ix0:ix1]
            sub_xx = xx[iy0:iy1, ix0:ix1]
            if roundness > 0:
                ir = max(0, radius - border)
                ihw, ihh = max(0, hw), max(0, hh)
                idx = np.clip(np.abs(sub_xx - cx) - ihw, 0, None)
                idy = np.clip(np.abs(sub_yy - cy) - ihh, 0, None)
                inner[iy0:iy1, ix0:ix1] = (idx**2 + idy**2) <= ir**2
            else:
                inner[iy0:iy1, ix0:ix1] = True
        border_mask_local = inside & ~inner
    else:
        border_mask_local = np.zeros_like(inside)
        inner = inside

    fill_mask_local = inner if fill else np.zeros_like(inside)

    arr = np.array(img)

    combined = np.zeros_like(inside)
    if fill:
        combined |= fill_mask_local
    if border > 0:
        combined |= border_mask_local
    full_shape = np.zeros((h, w), dtype=bool)
    full_shape[y0:y1, x0:x1] = combined

    if mode == 'overlay':
        if fill:
            fm = np.zeros((h, w), dtype=bool)
            fm[y0:y1, x0:x1] = fill_mask_local
            for c in range(3):
                arr[..., c][fm] = fill_color[c]
            arr[..., 3][fm] = 255
        if border > 0:
            bm = np.zeros((h, w), dtype=bool)
            bm[y0:y1, x0:x1] = border_mask_local
            for c in range(3):
                arr[..., c][bm] = border_color[c]
            arr[..., 3][bm] = 255
    elif mode == 'subtract':
        alpha_before = arr[..., 3].copy()
        arr[..., 3][full_shape] = 0
        cut_border = conf.get('RECT_CUT_BORDER', 0)
        if cut_border > 0:
            cut_color = _parse_color(conf.get('RECT_CUT_BORDER_COLOR', [255, 255, 255]))
            new_edge = (alpha_before > 0) & (arr[..., 3] == 0)
            edge_band = new_edge.copy()
            for _ in range(cut_border - 1):
                expanded = edge_band.copy()
                expanded[1:] |= edge_band[:-1]
                expanded[:-1] |= edge_band[1:]
                expanded[:, 1:] |= edge_band[:, :-1]
                expanded[:, :-1] |= edge_band[:, 1:]
                edge_band = expanded
            edge_band &= (alpha_before > 0) & (arr[..., 3] == 0)
            inward = edge_band.copy()
            for _ in range(cut_border):
                shrunk = inward.copy()
                shrunk[1:] &= inward[:-1]
                shrunk[:-1] &= inward[1:]
                shrunk[:, 1:] &= inward[:, :-1]
                shrunk[:, :-1] &= inward[:, 1:]
                inward = shrunk
            neighbor_opaque = np.zeros((h, w), dtype=bool)
            neighbor_opaque[1:] |= (alpha_before[:-1] > 0) & (arr[..., 3][:-1] > 0)
            neighbor_opaque[:-1] |= (alpha_before[1:] > 0) & (arr[..., 3][1:] > 0)
            neighbor_opaque[:, 1:] |= (alpha_before[:, :-1] > 0) & (arr[..., 3][:, :-1] > 0)
            neighbor_opaque[:, :-1] |= (alpha_before[:, 1:] > 0) & (arr[..., 3][:, 1:] > 0)
            seed = new_edge & neighbor_opaque
            cut_mask = seed.copy()
            for _ in range(cut_border - 1):
                expanded = cut_mask.copy()
                expanded[1:] |= cut_mask[:-1]
                expanded[:-1] |= cut_mask[1:]
                expanded[:, 1:] |= cut_mask[:, :-1]
                expanded[:, :-1] |= cut_mask[:, 1:]
                cut_mask = expanded
            cut_mask &= (alpha_before > 0)
            for c in range(3):
                arr[..., c][cut_mask] = cut_color[c]
            arr[..., 3][cut_mask] = 255
    elif mode == 'intersect':
        alpha_before = arr[..., 3].copy()
        arr[..., 3][~full_shape] = 0
        cut_border = conf.get('RECT_CUT_BORDER', 0)
        if cut_border > 0:
            cut_color = _parse_color(conf.get('RECT_CUT_BORDER_COLOR', [255, 255, 255]))
            still_opaque = (arr[..., 3] > 0)
            lost = (alpha_before > 0) & ~still_opaque
            neighbor_lost = np.zeros((h, w), dtype=bool)
            neighbor_lost[1:] |= lost[:-1]
            neighbor_lost[:-1] |= lost[1:]
            neighbor_lost[:, 1:] |= lost[:, :-1]
            neighbor_lost[:, :-1] |= lost[:, 1:]
            seed = still_opaque & neighbor_lost
            cut_mask = seed.copy()
            for _ in range(cut_border - 1):
                expanded = cut_mask.copy()
                expanded[1:] |= cut_mask[:-1]
                expanded[:-1] |= cut_mask[1:]
                expanded[:, 1:] |= cut_mask[:, :-1]
                expanded[:, :-1] |= cut_mask[:, 1:]
                cut_mask = expanded
            cut_mask &= still_opaque
            for c in range(3):
                arr[..., c][cut_mask] = cut_color[c]
            arr[..., 3][cut_mask] = 255

    img = Image.fromarray(arr, 'RGBA')
    return img


# LINES examples for .custom_processing:
#   Diagonal line corner to corner:
#     LINE_AX = 0.0
#     LINE_AY = 0.0
#     LINE_BX = 1.0
#     LINE_BY = 1.0
#     LINE_COLOR = white
#     LINE_THICKNESS = 2
#   Coordinates are normalized 0.0-1.0 (fraction of image size)
def _apply_line(img, conf):
    if not conf.get('LINE'):
        return img
    color_name = conf.get('LINE_COLOR', [255, 255, 255])
    thickness = conf.get('LINE_THICKNESS', 1)
    lax = conf.get('LINE_AX', 0.0)
    lay = conf.get('LINE_AY', 0.0)
    lbx = conf.get('LINE_BX', 1.0)
    lby = conf.get('LINE_BY', 1.0)
    import numpy as np
    img = img.convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    color = _parse_color(color_name)
    x0, y0 = int(lax * w), int(lay * h)
    x1, y1 = int(lbx * w), int(lby * h)
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    half = thickness // 2
    while True:
        for oy in range(-half, half + 1):
            for ox in range(-half, half + 1):
                px, py = x0 + ox, y0 + oy
                if 0 <= px < w and 0 <= py < h:
                    arr[py, px, :3] = color
                    arr[py, px, 3] = 255
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    img = Image.fromarray(arr, 'RGBA')
    return img


# EDGE_OUTLINE examples for .custom_processing:
#   White edge outline, 2px:
#     EDGE_OUTLINE = True
#     EDGE_OUTLINE_THICKNESS = 2
#     EDGE_OUTLINE_COLOR = white
#   Red edge outline from image border inward:
#     EDGE_OUTLINE = True
#     EDGE_OUTLINE_THICKNESS = 5
#     EDGE_OUTLINE_COLOR = #ff0000
def _apply_edge_outline(img, conf):
    if conf.get('EDGE_OUTLINE'):
        import numpy as np
        img = img.convert('RGBA')
        arr = np.array(img)
        h, w = arr.shape[:2]
        alpha = arr[..., 3]
        thickness = conf.get('EDGE_OUTLINE_THICKNESS', 2)
        color = _parse_color(conf.get('EDGE_OUTLINE_COLOR', [255, 255, 255]))
        edge_mask = np.zeros((h, w), dtype=bool)
        edge_mask[0, :] = True
        edge_mask[h-1, :] = True
        edge_mask[:, 0] = True
        edge_mask[:, w-1] = True
        seeds = edge_mask & (alpha > 0)
        outline = seeds.copy()
        for _ in range(thickness - 1):
            expanded = outline.copy()
            expanded[1:] |= outline[:-1]
            expanded[:-1] |= outline[1:]
            expanded[:, 1:] |= outline[:, :-1]
            expanded[:, :-1] |= outline[:, 1:]
            expanded &= (alpha > 0)
            outline = expanded
        for c in range(3):
            arr[..., c][outline] = color[c]
        arr[..., 3][outline] = 255
        img = Image.fromarray(arr, 'RGBA')
    return img


# GRAIN examples for .custom_processing:
#   Subtle B&W grain:
#     GRAIN = True
#     GRAIN_MODE = bw
#     GRAIN_SIZE = 1
#     GRAIN_ROUGHNESS = 0.2
#   Coarse color grain:
#     GRAIN = True
#     GRAIN_MODE = color
#     GRAIN_SIZE = 4
#     GRAIN_ROUGHNESS = 0.8
def _apply_grain(img, conf):
    if conf.get('GRAIN'):
        import numpy as np
        img = img.convert('RGBA')
        arr = np.array(img, dtype=np.float32)
        h, w = arr.shape[:2]
        mode = conf.get('GRAIN_MODE', 'bw')
        size = max(1, conf.get('GRAIN_SIZE', 1))
        roughness = conf.get('GRAIN_ROUGHNESS', 0.5)
        gh, gw = max(1, -(-h // size)), max(1, -(-w // size))
        if mode == 'bw':
            noise = np.random.uniform(-1, 1, (gh, gw)).astype(np.float32)
            noise = np.repeat(np.repeat(noise, size, axis=0), size, axis=1)[:h, :w]
            noise = noise[..., np.newaxis] * np.ones(3)
        else:
            noise = np.random.uniform(-1, 1, (gh, gw, 3)).astype(np.float32)
            noise = np.repeat(np.repeat(noise, size, axis=0), size, axis=1)[:h, :w]
        arr[..., :3] = np.clip(arr[..., :3] + noise * roughness * 255, 0, 255)
        img = Image.fromarray(arr.astype(np.uint8), 'RGBA')
    return img


def _apply_dither(img, conf):
    if conf['DITHERING']:
        dither_map = {
            'floyd_steinberg': Image.Dither.FLOYDSTEINBERG,
            'ordered': Image.Dither.ORDERED,
            'none': Image.Dither.NONE
        }
        
        has_alpha = img.mode == 'RGBA'
        alpha_channel = img.split()[3] if has_alpha else None
        
        if conf['DITHER_MODE'] == 'bw':
            rgb_img = img.convert('L')
            dithered = rgb_img.convert('1', dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        elif conf['DITHER_MODE'] == 'color_reduce':
            rgb_img = img.convert('RGB')
            palette_img = rgb_img.quantize(colors=conf['DITHER_COLORS'], dither=Image.Dither.NONE)
            dithered = rgb_img.quantize(palette=palette_img, dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')

        elif conf['DITHER_MODE'] == 'color_dominant':
            from io import BytesIO
            from colorthief import ColorThief
            rgb_img = img.convert('RGB')
            buf = BytesIO()
            rgb_img.save(buf, format='PNG')
            buf.seek(0)
            n = conf['DITHER_COLORS']
            palette_rgb = ColorThief(buf).get_palette(color_count=max(n + 1, 2), quality=10)[:n]
            palette_colors = []
            for r, g, b in palette_rgb:
                palette_colors.extend([r, g, b])
            while len(palette_colors) < 768:
                palette_colors.extend([0, 0, 0])
            palette_img = Image.new('P', (1, 1))
            palette_img.putpalette(palette_colors)
            dithered = rgb_img.quantize(palette=palette_img, dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        elif conf['DITHER_MODE'] == 'custom_palette':
            palette_colors = []
            for hex_color in conf['CUSTOM_PALETTE']:
                hex_color = hex_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                palette_colors.extend([r, g, b])
            
            while len(palette_colors) < 768:
                palette_colors.extend([0, 0, 0])
            
            palette_img = Image.new('P', (1, 1))
            palette_img.putpalette(palette_colors)
            
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(palette=palette_img, dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        if has_alpha:
            dithered = dithered.convert('RGBA')
            dithered.putalpha(alpha_channel)
        
        img = dithered
    return img


PIPELINE_FNS = {
    'sharpen': _apply_sharpen,
    'blur': _apply_blur,
    'contrast': _apply_contrast,
    'exposure': _apply_exposure,
    'gamma': _apply_gamma,
    'hue': _apply_hue,
    'saturation': _apply_saturation,
    'vibrance': _apply_vibrance,
    'color_to_transparent': _apply_color_to_transparent,
    'alpha_outline': _apply_alpha_outline,
    'dither': _apply_dither,
    'invert': _apply_invert,
    'pixelate': _apply_pixelate,
    'fill': _apply_fill,
    'colorize': _apply_colorize,
    'color_replace': _apply_color_replace,
    'rectangle': _apply_rectangle,
    'line': _apply_line,
    'edge_outline': _apply_edge_outline,
    'grain': _apply_grain,
    'contour': _apply_contour,
    'pose': _apply_pose,
    'face': _apply_face,
    'detect': _apply_detect,
}

DEFAULT_PIPELINE_ORDER = ['sharpen', 'blur', 'contrast', 'exposure', 'gamma', 'hue', 'saturation', 'vibrance', 'color_to_transparent', 'alpha_outline', 'dither', 'invert', 'pixelate', 'fill', 'colorize', 'color_replace', 'rectangle', 'line', 'edge_outline', 'grain', 'contour', 'pose', 'face', 'detect']


def apply_filter(img, conf):
    order = conf.get('PIPELINE_ORDER', DEFAULT_PIPELINE_ORDER)
    for step in order:
        if isinstance(step, dict):
            step_name = step.get('step', '')
            enabled = step.get('enabled', True)
            if not enabled:
                continue
            fn = PIPELINE_FNS.get(step_name)
            if fn:
                merged = dict(conf)
                merged.update(step.get('params', {}))
                if step_name == 'dither':
                    merged['DITHERING'] = True
                elif step_name in ('sharpen','blur','contrast','exposure','gamma','alpha_outline','invert','pixelate','fill','colorize','edge_outline','grain','color_to_transparent','color_replace','rectangle','line','hue','saturation','vibrance','contour','pose','face','detect'):
                    bool_map = {'sharpen':'SHARPEN','blur':'GAUSSIAN_BLUR','contrast':'CONTRAST','exposure':'EXPOSURE','gamma':'GAMMA','alpha_outline':'ALPHA_OUTLINE','invert':'INVERT','pixelate':'PIXELATE','fill':'FILL','colorize':'COLORIZE','edge_outline':'EDGE_OUTLINE','grain':'GRAIN','color_to_transparent':'COLOR_TO_TRANSPARENT','color_replace':'COLOR_REPLACE','rectangle':'RECTANGLE','line':'LINE','hue':'HUE','saturation':'SATURATION','vibrance':'VIBRANCE','contour':'CONTOUR','pose':'POSE','face':'FACE','detect':'DETECT'}
                    bk = bool_map.get(step_name)
                    if bk:
                        merged[bk] = True
                img = fn(img, merged)
        else:
            fn = PIPELINE_FNS.get(step)
            if fn:
                img = fn(img, conf)
    return img


def resize_image(img, target_size, conf):
    force_square = conf.get('SQUARE_IMAGES', True)
    resize_key = conf.get('RESIZE_METHOD', 'LANCZOS')
    resize_method = RESIZE_METHODS.get(resize_key.upper(), Image.Resampling.LANCZOS)
    
    if force_square:
        if img.size != (target_size, target_size):
            img = img.resize((target_size, target_size), resize_method)
        return img

    w, h = img.size
    longest = max(w, h)
    if longest != target_size:
        scale = target_size / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), resize_method)
    return img
